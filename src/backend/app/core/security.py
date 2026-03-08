from __future__ import annotations

from typing import cast

from passlib.context import CryptContext

# pbkdf2_sha256 avoids platform-specific bcrypt backend issues while remaining secure.
password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return cast(str, password_context.hash(password))


def verify_password(password: str, hashed_password: str) -> bool:
    return cast(bool, password_context.verify(password, hashed_password))
