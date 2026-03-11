from __future__ import annotations

import logging
from dataclasses import dataclass

from app.db.repositories.source_repo import ChunkRepository
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.collections import VectorRecord
from app.vector_store.milvus_client import VectorStoreClient

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HybridRetrieveResult:
    records: list[VectorRecord]
    vector_failed: bool


class HybridRetriever:
    def __init__(
        self,
        *,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreClient,
        chunk_repo: ChunkRepository,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.chunk_repo = chunk_repo

    def retrieve(
        self,
        *,
        user_id: str,
        notebook_id: str,
        query: str,
        top_k: int = 8,
        buffer: int = 4,
        lexical_limit: int | None = None,
    ) -> HybridRetrieveResult:
        vector_records, vector_failed = self._vector_candidates(
            user_id=user_id,
            notebook_id=notebook_id,
            query=query,
            top_k=top_k + buffer,
        )
        lexical_records = self._lexical_candidates(
            user_id=user_id,
            notebook_id=notebook_id,
            query=query,
            limit=lexical_limit or (top_k + buffer),
        )
        merged = self._rrf_merge(vector_records, lexical_records, top_k=top_k)
        return HybridRetrieveResult(records=merged, vector_failed=vector_failed)

    def _vector_candidates(
        self,
        *,
        user_id: str,
        notebook_id: str,
        query: str,
        top_k: int,
    ) -> tuple[list[VectorRecord], bool]:
        try:
            query_vector = self.embedding_service.embed_texts([query])[0]
            records = self.vector_store.search(
                user_id=user_id,
                notebook_id=notebook_id,
                query_vector=query_vector,
                top_k=top_k,
            )
            return records, False
        except Exception:  # noqa: BLE001
            logger.exception("Vector retrieval failed notebook_id=%s", notebook_id)
            return [], True

    def _lexical_candidates(
        self,
        *,
        user_id: str,
        notebook_id: str,
        query: str,
        limit: int,
    ) -> list[VectorRecord]:
        rows = self.chunk_repo.lexical_candidates(
            user_id=user_id,
            notebook_id=notebook_id,
            query=query,
            limit=limit,
        )
        return [
            VectorRecord(
                chunk_id=chunk.id,
                source_id=chunk.source_id,
                user_id=chunk.user_id,
                notebook_id=chunk.notebook_id or notebook_id,
                text=chunk.text,
                vector=[],
                metadata=chunk.citation_json,
            )
            for chunk in rows
        ]

    def _rrf_merge(
        self,
        primary: list[VectorRecord],
        secondary: list[VectorRecord],
        *,
        top_k: int,
        k: int = 60,
    ) -> list[VectorRecord]:
        scores: dict[str, float] = {}
        record_map: dict[str, VectorRecord] = {}
        for rank, record in enumerate(primary):
            record_map.setdefault(record.chunk_id, record)
            scores[record.chunk_id] = scores.get(record.chunk_id, 0.0) + 1.0 / (k + rank + 1)
        for rank, record in enumerate(secondary):
            record_map.setdefault(record.chunk_id, record)
            scores[record.chunk_id] = scores.get(record.chunk_id, 0.0) + 1.0 / (k + rank + 1)
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        merged: list[VectorRecord] = []
        for chunk_id, _score in ranked[:top_k]:
            merged.append(record_map[chunk_id])
        return merged
