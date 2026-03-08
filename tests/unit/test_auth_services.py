from __future__ import annotations

from app.auth.jwt_service import JwtService
from app.auth.password_service import PasswordService



def test_password_hash_and_verify_roundtrip() -> None:
    password = "complex-password-123"
    hashed = PasswordService.hash(password)
    assert hashed != password
    assert PasswordService.verify(password, hashed)



def test_jwt_create_and_decode_access() -> None:
    jwt_service = JwtService()
    token = jwt_service.create_access_token(user_id="user-1", email="test@example.com")
    payload = jwt_service.decode_token(token=token, expected_type="access")
    assert payload["sub"] == "user-1"
    assert payload["email"] == "test@example.com"
