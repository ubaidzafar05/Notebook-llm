from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import AppError
from app.core.config import get_settings


def test_google_start_returns_503_when_auth_state_store_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.auth import auth_state_store

    def _raise_unavailable(self: object) -> Any:
        raise AppError(code="AUTH_STATE_UNAVAILABLE", message="Auth state store unavailable", status_code=503)

    monkeypatch.setattr(auth_state_store.AuthStateStore, "_redis", _raise_unavailable)
    response = client.get("/api/v1/auth/google/start")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_STATE_UNAVAILABLE"


def test_refresh_returns_503_when_auth_state_store_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.auth import auth_state_store

    payload = {"email": "redis-outage@example.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    login = client.post("/api/v1/auth/login", json=payload)
    refresh_token = login.cookies.get(get_settings().auth_refresh_cookie_name)
    assert isinstance(refresh_token, str) and refresh_token

    def _raise_unavailable(self: object) -> Any:
        raise AppError(code="AUTH_STATE_UNAVAILABLE", message="Auth state store unavailable", status_code=503)

    monkeypatch.setattr(auth_state_store.AuthStateStore, "_redis", _raise_unavailable)
    response = client.post(
        "/api/v1/auth/refresh",
        cookies={get_settings().auth_refresh_cookie_name: refresh_token},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_STATE_UNAVAILABLE"
