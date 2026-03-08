from __future__ import annotations

from uuid import UUID

import requests

from app.core.config import get_settings
from app.core.exceptions import AppError


class ZepClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def is_enabled(self) -> bool:
        return bool(self.settings.zep_api_key and self.settings.zep_project_id)

    def upsert_message(self, user_id: str, session_id: str, role: str, content: str) -> None:
        self._validate_required_config()
        headers = self._headers()
        payload = {
            "project_id": self.settings.zep_project_id,
            "user_id": user_id,
            "session_id": session_id,
            "messages": [{"role": role, "content": content}],
        }
        try:
            response = requests.post("https://api.getzep.com/api/v2/memory", headers=headers, json=payload, timeout=20)
        except requests.Timeout as exc:
            raise AppError(code="ZEP_UPSERT_TIMEOUT", message="Zep request timed out", status_code=504) from exc
        except requests.RequestException as exc:
            raise AppError(code="ZEP_UNREACHABLE", message="Unable to reach Zep", status_code=502) from exc
        if response.status_code in {401, 403}:
            raise AppError(code="ZEP_AUTH_FAILED", message="Zep authentication failed", status_code=502)
        if response.status_code == 404:
            raise AppError(code="ZEP_PROJECT_NOT_FOUND", message="Zep project was not found", status_code=502)
        if response.status_code >= 400:
            raise AppError(code="ZEP_UPSERT_FAILED", message="Failed to persist memory to Zep", status_code=502)

    def summarize_session(self, user_id: str, session_id: str) -> str:
        self._validate_required_config()

        headers = self._headers()
        params = {"project_id": self.settings.zep_project_id, "user_id": user_id, "session_id": session_id}
        try:
            response = requests.get("https://api.getzep.com/api/v2/memory", headers=headers, params=params, timeout=20)
        except requests.Timeout as exc:
            raise AppError(code="ZEP_SUMMARY_TIMEOUT", message="Zep request timed out", status_code=504) from exc
        except requests.RequestException as exc:
            raise AppError(code="ZEP_UNREACHABLE", message="Unable to reach Zep", status_code=502) from exc
        if response.status_code in {401, 403}:
            raise AppError(code="ZEP_AUTH_FAILED", message="Zep authentication failed", status_code=502)
        if response.status_code == 404:
            raise AppError(code="ZEP_PROJECT_NOT_FOUND", message="Zep project was not found", status_code=502)
        if response.status_code >= 400:
            raise AppError(code="ZEP_SUMMARY_FAILED", message="Failed to fetch memory summary", status_code=502)
        body = response.json()
        summary = body.get("summary")
        return str(summary) if summary else "No summary available"

    def _validate_required_config(self) -> None:
        if not self.settings.zep_api_key:
            raise AppError(code="ZEP_CONFIG_MISSING", message="ZEP_API_KEY is required", status_code=503)
        if not self.settings.zep_project_id:
            raise AppError(code="ZEP_CONFIG_MISSING", message="ZEP_PROJECT_ID is required", status_code=503)
        try:
            UUID(self.settings.zep_project_id)
        except ValueError as exc:
            raise AppError(
                code="ZEP_PROJECT_INVALID",
                message="ZEP_PROJECT_ID must be a valid UUID",
                status_code=503,
            ) from exc

    def _headers(self) -> dict[str, str]:
        # Zep Cloud API keys use the Api-Key auth scheme, not Bearer.
        return {
            "Authorization": f"Api-Key {self.settings.zep_api_key}",
            "Content-Type": "application/json",
        }
