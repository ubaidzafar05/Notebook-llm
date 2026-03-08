from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.repositories.source_repo import ChunkRepository, SourceRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import SessionLocal


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    payload = {"email": email, "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    login = client.post("/api/v1/auth/login", json=payload)
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_source_chunks_returns_chunk_contract(client: TestClient) -> None:
    owner_email = "chunk-owner@example.com"
    headers = _auth_headers(client, owner_email)

    db = SessionLocal()
    try:
        owner = UserRepository(db).get_by_email(owner_email)
        assert owner is not None
        source = SourceRepository(db).create(
            user_id=owner.id,
            name="manual-source",
            source_type="text",
            path_or_url="data/manual.txt",
            checksum="abc123",
            metadata_json={"source": "test"},
        )
        ChunkRepository(db).bulk_create(
            source_id=source.id,
            user_id=owner.id,
            rows=[(0, "This is test chunk text", 5, {"page_number": 1, "source": "manual-source"})],
        )
        source_id = source.id
    finally:
        db.close()

    response = client.get(f"/api/v1/sources/{source_id}/chunks?limit=10&offset=0", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["source_id"] == source_id
    assert payload["limit"] == 10
    assert len(payload["chunks"]) == 1
    assert payload["chunks"][0]["chunk_id"]
    assert payload["chunks"][0]["chunk_index"] == 0
    assert "excerpt" in payload["chunks"][0]
    assert "citation" in payload["chunks"][0]


def test_list_source_chunks_is_user_isolated(client: TestClient) -> None:
    owner_email = "chunk-owner2@example.com"
    viewer_email = "chunk-viewer2@example.com"
    _auth_headers(client, owner_email)
    viewer_headers = _auth_headers(client, viewer_email)

    db = SessionLocal()
    try:
        owner = UserRepository(db).get_by_email(owner_email)
        assert owner is not None
        source = SourceRepository(db).create(
            user_id=owner.id,
            name="private-source",
            source_type="text",
            path_or_url="data/private.txt",
            checksum="def456",
            metadata_json={"source": "test"},
        )
        source_id = source.id
    finally:
        db.close()

    response = client.get(f"/api/v1/sources/{source_id}/chunks", headers=viewer_headers)
    assert response.status_code == 404
