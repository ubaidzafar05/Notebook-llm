from __future__ import annotations

import logging

import requests

from app.generation.ollama_client import OllamaClient
from app.generation.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class LlmRouter:
    def __init__(self) -> None:
        self.ollama = OllamaClient()
        self.openrouter = OpenRouterClient()

    def generate(self, system_prompt: str, user_prompt: str) -> tuple[str, dict[str, str]]:
        try:
            answer = self.ollama.generate(system_prompt=system_prompt, user_prompt=user_prompt)
            return answer, {"provider": "ollama", "fallback_used": "false"}
        except requests.RequestException as primary_error:
            logger.warning("Ollama generation failed; trying OpenRouter fallback: %s", primary_error)
            answer = self.openrouter.generate(system_prompt=system_prompt, user_prompt=user_prompt)
            return answer, {"provider": "openrouter", "fallback_used": "true"}
