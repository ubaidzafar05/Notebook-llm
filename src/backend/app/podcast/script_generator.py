from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.generation.llm_router import LlmRouter
from app.generation.prompt_loader import load_prompt
from schemas.podcast_script import PodcastScript


class ScriptGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.router = LlmRouter()
        self.prompt = load_prompt("podcast_system_prompt.md")

    def generate(self, title: str, source_context: str) -> tuple[PodcastScript, dict[str, str]]:
        user_prompt = f"Title: {title.strip()}\n\nSource Context:\n{source_context[:self.settings.podcast_context_max_chars]}"
        raw_script, model_info = self.router.generate(
            system_prompt=self.prompt,
            user_prompt=user_prompt,
            timeout_seconds=self.settings.ollama_podcast_timeout_seconds,
        )
        return _parse_script(raw_script), model_info


def _parse_script(raw_script: str) -> PodcastScript:
    normalized_script = _normalize_script(raw_script)
    parsed = _parse_json_script(normalized_script)
    if parsed is not None:
        return parsed
    return _parse_labelled_script(normalized_script)


def _normalize_script(raw_script: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", raw_script, flags=re.DOTALL | re.IGNORECASE).strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fence_match is not None:
        cleaned = fence_match.group(1).strip()
    json_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if json_match is not None:
        return json_match.group(0).strip()
    return cleaned


def _parse_json_script(raw_script: str) -> PodcastScript | None:
    try:
        payload = json.loads(raw_script)
    except json.JSONDecodeError:
        return None
    try:
        return PodcastScript.model_validate(payload)
    except ValidationError as exc:
        raise AppError(
            code="PODCAST_SCRIPT_INVALID",
            message="Model returned invalid podcast script structure",
            status_code=502,
            details={"error": str(exc)},
        ) from exc


def _parse_labelled_script(raw_script: str) -> PodcastScript:
    lines: list[dict[str, str]] = []
    for line in raw_script.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        matched = re.match(r"^(HOST|ANALYST)\s*:\s*(.+)$", cleaned)
        if matched is None:
            continue
        lines.append({"speaker": matched.group(1), "text": matched.group(2).strip()})
    if not lines:
        raise AppError(
            code="PODCAST_SCRIPT_INVALID",
            message="Model returned no parseable podcast turns",
            status_code=502,
        )
    try:
        return PodcastScript.model_validate({"turns": lines})
    except ValidationError as exc:
        raise AppError(
            code="PODCAST_SCRIPT_INVALID",
            message="Model returned invalid podcast turn sequence",
            status_code=502,
            details={"error": str(exc)},
        ) from exc
