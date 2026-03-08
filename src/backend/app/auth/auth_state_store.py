from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.redis_client import atomic_getdel, get_redis_client, namespaced_key


class AuthStateStore:
    def __init__(self) -> None:
        self.settings = get_settings()

    def save_oauth_state(self, state: str) -> None:
        redis = self._redis()
        key = namespaced_key("auth", "oauth_state", state)
        redis.setex(key, self.settings.oauth_state_ttl_seconds, "1")

    def consume_oauth_state(self, state: str) -> bool:
        redis = self._redis()
        key = namespaced_key("auth", "oauth_state", state)
        value = atomic_getdel(redis, key)
        return value == "1"

    def save_oauth_exchange(self, code: str, payload: dict[str, str]) -> None:
        redis = self._redis()
        key = namespaced_key("auth", "oauth_code", code)
        body = json.dumps(payload, ensure_ascii=True)
        redis.setex(key, self.settings.oauth_exchange_code_ttl_seconds, body)

    def consume_oauth_exchange(self, code: str) -> dict[str, str] | None:
        redis = self._redis()
        key = namespaced_key("auth", "oauth_code", code)
        body = atomic_getdel(redis, key)
        if body is None:
            return None
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AppError(
                code="AUTH_STATE_UNAVAILABLE",
                message="OAuth exchange state is corrupted",
                status_code=503,
            ) from exc
        if not isinstance(parsed, dict):
            return None
        return {str(key): str(value) for key, value in parsed.items()}

    def revoke_refresh_token(self, refresh_token: str, ttl_seconds: int | None = None) -> None:
        redis = self._redis()
        ttl = ttl_seconds if ttl_seconds is not None else self.settings.jwt_refresh_expires_minutes * 60
        hashed = _hash_token(refresh_token)
        key = namespaced_key("auth", "revoked_refresh", hashed)
        redis.setex(key, max(ttl, 60), "1")

    def is_refresh_token_revoked(self, refresh_token: str) -> bool:
        redis = self._redis()
        hashed = _hash_token(refresh_token)
        key = namespaced_key("auth", "revoked_refresh", hashed)
        return int(redis.exists(key)) == 1

    def _redis(self) -> Any:
        try:
            return get_redis_client()
        except AppError as exc:
            raise AppError(
                code="AUTH_STATE_UNAVAILABLE",
                message="Auth state store is unavailable",
                status_code=503,
                details={"cause": exc.code},
            ) from exc


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
