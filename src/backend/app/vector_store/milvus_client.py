from __future__ import annotations

import logging
import re
from math import sqrt
from typing import Any

from app.core.config import get_settings
from app.vector_store.collections import VectorRecord

logger = logging.getLogger(__name__)

_SAFE_MILVUS_VALUE_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _safe_milvus_value(value: str, field_name: str) -> str:
    """Validate that a value is safe to interpolate into a Milvus filter expression.

    Rejects any value containing quotes, backslashes, or other special characters
    that could break out of a Milvus expression string — preventing expression injection.
    """
    if not _SAFE_MILVUS_VALUE_RE.match(value):
        raise ValueError(
            f"Unsafe value for Milvus filter field '{field_name}': "
            f"must be alphanumeric, hyphens, or underscores only"
        )
    return value


class VectorStoreClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._in_memory: dict[str, VectorRecord] = {}
        self._milvus_enabled = False
        self._milvus_collection: Any | None = None
        self._milvus_detail = "Milvus initialization not attempted"
        self._milvus_reason = "unknown"
        self._initialize_milvus_if_possible()

    def _initialize_milvus_if_possible(self) -> None:
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
        except ImportError as exc:
            self._milvus_detail = f"Milvus import failure: {exc}"
            self._milvus_reason = "import_failure"
            logger.warning("pymilvus not available; using in-memory vector store")
            return

        try:
            connections.connect(alias="default", uri=self.settings.milvus_uri)
            if utility.has_collection(self.settings.milvus_collection):
                self._milvus_collection = Collection(self.settings.milvus_collection)
            else:
                fields = [
                    FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
                    FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
                    FieldSchema(name="notebook_id", dtype=DataType.VARCHAR, max_length=64),
                    FieldSchema(name="source_id", dtype=DataType.VARCHAR, max_length=64),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.settings.embedding_dimension),
                    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                ]
                schema = CollectionSchema(fields=fields, description="NotebookLM chunks")
                self._milvus_collection = Collection(name=self.settings.milvus_collection, schema=schema)
                self._milvus_collection.create_index(
                    field_name="embedding",
                    index_params={"index_type": "AUTOINDEX", "metric_type": "COSINE", "params": {}},
                )
            self._milvus_collection.load()
            self._milvus_enabled = True
            self._milvus_detail = "Milvus reachable"
            self._milvus_reason = "connected"
        except Exception as exc:  # noqa: BLE001
            logger.warning("Milvus unavailable, using in-memory fallback: %s", exc)
            self._milvus_enabled = False
            self._milvus_detail = f"Milvus connection failure: {exc}"
            self._milvus_reason = "connection_failure"

    def upsert(self, records: list[VectorRecord]) -> None:
        if self._milvus_enabled and self._milvus_collection is not None:
            self._upsert_milvus(records)
            return
        for record in records:
            self._in_memory[record.chunk_id] = record

    def _upsert_milvus(self, records: list[VectorRecord]) -> None:
        assert self._milvus_collection is not None
        chunk_ids = [record.chunk_id for record in records]
        user_ids = [record.user_id for record in records]
        notebook_ids = [record.notebook_id for record in records]
        source_ids = [record.source_id for record in records]
        vectors = [self._normalize_dimension(record.vector, self.settings.embedding_dimension) for record in records]
        texts = [record.text[:65000] for record in records]
        self._milvus_collection.insert([chunk_ids, user_ids, notebook_ids, source_ids, vectors, texts])
        self._milvus_collection.flush()

    def search(self, user_id: str, notebook_id: str, query_vector: list[float], top_k: int) -> list[VectorRecord]:
        if self._milvus_enabled and self._milvus_collection is not None:
            return self._search_milvus(user_id=user_id, notebook_id=notebook_id, query_vector=query_vector, top_k=top_k)
        return self._search_in_memory(user_id=user_id, notebook_id=notebook_id, query_vector=query_vector, top_k=top_k)

    def _search_milvus(self, user_id: str, notebook_id: str, query_vector: list[float], top_k: int) -> list[VectorRecord]:
        assert self._milvus_collection is not None
        safe_uid = _safe_milvus_value(user_id, "user_id")
        safe_nid = _safe_milvus_value(notebook_id, "notebook_id")
        search_res = self._milvus_collection.search(
            data=[self._normalize_dimension(query_vector, self.settings.embedding_dimension)],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {}},
            limit=top_k,
            expr=f'user_id == "{safe_uid}" and notebook_id == "{safe_nid}"',
            output_fields=["chunk_id", "user_id", "notebook_id", "source_id", "text"],
        )
        results: list[VectorRecord] = []
        for hits in search_res:
            for hit in hits:
                entity = hit.entity
                results.append(
                    VectorRecord(
                        chunk_id=str(entity.get("chunk_id")),
                        user_id=str(entity.get("user_id")),
                        notebook_id=str(entity.get("notebook_id")),
                        source_id=str(entity.get("source_id")),
                        text=str(entity.get("text")),
                        vector=[],
                        metadata={"score": float(hit.score)},
                    )
                )
        return results

    def _search_in_memory(self, user_id: str, notebook_id: str, query_vector: list[float], top_k: int) -> list[VectorRecord]:
        scored: list[tuple[float, VectorRecord]] = []
        for record in self._in_memory.values():
            if record.user_id != user_id or record.notebook_id != notebook_id:
                continue
            score = _cosine_similarity(query_vector, record.vector)
            scored.append((score, record))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:top_k]]

    def delete_source(self, user_id: str, source_id: str) -> None:
        if self._milvus_enabled and self._milvus_collection is not None:
            safe_uid = _safe_milvus_value(user_id, "user_id")
            safe_sid = _safe_milvus_value(source_id, "source_id")
            expr = f'user_id == "{safe_uid}" and source_id == "{safe_sid}"'
            self._milvus_collection.delete(expr)
            self._milvus_collection.flush()
            return

        to_delete = [chunk_id for chunk_id, rec in self._in_memory.items() if rec.user_id == user_id and rec.source_id == source_id]
        for chunk_id in to_delete:
            self._in_memory.pop(chunk_id, None)

    def is_milvus_ready(self) -> bool:
        return self._milvus_enabled

    def milvus_diagnostics(self) -> tuple[str, str]:
        return self._milvus_reason, self._milvus_detail

    @staticmethod
    def _normalize_dimension(vector: list[float], target_dim: int = 768) -> list[float]:
        if len(vector) == target_dim:
            return vector
        if len(vector) > target_dim:
            return vector[:target_dim]
        return vector + [0.0] * (target_dim - len(vector))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dim = min(len(a), len(b))
    numerator = sum(a[idx] * b[idx] for idx in range(dim))
    left = sqrt(sum(value * value for value in a[:dim]))
    right = sqrt(sum(value * value for value in b[:dim]))
    if left == 0 or right == 0:
        return 0.0
    return numerator / (left * right)
