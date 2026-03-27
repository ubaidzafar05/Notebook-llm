from __future__ import annotations

from typing import cast

import pytest

from app.core.config import reset_settings_cache
from app.core.health_checks import DependencyStatus, _check_milvus, _check_zep
from app.vector_store.milvus_client import VectorStoreClient


class _FakeVectorStore:
    def __init__(self, ready: bool, reason: str, detail: str) -> None:
        self._ready = ready
        self._reason = reason
        self._detail = detail

    def is_milvus_ready(self) -> bool:
        return self._ready

    def milvus_diagnostics(self) -> tuple[str, str]:
        return self._reason, self._detail


def test_milvus_check_classifies_import_failures() -> None:
    store = _FakeVectorStore(
        ready=False,
        reason="import_failure",
        detail="Milvus import failure: No module named pkg_resources",
    )
    status = _check_milvus(vector_store=cast(VectorStoreClient, store))
    assert isinstance(status, DependencyStatus)
    assert status.state == "degraded"
    assert status.detail.startswith("import_failure:")


def test_milvus_check_classifies_connection_failures() -> None:
    store = _FakeVectorStore(
        ready=False,
        reason="connection_failure",
        detail="Milvus connection failure: dial tcp 127.0.0.1:19530: connect refused",
    )
    status = _check_milvus(vector_store=cast(VectorStoreClient, store))
    assert status.state == "degraded"
    assert status.detail.startswith("connection_failure:")


def test_zep_check_is_skipped_when_memory_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as scoped:
        scoped.setenv("ENABLE_ZEP_MEMORY", "false")
        reset_settings_cache()
        status = _check_zep()
    reset_settings_cache()
    assert status.state == "skipped"
    assert status.detail == "Zep memory disabled"
