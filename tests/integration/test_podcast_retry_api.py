from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.jobs.queue import TaskQueue


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    payload = {"email": email, "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    login = client.post("/api/v1/auth/login", json=payload)
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_retry_podcast_creates_lineage_record(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_enqueue(*args: Any, **kwargs: Any) -> dict[str, str]:
        return {"mode": "rq", "queue_job_id": "rq-123", "queue_name": "notebooklm-default"}

    monkeypatch.setattr(TaskQueue, "enqueue", staticmethod(_fake_enqueue))
    headers = _auth_headers(client, "podcast-retry@example.com")

    create = client.post(
        "/api/v1/podcasts",
        headers=headers,
        json={"source_ids": ["src-1"], "title": "First Podcast"},
    )
    assert create.status_code == 202
    original_id = create.json()["data"]["podcast_id"]

    retry = client.post(
        f"/api/v1/podcasts/{original_id}/retry",
        headers=headers,
        json={"title": "Retry Podcast"},
    )
    assert retry.status_code == 202
    retry_data = retry.json()["data"]
    assert retry_data["retried_from_podcast_id"] == original_id

    retried_id = retry_data["podcast_id"]
    get_retried = client.get(f"/api/v1/podcasts/{retried_id}", headers=headers)
    assert get_retried.status_code == 200
    assert get_retried.json()["data"]["retried_from_podcast_id"] == original_id
