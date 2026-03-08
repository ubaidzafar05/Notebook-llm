from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models import Source, SourceStatus, SourceType
from app.db.repositories.source_repo import ChunkRepository, SourceRepository
from app.embeddings.embedding_service import EmbeddingService
from app.ingestion.chunking.chunk_policy import ChunkPolicy, default_policy, markdown_policy
from app.ingestion.chunking.recursive_chunker import chunk_text
from app.ingestion.chunking.structure_chunker import chunk_markdown_sections
from app.ingestion.parsers.audio_parser import AudioParser
from app.ingestion.parsers.markdown_parser import parse_markdown
from app.ingestion.parsers.pdf_parser import parse_pdf
from app.ingestion.parsers.text_parser import parse_text
from app.ingestion.parsers.web_parser import parse_web_url
from app.ingestion.parsers.youtube_parser import YouTubeParser
from app.ingestion.source_registry import ParsedSegment, infer_source_type_from_filename
from app.vector_store.collections import VectorRecord
from app.vector_store.milvus_client import VectorStoreClient

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        db: Session,
        vector_store: VectorStoreClient,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.db = db
        self.sources = SourceRepository(db)
        self.chunks = ChunkRepository(db)
        self.vector_store = vector_store
        self.embedding_service = embedding_service or EmbeddingService()
        self.audio_parser = AudioParser()
        self.youtube_parser = YouTubeParser()

    @staticmethod
    def checksum_bytes(content: bytes) -> str:
        digest = hashlib.sha256()
        digest.update(content)
        return digest.hexdigest()

    def create_source_from_file(
        self,
        user_id: str,
        notebook_id: str,
        filename: str,
        path: Path,
        checksum: str,
    ) -> Source:
        source_type = infer_source_type_from_filename(filename)
        return self.sources.create(
            user_id=user_id,
            notebook_id=notebook_id,
            name=filename,
            source_type=source_type.value,
            path_or_url=str(path),
            checksum=checksum,
            metadata_json={"source": "upload"},
        )

    def create_source_from_url(self, user_id: str, notebook_id: str, url: str, source_type: SourceType) -> Source:
        return self.sources.create(
            user_id=user_id,
            notebook_id=notebook_id,
            name=url,
            source_type=source_type.value,
            path_or_url=url,
            checksum=self.checksum_bytes(url.encode("utf-8")),
            metadata_json={"source": "url"},
        )

    def ingest_source(self, source: Source) -> int:
        self.sources.set_status(source, SourceStatus.PROCESSING)
        try:
            parsed_segments = self._parse_source(source)
            chunk_rows = self._chunk_segments(source=source, segments=parsed_segments)
            created_chunks = self.chunks.bulk_create(
                source_id=source.id,
                user_id=source.user_id,
                notebook_id=source.notebook_id or "",
                rows=chunk_rows,
            )
            try:
                embeddings = self.embedding_service.embed_texts([row[1] for row in chunk_rows])
            except Exception as exc:  # noqa: BLE001
                raise AppError(
                    code="EMBEDDING_FAILED",
                    message="Failed to generate embeddings",
                    status_code=500,
                    details={"failure_stage": "embed"},
                ) from exc
            records = self._build_vector_records(source=source, chunk_rows=chunk_rows, chunk_ids=[chunk.id for chunk in created_chunks], embeddings=embeddings)
            try:
                self.vector_store.upsert(records)
            except Exception as exc:  # noqa: BLE001
                raise AppError(
                    code="VECTOR_STORE_FAILED",
                    message="Failed to store vectors",
                    status_code=500,
                    details={"failure_stage": "store"},
                ) from exc
            metadata = {"chunks": str(len(created_chunks)), "status": "ready"}
            self.sources.set_status(source, SourceStatus.READY, metadata_json=metadata)
            return len(created_chunks)
        except AppError as exc:
            self._mark_failed_source(source=source, error=exc)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ingestion failed for source_id=%s", source.id)
            wrapped = AppError(
                code="INGESTION_FAILED",
                message="Ingestion failed unexpectedly",
                status_code=500,
                details={"failure_stage": "store"},
            )
            self._mark_failed_source(source=source, error=wrapped)
            raise wrapped from exc

    def _parse_source(self, source: Source) -> list[ParsedSegment]:
        source_type = SourceType(source.source_type)
        if source_type == SourceType.PDF:
            return parse_pdf(Path(source.path_or_url))
        if source_type == SourceType.TEXT:
            return parse_text(Path(source.path_or_url))
        if source_type == SourceType.MARKDOWN:
            return parse_markdown(Path(source.path_or_url))
        if source_type == SourceType.AUDIO:
            return self.audio_parser.parse(Path(source.path_or_url))
        if source_type == SourceType.WEB:
            return parse_web_url(source.path_or_url)
        if source_type == SourceType.YOUTUBE:
            work_dir = Path(source.path_or_url)
            if work_dir.exists():
                return self.youtube_parser.parse(url=source.metadata_json.get("url", ""), work_dir=work_dir)
            temp_dir = Path("data/processed") / source.id
            temp_dir.mkdir(parents=True, exist_ok=True)
            return self.youtube_parser.parse(url=source.path_or_url, work_dir=temp_dir)
        raise AppError(code="UNSUPPORTED_SOURCE", message=f"Unsupported source type: {source_type.value}", status_code=400)

    def _chunk_segments(
        self,
        source: Source,
        segments: list[ParsedSegment],
    ) -> list[tuple[int, str, int, dict[str, str | int | float | None]]]:
        if not segments:
            raise AppError(
                code="EMPTY_SOURCE",
                message="Source has no parseable text",
                status_code=400,
                details={"failure_stage": "chunk"},
            )

        rows: list[tuple[int, str, int, dict[str, str | int | float | None]]] = []
        policy = markdown_policy() if source.source_type == SourceType.MARKDOWN.value else default_policy()
        for segment in segments:
            segment_chunks = self._chunk_single_segment(source=source, segment=segment, policy=policy)
            for item in segment_chunks:
                rows.append((len(rows), item, len(item.split()), self._normalize_citation(segment.citation)))
        return rows

    def _chunk_single_segment(
        self,
        source: Source,
        segment: ParsedSegment,
        policy: ChunkPolicy,
    ) -> list[str]:
        if source.source_type == SourceType.MARKDOWN.value:
            return chunk_markdown_sections(segment.text, policy=policy)
        return chunk_text(segment.text, policy=policy)

    @staticmethod
    def _normalize_citation(
        citation: dict[str, str | int | float | None],
    ) -> dict[str, str | int | float | None]:
        normalized: dict[str, str | int | float | None] = {}
        for key, value in citation.items():
            if isinstance(value, str):
                normalized[key] = value
            elif isinstance(value, int):
                normalized[key] = value
            elif isinstance(value, float):
                normalized[key] = value
            elif value is None:
                normalized[key] = None
        return normalized

    def _build_vector_records(
        self,
        source: Source,
        chunk_rows: list[tuple[int, str, int, dict[str, str | int | float | None]]],
        chunk_ids: list[str],
        embeddings: list[list[float]],
    ) -> list[VectorRecord]:
        records: list[VectorRecord] = []
        for idx, row in enumerate(chunk_rows):
            _, text, _, citation = row
            record = VectorRecord(
                chunk_id=chunk_ids[idx],
                source_id=source.id,
                user_id=source.user_id,
                notebook_id=source.notebook_id or "",
                text=text,
                vector=embeddings[idx],
                metadata=citation,
            )
            records.append(record)
        return records

    def _mark_failed_source(self, source: Source, error: AppError) -> None:
        failure_stage = _failure_stage_for_code(error.code, error.details)
        metadata: dict[str, Any] = dict(source.metadata_json)
        metadata["status"] = "failed"
        metadata["failure_code"] = error.code
        metadata["failure_stage"] = failure_stage
        metadata["failure_detail"] = _sanitize_failure_detail(error.message)
        self.sources.set_status(source, SourceStatus.FAILED, metadata_json=metadata)


