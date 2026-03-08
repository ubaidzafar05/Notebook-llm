from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import AppError

ALGORITHM = "HS256"


class JwtService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def create_access_token(self, user_id: str, email: str) -> str:
        expires_at = datetime.now(UTC) + timedelta(minutes=self.settings.jwt_access_expires_minutes)
        payload = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "jti": str(uuid4()),
            "exp": expires_at,
        }
        token = jwt.encode(payload, self.settings.jwt_secret, algorithm=ALGORITHM)
        return cast(str, token)

    def create_refresh_token(self, user_id: str, email: str) -> str:
        expires_at = datetime.now(UTC) + timedelta(minutes=self.settings.jwt_refresh_expires_minutes)
        payload = {
            "sub": user_id,
            "email": email,
            "type": "refresh",
            "jti": str(uuid4()),
            "exp": expires_at,
        }
        token = jwt.encode(payload, self.settings.jwt_secret, algorithm=ALGORITHM)
        return cast(str, token)

    def decode_token(self, token: str, expected_type: str) -> dict[str, str]:
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=[ALGORITHM])
        except JWTError as exc:
            raise AppError(code="INVALID_TOKEN", message="Token validation failed", status_code=401) from exc

        token_type = payload.get("type")
        if token_type != expected_type:
            raise AppError(code="INVALID_TOKEN", message="Token type mismatch", status_code=401)

        sub = payload.get("sub")
        email = payload.get("email")
        if not isinstance(sub, str) or not isinstance(email, str):
            raise AppError(code="INVALID_TOKEN", message="Token payload is invalid", status_code=401)
        return {"sub": sub, "email": email}
