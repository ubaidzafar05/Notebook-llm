from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
from redis import Redis

from app.core.config import get_settings
from app.core.exceptions import AppError

_test_redis_singleton: _InMemoryRedis | None = None
_test_async_redis_singleton: _InMemoryAsyncRedis | None = None


def get_redis_client() -> Any:
    settings = get_settings()
    if settings.environment == "test":
        return _get_test_redis()
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            code="REDIS_UNAVAILABLE",
            message="Redis dependency is unavailable",
            status_code=503,
        ) from exc


def get_async_redis_client() -> Any:
    settings = get_settings()
    if settings.environment == "test":
        return _get_test_async_redis()
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        return client
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            code="REDIS_UNAVAILABLE",
            message="Redis dependency is unavailable",
            status_code=503,
        ) from exc


def namespaced_key(*segments: str) -> str:
    settings = get_settings()
    clean = [segment.strip() for segment in segments if segment.strip()]
    return ":".join([settings.redis_key_prefix, *clean])


def atomic_getdel(client: Any, key: str) -> str | None:
    try:
        value = client.getdel(key)
        if isinstance(value, str):
            return value
        return None
    except Exception:
        with client.pipeline(transaction=True) as pipe:
            pipe.get(key)
            pipe.delete(key)
            raw_value, _ = pipe.execute()
            if isinstance(raw_value, str):
                return raw_value
            return None


def _get_test_redis() -> Any:
    global _test_redis_singleton
    if _test_redis_singleton is None:
        _test_redis_singleton = _InMemoryRedis()
    return _test_redis_singleton


def _get_test_async_redis() -> Any:
    global _test_async_redis_singleton
    if _test_async_redis_singleton is None:
        _test_async_redis_singleton = _InMemoryAsyncRedis()
    return _test_async_redis_singleton


@dataclass(slots=True)
class _MemoryValue:
    value: str
    expires_at: datetime | None


class _MemoryPipeline:
    def __init__(self, store: _InMemoryRedis) -> None:
        self.store = store
        self.commands: list[tuple[str, str]] = []

    def __enter__(self) -> _MemoryPipeline:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.commands.clear()

    def get(self, key: str) -> None:
        self.commands.append(("get", key))

    def delete(self, key: str) -> None:
        self.commands.append(("delete", key))

    def execute(self) -> tuple[str | None, int]:
        first: str | None = None
        second = 0
        for index, (cmd, key) in enumerate(self.commands):
            if cmd == "get":
                value = self.store.get(key)
                if index == 0:
                    first = value
            if cmd == "delete":
                second = self.store.delete(key)
        return first, second


class _InMemoryRedis:
    def __init__(self) -> None:
        self.rows: dict[str, _MemoryValue] = {}
        self.sets: dict[str, set[str]] = {}

    def ping(self) -> bool:
        return True

    def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        self.rows[key] = _MemoryValue(value=value, expires_at=expires_at)
        return True

    def get(self, key: str) -> str | None:
        row = self.rows.get(key)
        if row is None:
            return None
        if row.expires_at is not None and row.expires_at <= datetime.now(UTC):
            self.rows.pop(key, None)
            return None
        return row.value

    def getdel(self, key: str) -> str | None:
        value = self.get(key)
        self.rows.pop(key, None)
        return value

    def exists(self, key: str) -> int:
        return 1 if self.get(key) is not None else 0

    def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self.rows:
                count += 1
            self.rows.pop(key, None)
            self.sets.pop(key, None)
        return count

    def sadd(self, key: str, *members: str) -> int:
        if key not in self.sets:
            self.sets[key] = set()
        before = len(self.sets[key])
        self.sets[key].update(members)
        return len(self.sets[key]) - before

    def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    def expire(self, key: str, ttl_seconds: int) -> bool:
        # For sets tracked in self.sets — just a no-op in tests
        return True

    def scan(self, cursor: int = 0, match: str = "", count: int = 100) -> tuple[int, list[str]]:
        import fnmatch

        pattern = match or "*"
        all_keys = list(self.rows.keys()) + list(self.sets.keys())
        matched = [k for k in all_keys if fnmatch.fnmatch(k, pattern)]
        return 0, matched

    def pipeline(self, transaction: bool = True) -> _MemoryPipeline:
        return _MemoryPipeline(self)


class _InMemoryAsyncRedis:
    def __init__(self) -> None:
        self.rows: dict[str, _MemoryValue] = {}

    async def ping(self) -> bool:
        return True

    async def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        self.rows[key] = _MemoryValue(value=value, expires_at=expires_at)
        return True

    async def get(self, key: str) -> str | None:
        row = self.rows.get(key)
        if row is None:
            return None
        if row.expires_at is not None and row.expires_at <= datetime.now(UTC):
            self.rows.pop(key, None)
            return None
        return row.value

    async def getdel(self, key: str) -> str | None:
        value = await self.get(key)
        self.rows.pop(key, None)
        return value

    async def exists(self, key: str) -> int:
        return 1 if (await self.get(key)) is not None else 0

    async def delete(self, key: str) -> int:
        existed = 1 if key in self.rows else 0
        self.rows.pop(key, None)
        return existed

    async def script_load(self, script: str) -> str:
        return "mock_lua_sha"

    async def evalsha(self, sha: str, numkeys: int, *keys_and_args: Any) -> int:
        return 0

    def pipeline(self, transaction: bool = True) -> Any:
        class AsyncPipeline:
            def __init__(self, store: _InMemoryAsyncRedis) -> None:
                self.store = store
            async def __aenter__(self) -> AsyncPipeline:
                return self
            async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
                pass
            def get(self, key: str) -> None:
                pass
            def delete(self, key: str) -> None:
                pass
            async def execute(self) -> tuple[str | None, int]:
                return None, 0
        return AsyncPipeline(self)
