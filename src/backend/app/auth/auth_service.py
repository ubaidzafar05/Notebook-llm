from __future__ import annotations

from schemas.auth import AuthTokenPair
from sqlalchemy.orm import Session

from app.auth.jwt_service import JwtService
from app.auth.password_service import PasswordService
from app.core.exceptions import AppError
from app.db.repositories.notebook_repo import NotebookRepository
from app.db.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.notebooks = NotebookRepository(db)
        self.jwt = JwtService()
        self.password_service = PasswordService()

    def register(self, email: str, password: str) -> tuple[str, str, AuthTokenPair]:
        existing = self.users.get_by_email(email)
        if existing is not None:
            raise AppError(code="EMAIL_ALREADY_EXISTS", message="Email is already registered", status_code=409)

        password_hash = self.password_service.hash(password)
        user = self.users.create(email=email, password_hash=password_hash)
        self.notebooks.ensure_default_for_user(user.id)
        tokens = self._generate_tokens(user.id, user.email)
        return user.id, user.email, tokens

    def login(self, email: str, password: str) -> tuple[str, str, AuthTokenPair]:
        user = self.users.get_by_email(email)
        if user is None or user.password_hash is None:
            raise AppError(code="INVALID_CREDENTIALS", message="Invalid email or password", status_code=401)

        is_valid = self.password_service.verify(password, user.password_hash)
        if not is_valid:
            raise AppError(code="INVALID_CREDENTIALS", message="Invalid email or password", status_code=401)

        tokens = self._generate_tokens(user.id, user.email)
        return user.id, user.email, tokens

    def refresh(self, refresh_token: str) -> AuthTokenPair:
        payload = self.jwt.decode_token(refresh_token, expected_type="refresh")
        user = self.users.get_by_id(payload["sub"])
        if user is None:
            raise AppError(code="INVALID_TOKEN", message="User no longer exists", status_code=401)
        return self._generate_tokens(user.id, user.email)

    def login_or_register_google(self, google_sub: str, email: str) -> tuple[str, str, AuthTokenPair]:
        user = self.users.get_by_google_sub(google_sub)
        if user is None:
            existing = self.users.get_by_email(email)
            if existing is not None:
                existing.google_sub = google_sub
                user = self.users.update(existing)
            else:
                user = self.users.create(email=email, password_hash=None, google_sub=google_sub)

        self.notebooks.ensure_default_for_user(user.id)
        tokens = self._generate_tokens(user.id, user.email)
        return user.id, user.email, tokens

    def _generate_tokens(self, user_id: str, email: str) -> AuthTokenPair:
        access = self.jwt.create_access_token(user_id=user_id, email=email)
        refresh = self.jwt.create_refresh_token(user_id=user_id, email=email)
        return AuthTokenPair(access_token=access, refresh_token=refresh)
