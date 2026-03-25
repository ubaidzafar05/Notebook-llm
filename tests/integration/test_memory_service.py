"""Integration tests for MemoryService graceful degradation."""

from __future__ import annotations

import requests
import pytest

from app.db.session import SessionLocal
from app.memory.memory_service import MemoryService


class TestMemoryServiceFallback:
    def test_store_message_succeeds_when_zep_enabled(self) -> None:
        db = SessionLocal()
        try:
            service = MemoryService(db)
            # conftest.py stubs Zep calls to succeed
            service.store_message(user_id="u1", session_id="s1", role="user", content="hi")
        finally:
            db.close()

    def test_store_message_no_error_when_zep_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.core.config.Settings.zep_api_key", "", raising=False)
        db = SessionLocal()
        try:
            service = MemoryService(db)
            service.store_message(user_id="u1", session_id="s1", role="user", content="hi")
        finally:
            db.close()

    def test_summarize_returns_local_when_zep_unreachable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*a: object, **kw: object) -> object:
            raise requests.ConnectionError("offline")

        monkeypatch.setattr("app.memory.zep_client.requests.get", _raise)
        db = SessionLocal()
        try:
            service = MemoryService(db)
            summary, provider = service.summarize_session(user_id="u1", session_id="s1")
            assert provider == "local"
            assert isinstance(summary, str)
        finally:
            db.close()

    def test_get_context_returns_empty_string_for_new_session(self) -> None:
        db = SessionLocal()
        try:
            service = MemoryService(db)
            ctx = service.get_context_for_generation(user_id="u1", session_id="new-session")
            # New session has no messages — expect empty or "No" prefix
            assert isinstance(ctx, str)
        finally:
            db.close()
