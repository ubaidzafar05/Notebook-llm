from __future__ import annotations

import requests
import pytest

from app.core.exceptions import AppError
from app.db.session import SessionLocal
from app.memory.memory_service import MemoryService


def test_store_message_raises_typed_error_when_zep_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_timeout(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        raise requests.Timeout("timeout")

    monkeypatch.setattr("app.memory.zep_client.requests.post", _raise_timeout)
    db = SessionLocal()
    try:
        service = MemoryService(db)
        with pytest.raises(AppError) as error:
            service.store_message(user_id="user1", session_id="session1", role="user", content="hello")
    finally:
        db.close()
    assert error.value.code == "ZEP_UPSERT_TIMEOUT"
    assert error.value.status_code == 504


def test_summarize_session_raises_typed_error_when_zep_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_request_error(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        raise requests.RequestException("network failure")

    monkeypatch.setattr("app.memory.zep_client.requests.get", _raise_request_error)
    db = SessionLocal()
    try:
        service = MemoryService(db)
        with pytest.raises(AppError) as error:
            service.summarize_session(user_id="user1", session_id="session1")
    finally:
        db.close()
    assert error.value.code == "ZEP_UNREACHABLE"
    assert error.value.status_code == 502
