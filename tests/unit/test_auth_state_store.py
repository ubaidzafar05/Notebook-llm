from __future__ import annotations

from app.auth.auth_state_store import AuthStateStore


def test_oauth_state_is_one_time_consumable() -> None:
    store = AuthStateStore()
    state = "state-once"
    store.save_oauth_state(state)
    assert store.consume_oauth_state(state) is True
    assert store.consume_oauth_state(state) is False


def test_oauth_exchange_code_is_one_time_consumable() -> None:
    store = AuthStateStore()
    code = "code-once"
    payload = {
        "user_id": "u1",
        "email": "u1@example.com",
        "access_token": "a",
        "refresh_token": "r",
    }
    store.save_oauth_exchange(code, payload)
    first = store.consume_oauth_exchange(code)
    second = store.consume_oauth_exchange(code)
    assert first is not None
    assert first["user_id"] == "u1"
    assert second is None


def test_refresh_token_revocation_roundtrip() -> None:
    store = AuthStateStore()
    token = "refresh-token-value"
    assert store.is_refresh_token_revoked(token) is False
    store.revoke_refresh_token(token, ttl_seconds=600)
    assert store.is_refresh_token_revoked(token) is True
