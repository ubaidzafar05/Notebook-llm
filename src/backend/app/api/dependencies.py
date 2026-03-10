from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, Response
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.orm import Session

from app.auth.jwt_service import JwtService
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_db


@dataclass(slots=True)
class AuthenticatedUser:
    id: str
    email: str



def get_request_id(x_request_id: str | None = Header(default=None)) -> str:
    return x_request_id or ""


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.replace("Bearer ", "", 1).strip()
    payload = JwtService().decode_token(token, expected_type="access")
    user = UserRepository(db).get_by_id(payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return AuthenticatedUser(id=user.id, email=user.email)


async def _rate_limit_guard(request: Request, response: Response, limiter: RateLimiter) -> None:
    if not getattr(request.app.state, "rate_limiter_ready", False):
        return
    await limiter(request, response)


def rate_limit_dependency(times: int, seconds: int) -> Depends:
    limiter = RateLimiter(times=times, seconds=seconds)

    async def dependency(request: Request, response: Response) -> None:
        await _rate_limit_guard(request, response, limiter)

    return Depends(dependency)
