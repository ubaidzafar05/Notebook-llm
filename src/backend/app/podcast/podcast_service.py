from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.models import Chunk, PodcastJob, PodcastStatus, Source
from app.db.repositories.job_repo import PodcastRepository
from app.db.repositories.source_repo import ChunkRepository, SourceRepository
from app.podcast.audio_mixer import AudioMixer
from app.podcast.script_generator import ScriptGenerator
from app.podcast.tts_service import TtsService


class PodcastService:
    def __init__(self, db: Session) -> None:
        self.settings = get_settings()
        self.repo = PodcastRepository(db)
        self.chunks = ChunkRepository(db)
        self.sources = SourceRepository(db)
        self.script_generator = ScriptGenerator()
        self.tts_service = TtsService()
        self.mixer = AudioMixer()

    def create_job(
        self,
        user_id: str,
        notebook_id: str,
        source_ids: list[str],
        voice_label: str | None = None,
        retried_from_podcast_id: str | None = None,
    ) -> str:
        podcast = self.repo.create(
            user_id=user_id,
            notebook_id=notebook_id,
            source_ids=source_ids,
            voice_label=voice_label,
            retried_from_podcast_id=retried_from_podcast_id,
        )
        return podcast.id

    def process_job(self, user_id: str, podcast_id: str, title: str, voice_label: str | None = None) -> None:
        podcast = self.repo.get_for_user(podcast_id=podcast_id, user_id=user_id)
        if podcast is None:
            return
        if voice_label is not None and voice_label.strip():
            podcast.voice_label = voice_label.strip()
        podcast.status = PodcastStatus.PROCESSING.value
        self.repo.save(podcast)

        chunks = self.chunks.list_for_sources(
            source_ids=podcast.source_ids_json,
            user_id=user_id,
            notebook_id=podcast.notebook_id,
        )
        if not chunks:
            raise AppError(
                code="PODCAST_NO_SOURCE_CONTEXT",
                message="No source chunks available for podcast generation",
                status_code=400,
            )
        sources = self.sources.list_by_ids_for_notebook(
            user_id=user_id,
            notebook_id=podcast.notebook_id,
            source_ids=podcast.source_ids_json,
        )
        context = _build_podcast_context(
            sources=sources,
            chunks=chunks,
            max_chars=self.settings.podcast_context_max_chars,
            chunks_per_source=self.settings.podcast_chunks_per_source,
            excerpt_chars=self.settings.podcast_chunk_excerpt_chars,
        )
        script, _ = self.script_generator.generate(title=title, source_context=context)
        tracks = self.tts_service.synthesize_script(
            script=script,
            output_dir=Path("outputs/podcasts") / podcast.id,
            voice_label=podcast.voice_label,
        )
        output_path = Path("outputs/podcasts") / f"{podcast.id}.mp3"
        duration_ms = self.mixer.merge_tracks(tracks=tracks, output_path=output_path)

        podcast.script = script.as_text()
        podcast.output_path = str(output_path)
        podcast.duration_ms = duration_ms
        podcast.status = PodcastStatus.COMPLETED.value
        self.repo.save(podcast)

    def fail_job(
        self,
        user_id: str,
        podcast_id: str,
        message: str,
        failure_code: str | None = None,
    ) -> None:
        podcast = self.repo.get_for_user(podcast_id=podcast_id, user_id=user_id)
        if podcast is None:
            return
        podcast.status = PodcastStatus.FAILED.value
        podcast.failure_code = failure_code
        podcast.failure_detail = message
        podcast.error_message = message
        self.repo.save(podcast)

    def get_job(self, user_id: str, podcast_id: str) -> PodcastJob | None:
        return self.repo.get_for_user(podcast_id=podcast_id, user_id=user_id)


def _build_podcast_context(
    *,
    sources: list[Source],
    chunks: list[Chunk],
    max_chars: int,
    chunks_per_source: int,
    excerpt_chars: int,
) -> str:
    # REASONING:
    # 1. Podcast prompts should receive a compact source brief, not raw notebook chunk dumps.
    # 2. Grouping excerpts by source preserves provenance while keeping the token budget bounded.
    # 3. Hard caps on section count and chars prevent local Ollama timeouts on long notebooks.
    chunks_by_source = _group_chunks_by_source(chunks)
    remaining_chars = max(max_chars, 500)
    sections: list[str] = []
    for source in sources:
        section = _build_source_section(
            source=source,
            chunks=chunks_by_source.get(source.id, []),
            chunks_per_source=chunks_per_source,
            excerpt_chars=excerpt_chars,
        )
        if not section:
            continue
        if len(section) > remaining_chars and sections:
            break
        clipped_section = _clip_section(section=section, max_chars=remaining_chars)
        sections.append(clipped_section)
        remaining_chars -= len(clipped_section) + 2
        if remaining_chars <= 0:
            break
    return "\n\n".join(sections)


def _group_chunks_by_source(chunks: list[Chunk]) -> dict[str, list[Chunk]]:
    grouped: dict[str, list[Chunk]] = {}
    for chunk in sorted(chunks, key=lambda item: (item.source_id, item.chunk_index)):
        grouped.setdefault(chunk.source_id, []).append(chunk)
    return grouped


def _build_source_section(
    *,
    source: Source,
    chunks: list[Chunk],
    chunks_per_source: int,
    excerpt_chars: int,
) -> str:
    if not chunks:
        return ""
    metadata = source.metadata_json if isinstance(source.metadata_json, dict) else {}
    summary = _clean_excerpt(str(metadata.get("summary", "")), excerpt_chars)
    lines = [f"Source: {source.name}", f"Type: {source.source_type}"]
    if summary:
        lines.append(f"Summary: {summary}")
    lines.append("Key excerpts:")
    for index, chunk in enumerate(chunks[: max(chunks_per_source, 1)], start=1):
        citation = chunk.citation_json if isinstance(chunk.citation_json, dict) else {}
        page = citation.get("page")
        prefix = f"{index}. page {page}: " if page is not None else f"{index}. "
        lines.append(prefix + _clean_excerpt(chunk.text, excerpt_chars))
    return "\n".join(lines)


def _clean_excerpt(text: str, limit: int) -> str:
    normalized = " ".join(text.split()).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(limit - 16, 0)].rstrip() + " (truncated)"


def _clip_section(*, section: str, max_chars: int) -> str:
    if len(section) <= max_chars:
        return section
    clipped = section[: max(max_chars - 16, 0)].rstrip()
    return clipped + " (truncated)"
