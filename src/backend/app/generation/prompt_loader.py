from __future__ import annotations

from pathlib import Path


def load_prompt(prompt_name: str) -> str:
    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / prompt_name
    return prompt_path.read_text(encoding="utf-8")