def _failure_stage_for_code(code: str, details: dict[str, Any]) -> str:
    detail_stage = details.get("failure_stage")
    if isinstance(detail_stage, str) and detail_stage:
        return detail_stage
    fetch_codes = {"WEB_FETCH_FAILED", "WEB_TIMEOUT", "YOUTUBE_FETCH_FAILED"}
    parse_codes = {
        "PDF_OPEN_FAILED",
        "PDF_EMPTY",
        "PDF_PARSE_FAILED",
        "WEB_PARSE_FAILED",
        "YOUTUBE_SUBTITLE_MISSING",
        "YOUTUBE_AUDIO_DOWNLOAD_FAILED",
        "YOUTUBE_TRANSCRIBE_FAILED",
        "AUDIO_PARSE_FAILED",
        "AUDIO_TIMEOUT",
        "AUDIO_UPSTREAM_FAILED",
        "UNSUPPORTED_SOURCE",
    }
    if code in fetch_codes:
        return "fetch"
    if code in parse_codes:
        return "parse"
    if code.startswith("CHUNK") or code == "EMPTY_SOURCE":
        return "chunk"
    if code.startswith("EMBEDDING"):
        return "embed"
    return "store"


def _sanitize_failure_detail(message: str) -> str:
    clean = message.strip().replace("\n", " ")
    return clean[:400]
