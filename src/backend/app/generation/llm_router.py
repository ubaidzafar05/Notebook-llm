from __future__ import annotations

from app.generation.ollama_client import OllamaClient


class LlmRouter:
    def __init__(self) -> None:
        self.ollama = OllamaClient()

    def generate(self, system_prompt: str, user_prompt: str) -> tuple[str, dict[str, str]]:
        answer = self.ollama.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        return answer, {"provider": "ollama", "fallback_used": "false"}
