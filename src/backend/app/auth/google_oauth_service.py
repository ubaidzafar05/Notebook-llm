from __future__ import annotations

from urllib.parse import urlencode

import requests

from app.core.config import get_settings
from app.core.exceptions import AppError


class GoogleOAuthService:
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

    def __init__(self) -> None:
        self.settings = get_settings()

    def build_authorization_url(self, state: str) -> str:
        if not self.settings.google_client_id:
            raise AppError(code="GOOGLE_OAUTH_DISABLED", message="Google OAuth is not configured", status_code=503)

        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": str(self.settings.google_redirect_uri),
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict[str, str]:
        payload = {
            "client_id": self.settings.google_client_id,
            "client_secret": self.settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": str(self.settings.google_redirect_uri),
        }
        response = requests.post(self.TOKEN_URL, data=payload, timeout=20)
        if response.status_code >= 400:
            raise AppError(code="GOOGLE_TOKEN_FAILED", message="Google token exchange failed", status_code=401)

        token_payload = response.json()
        access_token = token_payload.get("access_token")
        if not isinstance(access_token, str):
            raise AppError(code="GOOGLE_TOKEN_FAILED", message="Google access token missing", status_code=401)
        return {"access_token": access_token}

    def get_user_info(self, access_token: str) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(self.USERINFO_URL, headers=headers, timeout=20)
        if response.status_code >= 400:
            raise AppError(code="GOOGLE_USERINFO_FAILED", message="Google user info fetch failed", status_code=401)

        payload = response.json()
        sub = payload.get("sub")
        email = payload.get("email")
        if not isinstance(sub, str) or not isinstance(email, str):
            raise AppError(code="GOOGLE_USERINFO_FAILED", message="Google profile payload missing required fields", status_code=401)
        return {"sub": sub, "email": email}
