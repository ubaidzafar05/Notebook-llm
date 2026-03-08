from __future__ import annotations

import requests

from app.core.config import get_settings
from app.core.exceptions import AppError


class OpenRouterClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.settings.openrouter_api_key:
            raise AppError(code="OPENROUTER_NOT_CONFIGURED", message="OpenRouter API key missing", status_code=503)

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        response = requests.post(
            f"{self.settings.openrouter_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=90,
        )
        response.raise_for_status()
        body = response.json()
        choices = body.get("choices", [])
        if not choices:
            raise requests.RequestException("OpenRouter returned empty choices")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise requests.RequestException("OpenRouter response content missing")
        return content
