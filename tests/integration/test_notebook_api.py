from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.repositories.chat_repo import ChatRepository
from app.db.repositories.notebook_repo import NotebookRepository
from app.db.repositories.source_repo import ChunkRepository, SourceRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import SessionLocal


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    payload = {"email": email, "password": "password123"}
    register = client.post("/api/v1/auth/register", json=payload)
    assert register.status_code == 201
    login = client.post("/api/v1/auth/login", json=payload)
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_notebook_crud_contract_and_default_protection(client: TestClient) -> None:
    headers = _auth_headers(client, "notebook-owner@example.com")

    list_response = client.get("/api/v1/notebooks", headers=headers)
    assert list_response.status_code == 200
    initial_items = list_response.json()["data"]
    assert len(initial_items) == 1
    assert initial_items[0]["is_default"] is True
    assert initial_items[0]["is_pinned"] is False
    assert initial_items[0]["pinned_at"] is None
    default_notebook_id = initial_items[0]["id"]

    create_response = client.post(
        "/api/v1/notebooks",
        headers=headers,
        json={"title": "Research Notes", "description": "Focused notebook"},
    )
    assert create_response.status_code == 201
    notebook = create_response.json()["data"]
    assert notebook["title"] == "Research Notes"
    assert notebook["description"] == "Focused notebook"
    assert notebook["is_default"] is False
    assert notebook["is_pinned"] is False
    assert notebook["pinned_at"] is None

    get_response = client.get(f"/api/v1/notebooks/{notebook['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == notebook["id"]

    update_response = client.patch(
        f"/api/v1/notebooks/{notebook['id']}",
        headers=headers,
        json={"title": "Research Archive", "description": "Updated"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["title"] == "Research Archive"

    pin_response = client.patch(
        f"/api/v1/notebooks/{notebook['id']}",
        headers=headers,
        json={"is_pinned": True},
    )
    assert pin_response.status_code == 200
    pinned = pin_response.json()["data"]
    assert pinned["is_pinned"] is True
    assert pinned["pinned_at"] is not None

    protected_delete = client.delete(f"/api/v1/notebooks/{default_notebook_id}", headers=headers)
    assert protected_delete.status_code == 409
    assert protected_delete.json()["error"]["code"] == "DEFAULT_NOTEBOOK_PROTECTED"

    delete_response = client.delete(f"/api/v1/notebooks/{notebook['id']}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["deleted"] is True


def test_notebook_scoped_sources_and_chunks_are_isolated(client: TestClient) -> None:
    owner_email = "notebook-sources-owner@example.com"
    viewer_email = "notebook-sources-viewer@example.com"
    owner_headers = _auth_headers(client, owner_email)
    viewer_headers = _auth_headers(client, viewer_email)

    owner_notebooks = client.get("/api/v1/notebooks", headers=owner_headers).json()["data"]
    default_notebook_id = next(item["id"] for item in owner_notebooks if item["is_default"] is True)
    created = client.post(
        "/api/v1/notebooks",
        headers=owner_headers,
        json={"title": "Private Research", "description": "Notebook scoped source"},
    )
    assert created.status_code == 201
    private_notebook_id = created.json()["data"]["id"]

    db = SessionLocal()
    try:
        owner = UserRepository(db).get_by_email(owner_email)
        assert owner is not None
        source = SourceRepository(db).create(
            user_id=owner.id,
            notebook_id=private_notebook_id,
            name="scoped-source",
            source_type="text",
            path_or_url="data/scoped.txt",
            checksum="scoped-123",
            metadata_json={"section_heading": "Notebook Scope"},
        )
        ChunkRepository(db).bulk_create(
            source_id=source.id,
            user_id=owner.id,
            notebook_id=private_notebook_id,
            rows=[
                (
                    0,
                    "Notebook-scoped chunk for isolation testing.",
                    8,
                    {"page_number": 1, "section_path": "Notebook Scope"},
                )
            ],
        )
        source_id = source.id
    finally:
        db.close()

    scoped_sources = client.get(f"/api/v1/notebooks/{private_notebook_id}/sources", headers=owner_headers)
    assert scoped_sources.status_code == 200
    assert [item["id"] for item in scoped_sources.json()["data"]] == [source_id]

    default_sources = client.get(f"/api/v1/notebooks/{default_notebook_id}/sources", headers=owner_headers)
    assert default_sources.status_code == 200
    assert source_id not in [item["id"] for item in default_sources.json()["data"]]

    chunk_response = client.get(
        f"/api/v1/notebooks/{private_notebook_id}/sources/{source_id}/chunks?limit=10&offset=0",
        headers=owner_headers,
    )
    assert chunk_response.status_code == 200
    payload = chunk_response.json()["data"]
    assert payload["source_id"] == source_id
    assert payload["chunks"][0]["citation"]["section_path"] == "Notebook Scope"

    cross_user = client.get(
        f"/api/v1/notebooks/{private_notebook_id}/sources/{source_id}",
        headers=viewer_headers,
    )
    assert cross_user.status_code == 404

    db = SessionLocal()
    try:
        viewer = UserRepository(db).get_by_email(viewer_email)
        assert viewer is not None
        viewer_default = NotebookRepository(db).ensure_default_for_user(viewer.id)
    finally:
        db.close()
    cross_notebook = client.get(
        f"/api/v1/notebooks/{viewer_default.id}/sources/{source_id}/chunks",
        headers=owner_headers,
    )
    assert cross_notebook.status_code == 404


def test_legacy_chat_export_route_resolves_notebook_from_session(client: TestClient) -> None:
    headers = _auth_headers(client, "notebook-export@example.com")
    notebook_id = client.get("/api/v1/notebooks", headers=headers).json()["data"][0]["id"]

    created = client.post(
        f"/api/v1/notebooks/{notebook_id}/chat/sessions",
        headers=headers,
        json={"title": "Export Session"},
    )
    assert created.status_code == 201
    session_id = created.json()["data"]["id"]

    db = SessionLocal()
    try:
        user = UserRepository(db).get_by_email("notebook-export@example.com")
        assert user is not None
        session = ChatRepository(db).get_session_for_notebook(
            user_id=user.id,
            notebook_id=notebook_id,
            session_id=session_id,
        )
        assert session is not None
        ChatRepository(db).add_message(session=session, role="user", content="What is this?", citations=[], model_info={})
        ChatRepository(db).add_message(session=session, role="assistant", content="This is an export test.", citations=[], model_info={})
    finally:
        db.close()

    export_response = client.get(
        f"/api/v1/chat/sessions/{session_id}/export?format=md",
        headers=headers,
    )
    assert export_response.status_code == 200
    assert "This is an export test." in export_response.text
