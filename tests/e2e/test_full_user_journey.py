from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import PodcastStatus
from app.db.repositories.job_repo import PodcastRepository
from app.db.session import SessionLocal
from app.generation.llm_router import LlmRouter
from app.jobs.queue import TaskQueue


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    payload = {"email": email, "password": "password123"}
    register = client.post("/api/v1/auth/register", json=payload)
    assert register.status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    assert login.status_code == 200
    access_token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def _complete_podcast_job(user_id: str, podcast_id: str) -> None:
    db = SessionLocal()
    try:
        repo = PodcastRepository(db)
        podcast = repo.get_for_user(podcast_id=podcast_id, user_id=user_id)
        assert podcast is not None
        output_path = Path("outputs/podcasts") / f"{podcast.id}.mp3"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"ID3TEST")
        podcast.status = PodcastStatus.COMPLETED.value
        podcast.output_path = str(output_path)
        podcast.duration_ms = 1000
        podcast.script = "HOST: Test\nANALYST: Test"
        repo.save(podcast)
    finally:
        db.close()


def _extract_final_sse_payload(raw_body: str) -> dict[str, Any]:
    final_payload: dict[str, Any] | None = None
    for line in raw_body.splitlines():
        if not line.startswith("data: "):
            continue
        payload = json.loads(line.replace("data: ", "", 1))
        if isinstance(payload, dict) and payload.get("type") == "final":
            final_payload = payload
    assert final_payload is not None
    return final_payload


def _sync_enqueue(fn: Any, *args: Any, retry_max: int = 2) -> dict[str, str]:
    _ = retry_max
    if getattr(fn, "__name__", "") == "process_ingestion_job":
        fn(*args)
    if getattr(fn, "__name__", "") == "process_podcast_job":
        _complete_podcast_job(user_id=str(args[0]), podcast_id=str(args[1]))
    return {
        "mode": "rq",
        "queue_job_id": f"rq-test-{uuid4().hex[:8]}",
        "queue_name": "notebooklm-default",
    }


def _ingest_text_source(client: TestClient, headers: dict[str, str]) -> tuple[str, set[str]]:
    upload = client.post(
        "/api/v1/sources/upload",
        headers=headers,
        files={"file": ("notes.txt", b"NotebookLM clone uses grounded citations and memory.")},
    )
    assert upload.status_code == 202
    upload_data = upload.json()["data"]
    source_id = upload_data["source_id"]
    job_id = upload_data["job_id"]
    job = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert job.status_code == 200
    assert job.json()["data"]["status"] == "completed"
    chunks = client.get(f"/api/v1/sources/{source_id}/chunks?limit=50&offset=0", headers=headers)
    assert chunks.status_code == 200
    chunk_items = chunks.json()["data"]["chunks"]
    assert chunk_items
    return source_id, {str(item["chunk_id"]) for item in chunk_items}


def _chat_and_validate(
    client: TestClient,
    headers: dict[str, str],
    source_id: str,
    valid_chunk_ids: set[str],
) -> None:
    create_session = client.post("/api/v1/chat/sessions", headers=headers, json={"title": "Journey"})
    assert create_session.status_code == 201
    session_id = create_session.json()["data"]["id"]

    chat_stream = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=headers,
        json={"message": "What is this notebook about?", "source_ids": [source_id]},
    )
    assert chat_stream.status_code == 200
    final_event = _extract_final_sse_payload(chat_stream.text)
    assert isinstance(final_event.get("content"), str)
    assert isinstance(final_event.get("model_info"), dict)
    assert final_event.get("confidence") in {"low", "medium", "high"}
    citations_raw = final_event.get("citations")
    assert isinstance(citations_raw, list) and citations_raw
    for citation in citations_raw:
        assert isinstance(citation, dict)
        assert str(citation["chunk_id"]) in valid_chunk_ids


def _podcast_and_retry(client: TestClient, headers: dict[str, str], source_id: str) -> None:
    create_podcast = client.post(
        "/api/v1/podcasts",
        headers=headers,
        json={"source_ids": [source_id], "title": "Journey Podcast"},
    )
    assert create_podcast.status_code == 202
    podcast_id = create_podcast.json()["data"]["podcast_id"]

    podcast = client.get(f"/api/v1/podcasts/{podcast_id}", headers=headers)
    assert podcast.status_code == 200
    assert podcast.json()["data"]["status"] == "completed"

    audio = client.get(f"/api/v1/podcasts/{podcast_id}/audio", headers=headers)
    assert audio.status_code == 200

    retry = client.post(
        f"/api/v1/podcasts/{podcast_id}/retry",
        headers=headers,
        json={"title": "Journey Podcast Retry"},
    )
    assert retry.status_code == 202
    retry_data = retry.json()["data"]
    assert retry_data["retried_from_podcast_id"] == podcast_id

    retried_id = retry_data["podcast_id"]
    retried = client.get(f"/api/v1/podcasts/{retried_id}", headers=headers)
    assert retried.status_code == 200
    assert retried.json()["data"]["retried_from_podcast_id"] == podcast_id
    assert retried.json()["data"]["status"] == "completed"


def test_full_user_journey_contract(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_generate(self: LlmRouter, system_prompt: str, user_prompt: str) -> tuple[str, dict[str, str]]:
        _ = (system_prompt, user_prompt)
        return "Grounded answer.", {"provider": "test", "fallback_used": "false"}

    monkeypatch.setattr(LlmRouter, "generate", _fake_generate)
    monkeypatch.setattr(TaskQueue, "enqueue", staticmethod(_sync_enqueue))
    headers = _auth_headers(client, "journey@example.com")
    source_id, valid_chunk_ids = _ingest_text_source(client=client, headers=headers)
    _chat_and_validate(client=client, headers=headers, source_id=source_id, valid_chunk_ids=valid_chunk_ids)
    _podcast_and_retry(client=client, headers=headers, source_id=source_id)
