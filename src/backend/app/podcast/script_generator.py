from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.core.exceptions import AppError
from app.generation.llm_router import LlmRouter
from app.generation.prompt_loader import load_prompt
from schemas.podcast_script import PodcastScript


class ScriptGenerator:
    def __init__(self) -> None:
        self.router = LlmRouter()
        self.prompt = load_prompt("podcast_system_prompt.md")

    def generate(self, title: str, source_context: str) -> tuple[PodcastScript, dict[str, str]]:
        user_prompt = f"Title: {title}\n\nSource Context:\n{source_context[:12000]}"
        raw_script, model_info = self.router.generate(system_prompt=self.prompt, user_prompt=user_prompt)
        return _parse_script(raw_script), model_info


def _parse_script(raw_script: str) -> PodcastScript:
    parsed = _parse_json_script(raw_script)
    if parsed is not None:
        return parsed
    return _parse_labelled_script(raw_script)


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
