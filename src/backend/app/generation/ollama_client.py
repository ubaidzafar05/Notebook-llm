from __future__ import annotations

import logging
from time import perf_counter

import requests

from app.core.circuit_breaker import CircuitBreaker
from app.core.exceptions import AppError
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @CircuitBreaker(name="ollama_generate", failure_threshold=3, recovery_timeout=30, exceptions=(AppError, requests.RequestException))
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        timeout_seconds: int | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        options: dict[str, int | float] = {"temperature": 0.2}
        if max_output_tokens is not None:
            options["num_predict"] = max_output_tokens
        payload = {
            "model": self.settings.ollama_chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": options,
        }
        if self.settings.ollama_disable_thinking:
            payload["think"] = False
        body = self._post_json(
            path="/api/chat",
            payload=payload,
            timeout_seconds=timeout_seconds or self.settings.ollama_request_timeout_seconds,
        )
        message = body.get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise AppError(code="OLLAMA_INVALID_RESPONSE", message="Invalid Ollama response payload", status_code=502)
        answer = content.strip()
        if answer:
            return answer
        thinking = body.get("message", {}).get("thinking")
        logger.warning(
            "Ollama returned empty content model=%s has_thinking=%s done_reason=%s",
            self.settings.ollama_chat_model,
            isinstance(thinking, str) and bool(thinking.strip()),
            body.get("done_reason"),
        )
        raise AppError(code="OLLAMA_EMPTY_RESPONSE", message="Ollama returned empty content", status_code=502)

    def warm_model(self, *, timeout_seconds: int | None = None) -> None:
        payload = {
            "model": self.settings.ollama_chat_model,
            "messages": [{"role": "user", "content": "ping"}],
            "stream": False,
            "options": {"temperature": 0, "num_predict": 1},
        }
        if self.settings.ollama_disable_thinking:
            payload["think"] = False
        self._post_json(
            path="/api/chat",
            payload=payload,
            timeout_seconds=timeout_seconds or self.settings.ollama_prewarm_timeout_seconds,
        )

    def _post_json(self, *, path: str, payload: dict[str, object], timeout_seconds: int) -> dict[str, object]:
        start = perf_counter()
        try:
            response = requests.post(
                f"{self.settings.ollama_base_url}{path}",
                json=payload,
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except requests.Timeout as exc:
            logger.warning(
                "Ollama request timed out model=%s timeout_seconds=%s path=%s",
                self.settings.ollama_chat_model,
                timeout_seconds,
                path,
            )
            raise AppError(code="OLLAMA_TIMEOUT", message="Ollama request timed out", status_code=504) from exc
        except requests.RequestException as exc:
            logger.warning(
                "Ollama request failed model=%s timeout_seconds=%s path=%s error=%s",
                self.settings.ollama_chat_model,
                timeout_seconds,
                path,
                exc,
            )
            raise AppError(code="OLLAMA_UNAVAILABLE", message="Ollama request failed", status_code=502) from exc
        elapsed_ms = int((perf_counter() - start) * 1000)
        logger.info(
            "Ollama request completed model=%s path=%s elapsed_ms=%s timeout_seconds=%s",
            self.settings.ollama_chat_model,
            path,
            elapsed_ms,
            timeout_seconds,
        )
        if not isinstance(body, dict):
            raise AppError(code="OLLAMA_INVALID_RESPONSE", message="Invalid Ollama JSON payload", status_code=502)
        return body
