from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.core.redis_client import get_redis_client, namespaced_key

logger = logging.getLogger(__name__)


class SemanticCacheService:
    """
    Stores and retrieves LLM responses based on exactly matching questions and context IDs.
    Uses a deterministic hash of the user's question combined with the source context IDs.

    Maintains a reverse index (source_id → set of cache keys) so that invalidation
    on source delete only removes affected entries instead of flushing the whole cache.
    """

    def __init__(self) -> None:
        try:
            self.redis = get_redis_client()
        except Exception as exc:  # noqa: BLE001
            logger.warning("SemanticCache disabled: redis unavailable (%s)", exc)
            self.redis = None
        self.ttl_seconds = 86400  # 24 hours

    def get_cached_answer(self, question: str, chunk_ids: list[str]) -> tuple[str, list[dict[str, Any]]] | None:
        if self.redis is None:
            return None
        cache_key = self._build_key(question, chunk_ids)
        try:
            raw = self.redis.get(cache_key)
            if not raw:
                return None
            data = json.loads(raw)
            logger.info("SemanticCache hit for question: %s", question)
            return data["answer"], data["citations"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read from SemanticCache: %s", exc)
            return None

    def store_answer(
        self,
        question: str,
        chunk_ids: list[str],
        answer: str,
        citations: list[dict[str, Any]],
        source_ids: list[str] | None = None,
    ) -> None:
        if self.redis is None:
            return
        cache_key = self._build_key(question, chunk_ids)
        payload = {"answer": answer, "citations": citations}
        try:
            self.redis.setex(cache_key, self.ttl_seconds, json.dumps(payload))
            # Maintain reverse index: source_id → {cache_key, ...}
            if source_ids:
                for sid in set(source_ids):
                    idx_key = self._source_index_key(sid)
                    self.redis.sadd(idx_key, cache_key)
                    self.redis.expire(idx_key, self.ttl_seconds * 2)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to write to SemanticCache: %s", exc)

    def invalidate_for_source(self, source_id: str) -> None:
        """Remove cache entries that reference chunks from the deleted source.

        Uses the reverse index (source_id → set of cache keys) for targeted
        invalidation.  Falls back to a conservative full flush if no index exists.
        """
        if self.redis is None:
            return
        idx_key = self._source_index_key(source_id)
        try:
            members = self.redis.smembers(idx_key)
            if members:
                # Targeted deletion
                for cache_key in members:
                    self.redis.delete(cache_key)
                self.redis.delete(idx_key)
                logger.info(
                    "SemanticCache: targeted invalidation removed %d entries for source %s",
                    len(members),
                    source_id,
                )
            else:
                # No index found — conservative full flush for safety
                self._flush_all()
                logger.info("SemanticCache: full flush for deleted source %s (no reverse index)", source_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SemanticCache invalidation failed: %s", exc)

    def _flush_all(self) -> None:
        """Remove all semantic_cache:* keys via SCAN."""
        if self.redis is None:
            return
        prefix = namespaced_key("semantic_cache", "")
        cursor: int = 0
        while True:
            cursor, keys = self.redis.scan(cursor=cursor, match=f"{prefix}*", count=200)
            if keys:
                self.redis.delete(*keys)
            if cursor == 0:
                break

    def _build_key(self, question: str, chunk_ids: list[str]) -> str:
        normalized_q = question.strip().lower()
        context_fingerprint = ",".join(sorted(chunk_ids))
        raw_string = f"{normalized_q}|{context_fingerprint}"
        hash_val = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
        return namespaced_key("semantic_cache", hash_val)

    def _source_index_key(self, source_id: str) -> str:
        return namespaced_key("semantic_cache_idx", f"source:{source_id}")
