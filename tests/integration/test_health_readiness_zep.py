from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.health_checks import DependencyStatus


def test_readiness_returns_503_when_zep_is_down(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.v1 import health_routes

    def _collect(*, vector_store: object | None = None) -> dict[str, DependencyStatus]:
        _ = vector_store
        return {
            "postgres": DependencyStatus(state="up", detail="ok", latency_ms=1),
            "redis": DependencyStatus(state="up", detail="ok", latency_ms=1),
            "milvus": DependencyStatus(state="degraded", detail="fallback", latency_ms=None),
            "ollama": DependencyStatus(state="up", detail="ok", latency_ms=1),
            "openrouter": DependencyStatus(state="up", detail="ok", latency_ms=1),
            "zep": DependencyStatus(state="down", detail="Zep auth failed", latency_ms=1),
            "provider_gate": DependencyStatus(state="up", detail="Providers available: ollama, openrouter", latency_ms=None),
        }

    monkeypatch.setattr(health_routes, "collect_dependency_health", _collect)
    response = client.get("/api/v1/health/readiness")
    assert response.status_code == 503
    payload = response.json()
    assert payload["data"]["status"] == "not_ready"
    assert payload["data"]["required_dependencies"]["zep"]["status"] == "down"
