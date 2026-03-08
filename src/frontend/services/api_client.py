from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any, cast

import requests


class ApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


class ApiClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        self.access_token: str | None = None
        self._session = requests.Session()

    def set_access_token(self, access_token: str | None) -> None:
        self.access_token = access_token.strip() if isinstance(access_token, str) else None

    def register(self, email: str, password: str) -> dict[str, Any]:
        data = self._request_dict("POST", "/api/v1/auth/register", json_body={"email": email, "password": password})
        self.set_access_token(cast(str | None, data.get("access_token")))
        return data

    def login(self, email: str, password: str) -> dict[str, Any]:
        data = self._request_dict("POST", "/api/v1/auth/login", json_body={"email": email, "password": password})
        self.set_access_token(cast(str | None, data.get("access_token")))
        return data

    def refresh(self) -> dict[str, Any]:
        data = self._request_dict("POST", "/api/v1/auth/refresh", allow_refresh=False)
        self.set_access_token(cast(str | None, data.get("access_token")))
        return data

    def google_start(self) -> dict[str, Any]:
        return self._request_dict("GET", "/api/v1/auth/google/start", allow_refresh=False)

    def google_exchange(self, oauth_code: str) -> dict[str, Any]:
        data = self._request_dict(
            "POST",
            "/api/v1/auth/google/exchange",
            json_body={"oauth_code": oauth_code},
            allow_refresh=False,
        )
        self.set_access_token(cast(str | None, data.get("access_token")))
        return data

    def logout(self) -> dict[str, Any]:
        data = self._request_dict("POST", "/api/v1/auth/logout", allow_refresh=False)
        self.set_access_token(None)
        self._session.cookies.clear()
        return data

    def upload_source(self, filename: str, content: bytes) -> dict[str, Any]:
        files = {"file": (filename, content)}
        return self._request_dict("POST", "/api/v1/sources/upload", files=files)

    def ingest_url(self, url: str, source_type: str) -> dict[str, Any]:
        return self._request_dict("POST", "/api/v1/sources/url", json_body={"url": url, "source_type": source_type})

    def list_sources(self) -> list[dict[str, Any]]:
        return self._request_list("GET", "/api/v1/sources")

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self._request_dict("GET", f"/api/v1/jobs/{job_id}")

    def dependency_health(self) -> dict[str, Any]:
        return self._request_dict("GET", "/api/v1/health/dependencies", allow_refresh=False)

    def get_source_chunks(self, source_id: str, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        return self._request_dict("GET", f"/api/v1/sources/{source_id}/chunks?limit={limit}&offset={offset}")

    def list_notebooks(self) -> list[dict[str, Any]]:
        return self._request_list("GET", "/api/v1/notebooks")

    def create_notebook(self, title: str, description: str | None = None) -> dict[str, Any]:
        payload = {"title": title, "description": description or None}
        return self._request_dict("POST", "/api/v1/notebooks", json_body=payload)

    def create_session(self, title: str) -> dict[str, Any]:
        return self._request_dict("POST", "/api/v1/chat/sessions", json_body={"title": title})

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._request_list("GET", "/api/v1/chat/sessions")

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        return self._request_list("GET", f"/api/v1/chat/sessions/{session_id}/messages")

    def send_message_stream(self, session_id: str, message: str, source_ids: list[str]) -> dict[str, Any]:
        text_buffer: list[str] = []
        final_citations: list[dict[str, Any]] = []
        model_info: dict[str, str] = {}
        confidence = "low"
        for payload in self.stream_message_events(session_id=session_id, message=message, source_ids=source_ids):
            if payload.get("type") == "token":
                text_buffer.append(str(payload.get("value", "")))
            if payload.get("type") == "final":
                content = payload.get("content")
                if isinstance(content, str) and content.strip():
                    text_buffer = [content]
                citations = payload.get("citations")
                if isinstance(citations, list):
                    final_citations = [cast(dict[str, Any], item) for item in citations if isinstance(item, dict)]
                info = payload.get("model_info")
                if isinstance(info, dict):
                    model_info = {str(key): str(value) for key, value in info.items()}
                confidence = str(payload.get("confidence", "low"))
        return {
            "content": "".join(text_buffer).strip(),
            "citations": final_citations,
            "model_info": model_info,
            "confidence": confidence,
        }

    def stream_message_events(self, session_id: str, message: str, source_ids: list[str]) -> Iterator[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/chat/sessions/{session_id}/messages"
        response = self._session.post(
            url,
            headers=self._auth_headers(),
            json={"message": message, "source_ids": source_ids},
            stream=True,
            timeout=120,
        )
        try:
            if response.status_code == 401:
                self.refresh()
                response.close()
                response = self._session.post(
                    url,
                    headers=self._auth_headers(),
                    json={"message": message, "source_ids": source_ids},
                    stream=True,
                    timeout=120,
                )
            if response.status_code >= 400:
                raise _error_from_response(response)
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                payload = json.loads(line.replace("data: ", "", 1))
                if isinstance(payload, dict):
                    yield payload
        finally:
            response.close()

    def get_memory(self, session_id: str) -> dict[str, Any]:
        return self._request_dict("GET", f"/api/v1/memory/sessions/{session_id}")

    def create_podcast(self, source_ids: list[str], title: str) -> dict[str, Any]:
        return self._request_dict("POST", "/api/v1/podcasts", json_body={"source_ids": source_ids, "title": title})

    def get_podcast(self, podcast_id: str) -> dict[str, Any]:
        return self._request_dict("GET", f"/api/v1/podcasts/{podcast_id}")

    def retry_podcast(self, podcast_id: str, title: str) -> dict[str, Any]:
        return self._request_dict("POST", f"/api/v1/podcasts/{podcast_id}/retry", json_body={"title": title})

    def podcast_audio_url(self, podcast_id: str) -> str:
        return f"{self.base_url}/api/v1/podcasts/{podcast_id}/audio"

    def _request_data(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes]] | None = None,
        *,
        allow_refresh: bool = True,
    ) -> object:
        url = f"{self.base_url}{path}"
        try:
            response = self._session.request(
                method=method,
                url=url,
                json=json_body,
                files=files,
                headers=self._auth_headers(),
                timeout=45,
            )
        except requests.RequestException as exc:
            raise ApiError("Backend request failed", code="NETWORK_ERROR") from exc
        if response.status_code == 401 and allow_refresh and self._can_retry_with_refresh(path):
            response.close()
            self.refresh()
            return self._request_data(method, path, json_body, files, allow_refresh=False)
        if response.status_code >= 400:
            raise _error_from_response(response)
        payload = _json_or_empty_dict(response)
        return payload.get("data")

    def _request_dict(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes]] | None = None,
        *,
        allow_refresh: bool = True,
    ) -> dict[str, Any]:
        data = self._request_data(method, path, json_body, files, allow_refresh=allow_refresh)
        if not isinstance(data, dict):
            raise ApiError("Invalid backend response", code="INVALID_RESPONSE")
        return cast(dict[str, Any], data)

    def _request_list(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes]] | None = None,
        *,
        allow_refresh: bool = True,
    ) -> list[dict[str, Any]]:
        data = self._request_data(method, path, json_body, files, allow_refresh=allow_refresh)
        if not isinstance(data, list):
            raise ApiError("Invalid backend response", code="INVALID_RESPONSE")
        return [cast(dict[str, Any], item) for item in data if isinstance(item, dict)]

    def _can_retry_with_refresh(self, path: str) -> bool:
        if path.startswith("/api/v1/auth/"):
            return False
        return True

    def _auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers


def _json_or_empty_dict(response: requests.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return cast(dict[str, Any], body if isinstance(body, dict) else {})


def _error_from_response(response: requests.Response) -> ApiError:
    payload = _json_or_empty_dict(response)
    error = payload.get("error", {})
    if isinstance(error, dict):
        message = str(error.get("message", "Request failed"))
        code_raw = error.get("code")
        details_raw = error.get("details")
        code = str(code_raw) if code_raw is not None else f"HTTP_{response.status_code}"
        return ApiError(message, code=code, details=_normalize_error_details(details_raw))
    return ApiError(f"Request failed with status {response.status_code}", code=f"HTTP_{response.status_code}")


def _normalize_error_details(details: object) -> dict[str, Any] | list[dict[str, Any]] | None:
    if isinstance(details, dict):
        return cast(dict[str, Any], details)
    if isinstance(details, list):
        normalized: list[dict[str, Any]] = []
        for item in details:
            if isinstance(item, dict):
                normalized.append(cast(dict[str, Any], item))
        return normalized
    return None
