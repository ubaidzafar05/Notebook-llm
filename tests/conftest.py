from __future__ import annotations

# ruff: noqa: E402

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import text

TEST_DB_PATH = Path(__file__).resolve().parent / ".tmp" / "test.db"
TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["ZEP_API_KEY"] = "test-zep-key"
os.environ["ZEP_PROJECT_ID"] = "00000000-0000-4000-8000-000000000001"

from app.core.config import reset_settings_cache

reset_settings_cache()

from app.db.models import Base
from app.db.migration_runner import upgrade_to_head
from app.db.session import engine
from app.main import app


class _StubResponse:
    def __init__(self, status_code: int, body: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict[str, Any]:
        return self._body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


def _fake_zep_post(*args: Any, **kwargs: Any) -> _StubResponse:
    url = str(args[0]) if args else ""
    _ = kwargs
    if "api.getzep.com" not in url:
        raise requests.RequestException("network disabled in test transport")
    return _StubResponse(status_code=200, body={})


def _fake_zep_get(*args: Any, **kwargs: Any) -> _StubResponse:
    url = str(args[0]) if args else ""
    _ = kwargs
    if "api.getzep.com" not in url:
        raise requests.RequestException("network disabled in test transport")
    if url.endswith("/memory"):
        return _StubResponse(status_code=200, body={"summary": "Test summary"})
    return _StubResponse(status_code=200, body={"id": os.environ["ZEP_PROJECT_ID"]})


@pytest.fixture(autouse=True)
def mock_zep_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.memory.zep_client.requests.post", _fake_zep_post)
    monkeypatch.setattr("app.memory.zep_client.requests.get", _fake_zep_get)


@pytest.fixture(autouse=True)
def reset_db() -> None:
    from app.core import redis_client

    redis_client._test_redis_singleton = None
    engine.dispose()
    _reset_sqlite_test_database()
    upgrade_to_head(str(engine.url))


def _reset_sqlite_test_database() -> None:
    if engine.url.get_backend_name() != "sqlite":
        Base.metadata.drop_all(bind=engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        return

    db_path = Path(engine.url.database or "")
    if db_path.exists():
        db_path.unlink()
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = db_path.with_name(f"{db_path.name}{suffix}")
        if sidecar.exists():
            sidecar.unlink()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
