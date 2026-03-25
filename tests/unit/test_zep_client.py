from __future__ import annotations

import requests
import pytest

from app.db.session import SessionLocal
from app.memory.memory_service import MemoryService


def test_store_message_falls_back_gracefully_when_zep_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """When Zep is unreachable, store_message should log a warning and NOT raise."""

    def _raise_timeout(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        raise requests.Timeout("timeout")

    monkeypatch.setattr("app.memory.zep_client.requests.post", _raise_timeout)
    db = SessionLocal()
    try:
        service = MemoryService(db)
        # Should NOT raise — graceful fallback
        service.store_message(user_id="user1", session_id="session1", role="user", content="hello")
    finally:
        db.close()


def test_summarize_session_falls_back_to_local_when_zep_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """When Zep is unreachable, summarize_session should return local fallback."""

    def _raise_request_error(*args: object, **kwargs: object) -> object:
        _ = (args, kwargs)
        raise requests.RequestException("network failure")

    monkeypatch.setattr("app.memory.zep_client.requests.get", _raise_request_error)
    db = SessionLocal()
    try:
        service = MemoryService(db)
        summary, provider = service.summarize_session(user_id="user1", session_id="session1")
        assert provider == "local"
        assert isinstance(summary, str)
    finally:
        db.close()
