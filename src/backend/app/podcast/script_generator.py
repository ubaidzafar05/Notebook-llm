from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.generation.llm_router import LlmRouter
from app.generation.prompt_loader import load_prompt
from schemas.podcast_script import PodcastScript

logger = logging.getLogger(__name__)


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
            max_output_tokens=420,
        )
        try:
            return _parse_script(raw_script), model_info
        except AppError as exc:
            if exc.code != "PODCAST_SCRIPT_INVALID" or exc.message != "Model returned no parseable podcast turns":
                raise
            logger.warning(
                "Podcast script parse failed; using deterministic fallback title=%s raw_excerpt=%s",
                title,
                raw_script[:240].replace("\n", " "),
            )
            return _build_fallback_script(title=title, source_context=source_context), {
                **model_info,
                "script_fallback": "template",
            }


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
    if isinstance(payload, list):
        payload = {"turns": payload}
    if isinstance(payload, dict) and "dialogue" in payload and "turns" not in payload:
        payload = {"turns": payload["dialogue"]}
    if isinstance(payload, dict) and isinstance(payload.get("turns"), list):
        payload = {"turns": [_normalize_turn(item) for item in payload["turns"]]}
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
    current: dict[str, str] | None = None
    for line in raw_script.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        matched = re.match(r"^(?:[-*]|\d+[.)])?\s*\**(host|analyst)\**\s*[:\-]\s*(.+)$", cleaned, flags=re.IGNORECASE)
        if matched is None:
            if current is not None:
                current["text"] = f"{current['text']} {cleaned}".strip()
            continue
        current = {"speaker": matched.group(1).upper(), "text": matched.group(2).strip()}
        lines.append(current)
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


def _normalize_turn(item: object) -> dict[str, str]:
    if not isinstance(item, dict):
        return {"speaker": "HOST", "text": str(item).strip()}
    speaker = str(item.get("speaker") or item.get("role") or "HOST").strip().upper()
    text = str(item.get("text") or item.get("content") or "").strip()
    return {"speaker": speaker, "text": text}


def _build_fallback_script(*, title: str, source_context: str) -> PodcastScript:
    facts = _extract_context_facts(source_context)
    opening = [
        {"speaker": "HOST", "text": f"Welcome back. Today we are reviewing {title.strip() or 'this notebook'}."},
        {"speaker": "ANALYST", "text": "This briefing stays grounded in the uploaded sources and avoids claims outside the notebook evidence."},
    ]
    body: list[dict[str, str]] = []
    for index, fact in enumerate(facts[:3], start=1):
        body.append({"speaker": "HOST", "text": f"What is source insight {index} that matters here?"})
        body.append({"speaker": "ANALYST", "text": fact})
    closing = [
        {"speaker": "HOST", "text": "What is the practical takeaway from these materials?"},
        {"speaker": "ANALYST", "text": "The notebook points to a grounded answer path: use the cited sources, inspect the excerpts, and keep conclusions tied to the available evidence."},
        {"speaker": "HOST", "text": "That keeps the discussion auditable instead of speculative."},
        {"speaker": "ANALYST", "text": "Exactly. The value here is not just the answer, but the supporting trail back to the notebook sources."},
    ]
    return PodcastScript.model_validate({"turns": opening + body + closing})


def _extract_context_facts(source_context: str) -> list[str]:
    facts: list[str] = []
    for line in source_context.splitlines():
        cleaned = " ".join(line.split()).strip(" -")
        if not cleaned or cleaned.lower().startswith(("source:", "type:", "summary:", "key excerpts:")):
            continue
        cleaned = re.sub(r"^\d+\.\s*(page\s+\d+:\s*)?", "", cleaned, flags=re.IGNORECASE)
        if cleaned:
            facts.append(cleaned)
    while len(facts) < 3:
        facts.append("The available sources provide limited detail, so this segment stays conservative and sticks to what was actually indexed.")
    return facts
