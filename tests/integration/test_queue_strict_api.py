from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import AppError
from app.jobs.queue import TaskQueue


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    payload = {"email": email, "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    login = client.post("/api/v1/auth/login", json=payload)
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_source_upload_returns_503_when_queue_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_queue_unavailable(*args: Any, **kwargs: Any) -> Any:
        raise AppError(code="QUEUE_UNAVAILABLE", message="Queue backend unavailable", status_code=503)

    monkeypatch.setattr(TaskQueue, "enqueue", staticmethod(_raise_queue_unavailable))
    headers = _auth_headers(client, "queue-source@example.com")
    response = client.post(
        "/api/v1/sources/upload",
        headers=headers,
        files={"file": ("note.txt", b"hello world")},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "QUEUE_UNAVAILABLE"


def test_podcast_create_returns_503_when_queue_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_queue_unavailable(*args: Any, **kwargs: Any) -> Any:
        raise AppError(code="QUEUE_UNAVAILABLE", message="Queue backend unavailable", status_code=503)

    monkeypatch.setattr(TaskQueue, "enqueue", staticmethod(_raise_queue_unavailable))
    headers = _auth_headers(client, "queue-podcast@example.com")
    response = client.post(
        "/api/v1/podcasts",
        headers=headers,
        json={"source_ids": ["src-1"], "title": "Retry Queue"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "QUEUE_UNAVAILABLE"
