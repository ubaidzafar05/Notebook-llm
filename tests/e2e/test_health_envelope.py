from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_envelope_shape(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert set(payload.keys()) == {"data", "error", "meta"}
    assert payload["data"]["status"] in {"ok", "degraded"}
    assert "dependencies" in payload["data"]
    assert payload["error"] is None
    assert "request_id" in payload["meta"]


def test_dependency_health_endpoint_shape(client: TestClient) -> None:
    response = client.get("/api/v1/health/dependencies")
    assert response.status_code == 200

    payload = response.json()
    assert set(payload.keys()) == {"data", "error", "meta"}
    assert payload["error"] is None
    for dependency in ("postgres", "redis", "milvus", "ollama", "openrouter", "zep", "provider_gate"):
        assert dependency in payload["data"]
        assert payload["data"][dependency]["status"] in {"up", "down", "degraded", "skipped"}


def test_readiness_endpoint_shape(client: TestClient) -> None:
    response = client.get("/api/v1/health/readiness")
    assert response.status_code in {200, 503}

    payload = response.json()
    assert set(payload.keys()) == {"data", "error", "meta"}
    assert payload["error"] is None
    assert payload["data"]["status"] in {"ready", "not_ready"}
    assert "required_dependencies" in payload["data"]
    assert "postgres" in payload["data"]["required_dependencies"]
    assert "redis" in payload["data"]["required_dependencies"]
    assert "milvus" in payload["data"]["required_dependencies"]
    assert "zep" in payload["data"]["required_dependencies"]
    assert "provider_gate" in payload["data"]["required_dependencies"]
