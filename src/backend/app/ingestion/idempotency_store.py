from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.redis_client import get_redis_client, namespaced_key


class IdempotencyStore:
    def __init__(self) -> None:
        self.settings = get_settings()

    def load(self, user_id: str, operation: str, idempotency_key: str) -> dict[str, Any] | None:
        redis = self._redis()
        key = _cache_key(user_id=user_id, operation=operation, idempotency_key=idempotency_key)
        raw = redis.get(key)
        if raw is None:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AppError(
                code="IDEMPOTENCY_UNAVAILABLE",
                message="Idempotency cache payload is corrupted",
                status_code=503,
            ) from exc
        if not isinstance(parsed, dict):
            return None
        return parsed

    def store(self, user_id: str, operation: str, idempotency_key: str, payload: dict[str, Any]) -> None:
        redis = self._redis()
        key = _cache_key(user_id=user_id, operation=operation, idempotency_key=idempotency_key)
        serialized = json.dumps(payload, ensure_ascii=True)
        redis.setex(key, self.settings.idempotency_ttl_seconds, serialized)

    def _redis(self) -> Any:
        try:
            return get_redis_client()
        except AppError as exc:
            raise AppError(
                code="IDEMPOTENCY_UNAVAILABLE",
                message="Idempotency store is unavailable",
                status_code=503,
                details={"cause": exc.code},
            ) from exc


def _cache_key(user_id: str, operation: str, idempotency_key: str) -> str:
    return namespaced_key("idem", user_id, operation, idempotency_key.strip())
