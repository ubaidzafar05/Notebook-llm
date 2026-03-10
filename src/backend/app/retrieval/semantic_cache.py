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
    For this implementation, we use a deterministic hash of the user's question combined
    with the source context IDs to ensure we don't serve a stale answer if the context changes.
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

    def store_answer(self, question: str, chunk_ids: list[str], answer: str, citations: list[dict[str, Any]]) -> None:
        if self.redis is None:
            return
        cache_key = self._build_key(question, chunk_ids)
        payload = {
            "answer": answer,
            "citations": citations,
        }
        try:
            self.redis.setex(cache_key, self.ttl_seconds, json.dumps(payload))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to write to SemanticCache: %s", exc)

    def _build_key(self, question: str, chunk_ids: list[str]) -> str:
        normalized_q = question.strip().lower()
        context_fingerprint = ",".join(sorted(chunk_ids))
        raw_string = f"{normalized_q}|{context_fingerprint}"
        hash_val = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
        return namespaced_key("semantic_cache", hash_val)
