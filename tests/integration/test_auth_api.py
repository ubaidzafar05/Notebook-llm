from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_register_login_refresh_flow(client: TestClient) -> None:
    register_payload = {"email": "user@example.com", "password": "password123"}
    register_response = client.post("/api/v1/auth/register", json=register_payload)
    assert register_response.status_code == 201
    register_data = register_response.json()["data"]

    assert register_data["user"]["email"] == "user@example.com"
    assert register_data["access_token"]
    assert register_response.cookies.get(get_settings().auth_refresh_cookie_name)

    login_response = client.post("/api/v1/auth/login", json=register_payload)
    assert login_response.status_code == 200
    login_data = login_response.json()["data"]
    assert login_data["access_token"]

    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()["data"]
    assert refresh_data["access_token"]
    assert refresh_response.cookies.get(get_settings().auth_refresh_cookie_name)



def test_duplicate_registration_returns_conflict(client: TestClient) -> None:
    payload = {"email": "dupe@example.com", "password": "password123"}
    first = client.post("/api/v1/auth/register", json=payload)
    second = client.post("/api/v1/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_refresh_token_rotation_rejects_old_token(client: TestClient) -> None:
    payload = {"email": "rotate@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    login_response = client.post("/api/v1/auth/login", json=payload)
    cookie_name = get_settings().auth_refresh_cookie_name
    first_refresh_token = login_response.cookies.get(cookie_name)
    assert first_refresh_token

    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    second_refresh_token = refreshed.cookies.get(cookie_name)
    assert second_refresh_token
    assert second_refresh_token != first_refresh_token

    client.cookies.set(cookie_name, first_refresh_token)
    replay = client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "INVALID_TOKEN"


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    payload = {"email": "logout@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    login_response = client.post("/api/v1/auth/login", json=payload)
    cookie_name = get_settings().auth_refresh_cookie_name
    refresh_token = login_response.cookies.get(cookie_name)
    assert refresh_token

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200

    client.cookies.set(cookie_name, refresh_token)
    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "INVALID_TOKEN"


def test_google_exchange_rejects_unknown_oauth_code(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/google/exchange",
        json={"oauth_code": "invalid-code-value-should-fail"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_OAUTH_CODE"


def test_register_validation_error_uses_standard_envelope(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "invalid", "password": "short"},
    )
    assert response.status_code == 422
    payload = response.json()
    assert set(payload.keys()) == {"data", "error", "meta"}
    assert payload["data"] is None
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["message"] == "Request validation failed"
    details = payload["error"]["details"]
    assert isinstance(details, list) and details
    detail_fields = {str(item["field"]) for item in details}
    assert "body.email" in detail_fields
    assert "body.password" in detail_fields
