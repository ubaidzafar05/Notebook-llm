from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from jose import jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.cookie_service import clear_refresh_cookie, set_refresh_cookie
from app.auth.auth_service import AuthService
from app.auth.auth_state_store import AuthStateStore
from app.auth.google_oauth_service import GoogleOAuthService
from app.core.config import get_settings
from app.core.response_envelope import error_response, success_response
from app.db.session import get_db
from schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class OAuthExchangeRequest(BaseModel):
    oauth_code: str = Field(min_length=20)


@router.post("/register")
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    service = AuthService(db)
    user_id, email, tokens = service.register(payload.email, payload.password)
    body = AuthResponse(user=UserOut(id=user_id, email=email), access_token=tokens.access_token)
    response = success_response(data=body.model_dump(), request_id=request_id, status_code=201)
    set_refresh_cookie(response, tokens.refresh_token)
    return response


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    service = AuthService(db)
    user_id, email, tokens = service.login(payload.email, payload.password)
    body = AuthResponse(user=UserOut(id=user_id, email=email), access_token=tokens.access_token)
    response = success_response(data=body.model_dump(), request_id=request_id)
    set_refresh_cookie(response, tokens.refresh_token)
    return response


@router.post("/refresh")
def refresh_token(
    request: Request,
    payload: RefreshRequest | None = Body(default=None),
    db: Session = Depends(get_db),
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    raw_refresh_token = _resolve_refresh_token(request, payload)
    if raw_refresh_token is None:
        return error_response(
            code="INVALID_TOKEN",
            message="Refresh token is required",
            request_id=request_id,
            status_code=401,
        )
    store = AuthStateStore()
    if store.is_refresh_token_revoked(raw_refresh_token):
        return error_response(
            code="INVALID_TOKEN",
            message="Refresh token has been revoked",
            request_id=request_id,
            status_code=401,
        )

    tokens = AuthService(db).refresh(raw_refresh_token)
    store.revoke_refresh_token(
        raw_refresh_token,
        ttl_seconds=_refresh_token_ttl_seconds(raw_refresh_token),
    )
    response = success_response(
        data={"access_token": tokens.access_token, "token_type": tokens.token_type},
        request_id=request_id,
    )
    set_refresh_cookie(response, tokens.refresh_token)
    return response


@router.post("/logout")
def logout(request: Request, payload: LogoutRequest | None = Body(default=None)) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    raw_refresh_token = _resolve_refresh_token(request, payload)
    response = success_response(data={"logged_out": True}, request_id=request_id)
    clear_refresh_cookie(response)
    if raw_refresh_token is None:
        return response
    AuthStateStore().revoke_refresh_token(
        raw_refresh_token,
        ttl_seconds=_refresh_token_ttl_seconds(raw_refresh_token),
    )
    return response


@router.get("/google/start")
def google_start(request: Request) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    state = secrets.token_urlsafe(24)
    AuthStateStore().save_oauth_state(state)
    url = GoogleOAuthService().build_authorization_url(state=state)
    return success_response(data={"auth_url": url, "state": state}, request_id=request_id)


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    request_id = getattr(request.state, "request_id", "")
    store = AuthStateStore()
    if not store.consume_oauth_state(state):
        return error_response(
            code="INVALID_OAUTH_STATE",
            message="OAuth state mismatch",
            request_id=request_id,
            status_code=400,
        )

    oauth = GoogleOAuthService()
    token_payload = oauth.exchange_code(code=code)
    user_info = oauth.get_user_info(access_token=token_payload["access_token"])
    user_id, email, tokens = AuthService(db).login_or_register_google(
        google_sub=user_info["sub"],
        email=user_info["email"],
    )

    exchange_code = secrets.token_urlsafe(32)
    store.save_oauth_exchange(
        exchange_code,
        {
            "user_id": user_id,
            "email": email,
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
        },
    )
    settings = get_settings()
    redirect_url = f"{settings.ui_url}/auth/callback?oauth_code={exchange_code}"
    response = RedirectResponse(url=redirect_url, status_code=302)
    set_refresh_cookie(response, tokens.refresh_token)
    return response


@router.post("/google/exchange")
def exchange_google_code(payload: OAuthExchangeRequest, request: Request) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    row = AuthStateStore().consume_oauth_exchange(payload.oauth_code)
    if row is None:
        return error_response(
            code="INVALID_OAUTH_CODE",
            message="OAuth exchange code is invalid",
            request_id=request_id,
            status_code=400,
        )

    body = {
        "user": {"id": row["user_id"], "email": row["email"]},
        "access_token": row["access_token"],
        "token_type": "bearer",
    }
    response = success_response(data=body, request_id=request_id)
    refresh_token = row.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token:
        set_refresh_cookie(response, refresh_token)
    return response


def _resolve_refresh_token(request: Request, payload: RefreshRequest | LogoutRequest | None) -> str | None:
    cookie_name = get_settings().auth_refresh_cookie_name
    cookie_token = request.cookies.get(cookie_name)
    if isinstance(cookie_token, str) and cookie_token.strip():
        return cookie_token.strip()
    if payload is None or payload.refresh_token is None:
        return None
    token = payload.refresh_token.strip()
    return token or None


def _refresh_token_ttl_seconds(refresh_token: str) -> int:
    default_ttl = get_settings().jwt_refresh_expires_minutes * 60
    try:
        claims = jwt.get_unverified_claims(refresh_token)
    except Exception:  # noqa: BLE001
        return default_ttl
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)):
        return default_ttl
    now_ts = int(datetime.now(UTC).timestamp())
    return max(int(exp) - now_ts, 60)
