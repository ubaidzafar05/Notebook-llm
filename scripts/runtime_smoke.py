from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

import requests


def main() -> int:
    args = parse_args()
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    email = f"smoke.{int(time.time())}@example.com"
    password = "Password123!"

    access_token = register_user(session, args.base_url, email, password)
    session.headers["Authorization"] = f"Bearer {access_token}"

    notebook_id = create_notebook(session, args.base_url)
    verify_notebook_listing(session, args.base_url, notebook_id)
    toggle_pin(session, args.base_url, notebook_id, True)
    toggle_pin(session, args.base_url, notebook_id, False)

    source_id, job_id = upload_source(session, args.base_url, notebook_id)
    wait_for_ingestion(session, args.base_url, notebook_id, source_id, job_id)
    chunk_count = get_chunk_count(session, args.base_url, notebook_id, source_id)

    session_id = create_chat_session(session, args.base_url, notebook_id)
    final_message = send_chat_message(session, args.base_url, notebook_id, session_id, source_id)
    export_session(session, args.base_url, notebook_id, session_id, source_id)
    fetch_usage(session, args.base_url, notebook_id)

    podcast_id = create_podcast(session, args.base_url, notebook_id, source_id)
    wait_for_podcast(session, args.base_url, notebook_id, podcast_id)

    print(
        json.dumps(
            {
                "status": "ok",
                "notebook_id": notebook_id,
                "source_id": source_id,
                "job_id": job_id,
                "session_id": session_id,
                "podcast_id": podcast_id,
                "chunk_count": chunk_count,
                "citations": len(final_message.get("citations", [])),
            },
            indent=2,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime smoke test for NotebookLLM.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    return parser.parse_args()


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    expected: set[int],
    **kwargs: object,
) -> dict[str, object]:
    response = session.request(method, url, timeout=120, **kwargs)
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        raise RuntimeError(f"{method} {url} returned non-JSON response: {response.text[:500]}")
    payload = response.json()
    print(f"{method} {url} -> {response.status_code}")
    if response.status_code not in expected:
        raise RuntimeError(json.dumps(payload, indent=2))
    return payload


def register_user(session: requests.Session, base_url: str, email: str, password: str) -> str:
    payload = request_json(
        session,
        "POST",
        f"{base_url}/api/v1/auth/register",
        expected={201},
        json={"email": email, "password": password},
    )
    data = expect_record(payload, "data")
    return expect_string(data, "access_token")


def create_notebook(session: requests.Session, base_url: str) -> str:
    payload = request_json(
        session,
        "POST",
        f"{base_url}/api/v1/notebooks",
        expected={201},
        json={"title": "Smoke Notebook", "description": "production smoke"},
    )
    data = expect_record(payload, "data")
    return expect_string(data, "id")


def verify_notebook_listing(session: requests.Session, base_url: str, notebook_id: str) -> None:
    payload = request_json(session, "GET", f"{base_url}/api/v1/notebooks", expected={200})
    data = expect_list(payload, "data")
    if not any(expect_string(item, "id") == notebook_id for item in data):
        raise RuntimeError("Created notebook missing from list endpoint")


def toggle_pin(session: requests.Session, base_url: str, notebook_id: str, is_pinned: bool) -> None:
    request_json(
        session,
        "PATCH",
        f"{base_url}/api/v1/notebooks/{notebook_id}",
        expected={200},
        json={"is_pinned": is_pinned},
    )


def upload_source(session: requests.Session, base_url: str, notebook_id: str) -> tuple[str, str]:
    source_path = Path("/tmp/notebooklm-smoke.txt")
    source_path.write_text(
        "NotebookLM smoke source\n\n"
        "The capital of France is Paris.\n"
        "Qwen3 8B is the active local chat model.\n"
        "Exports should include source context and cited chunk text.\n",
        encoding="utf-8",
    )
    with source_path.open("rb") as handle:
        payload = request_json(
            session,
            "POST",
            f"{base_url}/api/v1/notebooks/{notebook_id}/sources/upload",
            expected={202},
            files={"file": ("notebooklm-smoke.txt", handle, "text/plain")},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
    data = expect_record(payload, "data")
    return expect_string(data, "source_id"), expect_string(data, "job_id")


def wait_for_ingestion(
    session: requests.Session,
    base_url: str,
    notebook_id: str,
    source_id: str,
    job_id: str,
) -> None:
    deadline = time.time() + 120
    while time.time() < deadline:
        source_payload = request_json(
            session,
            "GET",
            f"{base_url}/api/v1/notebooks/{notebook_id}/sources",
            expected={200},
        )
        sources = expect_list(source_payload, "data")
        source = next((item for item in sources if expect_string(item, "id") == source_id), None)
        if source is None:
            raise RuntimeError("Uploaded source disappeared from source list")
        source_status = expect_string(source, "status")

        job_payload = request_json(session, "GET", f"{base_url}/api/v1/jobs/{job_id}", expected={200})
        job_data = expect_record(job_payload, "data")
        job_status = expect_string(job_data, "status")
        print(f"ingestion poll: source={source_status} job={job_status}")

        if source_status == "ready" and job_status == "completed":
            return
        if source_status in {"failed", "error"} or job_status in {"failed", "canceled"}:
            raise RuntimeError(json.dumps(job_payload, indent=2))
        time.sleep(2)
    raise RuntimeError("Ingestion timed out")


def get_chunk_count(session: requests.Session, base_url: str, notebook_id: str, source_id: str) -> int:
    payload = request_json(
        session,
        "GET",
        f"{base_url}/api/v1/notebooks/{notebook_id}/sources/{source_id}/chunks?limit=20&offset=0",
        expected={200},
    )
    data = expect_record(payload, "data")
    chunks = expect_list(data, "chunks")
    return len(chunks)


def create_chat_session(session: requests.Session, base_url: str, notebook_id: str) -> str:
    payload = request_json(
        session,
        "POST",
        f"{base_url}/api/v1/notebooks/{notebook_id}/chat/sessions",
        expected={201},
        json={"title": "Smoke Session"},
    )
    data = expect_record(payload, "data")
    return expect_string(data, "id")


def send_chat_message(
    session: requests.Session,
    base_url: str,
    notebook_id: str,
    session_id: str,
    source_id: str,
) -> dict[str, object]:
    response = session.post(
        f"{base_url}/api/v1/notebooks/{notebook_id}/chat/sessions/{session_id}/messages",
        json={"message": "What is the capital of France? Answer with citations.", "source_ids": [source_id]},
        timeout=180,
        stream=True,
    )
    print(f"POST {base_url}/api/v1/notebooks/{notebook_id}/chat/sessions/{session_id}/messages -> {response.status_code}")
    if response.status_code != 200:
        raise RuntimeError(response.text[:2000])

    final_payload: dict[str, object] | None = None
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data:"):
            continue
        payload = json.loads(raw_line[5:].strip())
        if payload.get("type") == "final":
            final_payload = payload

    if final_payload is None:
        raise RuntimeError("No final SSE payload received from chat stream")
    return final_payload


def export_session(
    session: requests.Session,
    base_url: str,
    notebook_id: str,
    session_id: str,
    source_id: str,
) -> None:
    for export_format in ("md", "pdf"):
        response = session.get(
            f"{base_url}/api/v1/notebooks/{notebook_id}/chat/sessions/{session_id}/export"
            f"?format={export_format}&top_k=6&similarity_threshold=0.72"
            f"&model=ollama/qwen3:8b&memory_enabled=true&attached_sources={source_id}",
            timeout=180,
        )
        print(f"GET export {export_format} -> {response.status_code}")
        if response.status_code != 200:
            raise RuntimeError(response.text[:2000])
        if len(response.content) <= 50:
            raise RuntimeError(f"Export {export_format} returned unexpectedly small payload")


def fetch_usage(session: requests.Session, base_url: str, notebook_id: str) -> None:
    request_json(session, "GET", f"{base_url}/api/v1/notebooks/{notebook_id}/usage", expected={200})


def create_podcast(session: requests.Session, base_url: str, notebook_id: str, source_id: str) -> str:
    payload = request_json(
        session,
        "POST",
        f"{base_url}/api/v1/notebooks/{notebook_id}/podcasts",
        expected={202},
        json={"source_ids": [source_id], "title": "Smoke Podcast", "voice": "Alloy Host"},
    )
    data = expect_record(payload, "data")
    return expect_string(data, "podcast_id")


def wait_for_podcast(session: requests.Session, base_url: str, notebook_id: str, podcast_id: str) -> None:
    deadline = time.time() + 180
    while time.time() < deadline:
        payload = request_json(session, "GET", f"{base_url}/api/v1/notebooks/{notebook_id}/podcasts", expected={200})
        podcasts = expect_list(payload, "data")
        podcast = next((item for item in podcasts if expect_string(item, "id") == podcast_id), None)
        if podcast is None:
            raise RuntimeError("Created podcast missing from list endpoint")
        status = expect_string(podcast, "status")
        print(f"podcast poll: {status}")
        if status == "completed":
            response = session.get(f"{base_url}/api/v1/notebooks/{notebook_id}/podcasts/{podcast_id}/audio", timeout=60)
            print(f"GET audio -> {response.status_code}")
            if response.status_code != 200:
                raise RuntimeError(response.text[:2000])
            return
        if status == "failed":
            raise RuntimeError(json.dumps(podcast, indent=2))
        time.sleep(2)
    raise RuntimeError("Podcast timed out")


def expect_record(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected object at {key}, got {type(value).__name__}")
    return value


def expect_list(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise RuntimeError(f"Expected list at {key}, got {type(value).__name__}")
    normalized: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise RuntimeError(f"Expected list item object at {key}, got {type(item).__name__}")
        normalized.append(item)
    return normalized


def expect_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise RuntimeError(f"Expected string at {key}, got {type(value).__name__}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
