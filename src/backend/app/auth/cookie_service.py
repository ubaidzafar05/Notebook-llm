from __future__ import annotations

from typing import Literal, cast

from fastapi import Response

from app.core.config import get_settings


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    samesite = cast(Literal["lax", "strict", "none"], settings.auth_cookie_samesite.lower())
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=samesite,
        max_age=settings.jwt_refresh_expires_minutes * 60,
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    samesite = cast(Literal["lax", "strict", "none"], settings.auth_cookie_samesite.lower())
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=samesite,
        path="/api/v1/auth",
    )
