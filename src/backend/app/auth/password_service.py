from __future__ import annotations

from app.core.security import hash_password, verify_password


class PasswordService:
    @staticmethod
    def hash(password: str) -> str:
        return hash_password(password)

    @staticmethod
    def verify(password: str, hashed_password: str) -> bool:
        return verify_password(password, hashed_password)
