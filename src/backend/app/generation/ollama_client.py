from __future__ import annotations

import requests

from app.core.circuit_breaker import CircuitBreaker
from app.core.config import get_settings


class OllamaClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @CircuitBreaker(name="ollama_generate", failure_threshold=3, recovery_timeout=30, exceptions=(requests.RequestException,))
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        timeout_seconds: int | None = None,
    ) -> str:
        payload = {
            "model": self.settings.ollama_chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.2},
        }
        response = requests.post(
            f"{self.settings.ollama_base_url}/api/chat",
            json=payload,
            timeout=timeout_seconds or self.settings.ollama_request_timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        message = body.get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise requests.RequestException("Invalid Ollama response")
        return content
