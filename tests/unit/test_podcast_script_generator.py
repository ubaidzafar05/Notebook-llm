from __future__ import annotations

import pytest

from app.core.exceptions import AppError
from app.podcast.script_generator import ScriptGenerator


def test_script_generator_parses_json_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_generate(*_: object, **__: object) -> tuple[str, dict[str, str]]:
        content = {
            "turns": [
                {"speaker": "HOST", "text": "Welcome to the briefing."},
                {"speaker": "ANALYST", "text": "We focus on grounded source evidence."},
                {"speaker": "HOST", "text": "What are the key findings?"},
                {"speaker": "ANALYST", "text": "Citations map to source chunks."},
                {"speaker": "HOST", "text": "How does memory help?"},
                {"speaker": "ANALYST", "text": "Zep keeps notebook context coherent."},
                {"speaker": "HOST", "text": "Can users verify claims?"},
                {"speaker": "ANALYST", "text": "Yes, anchors include page or timestamp."},
                {"speaker": "HOST", "text": "What about retrieval quality?"},
                {"speaker": "ANALYST", "text": "Reranking improves relevance ordering."},
                {"speaker": "HOST", "text": "Is failover in place?"},
                {"speaker": "ANALYST", "text": "Generation can fall back on provider outage."},
            ]
        }
        import json

        return json.dumps(content), {"provider": "test"}

    generator = ScriptGenerator()
    monkeypatch.setattr(generator.router, "generate", _fake_generate)
    script, info = generator.generate(title="Test", source_context="context")
    assert info["provider"] == "test"
    assert len(script.turns) == 12
    assert script.turns[0].speaker == "HOST"
    assert script.turns[1].speaker == "ANALYST"


def test_script_generator_rejects_invalid_script(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_generate(*_: object, **__: object) -> tuple[str, dict[str, str]]:
        return '{"turns":[{"speaker":"HOST","text":"Only one turn"}]}', {"provider": "test"}

    generator = ScriptGenerator()
    monkeypatch.setattr(generator.router, "generate", _fake_generate)
    with pytest.raises(AppError) as exc:
        generator.generate(title="Bad", source_context="context")
    assert exc.value.code == "PODCAST_SCRIPT_INVALID"


def test_script_generator_parses_fenced_json_with_think_block(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_generate(*_: object, **__: object) -> tuple[str, dict[str, str]]:
        return (
            "<think>reasoning</think>\n```json\n"
            '{"turns":[{"speaker":"HOST","text":"Opening."},{"speaker":"ANALYST","text":"Detail one."},'
            '{"speaker":"HOST","text":"Question two."},{"speaker":"ANALYST","text":"Answer two."},'
            '{"speaker":"HOST","text":"Question three."},{"speaker":"ANALYST","text":"Answer three."},'
            '{"speaker":"HOST","text":"Question four."},{"speaker":"ANALYST","text":"Answer four."},'
            '{"speaker":"HOST","text":"Question five."},{"speaker":"ANALYST","text":"Answer five."},'
            '{"speaker":"HOST","text":"Question six."},{"speaker":"ANALYST","text":"Answer six."}]}\n```',
            {"provider": "test"},
        )

    generator = ScriptGenerator()
    monkeypatch.setattr(generator.router, "generate", _fake_generate)
    script, info = generator.generate(title="Wrapped", source_context="context")
    assert info["provider"] == "test"
    assert len(script.turns) == 12
    assert script.turns[0].text == "Opening."


def test_script_generator_falls_back_when_model_returns_unlabelled_text(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_generate(*_: object, **__: object) -> tuple[str, dict[str, str]]:
        return ("This is a prose summary without JSON or speaker labels.", {"provider": "test"})

    generator = ScriptGenerator()
    monkeypatch.setattr(generator.router, "generate", _fake_generate)
    script, info = generator.generate(
        title="Fallback",
        source_context="Source: Audit\nType: text\nKey excerpts:\n1. Postgres stores notebook state.\n2. Milvus stores retrieval vectors.",
    )
    assert info["provider"] == "test"
    assert info["script_fallback"] == "template"
    assert len(script.turns) == 12
    assert script.turns[0].speaker == "HOST"
    assert any("Postgres stores notebook state." in turn.text for turn in script.turns)


def test_script_generator_parses_markdown_labelled_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_generate(*_: object, **__: object) -> tuple[str, dict[str, str]]:
        return (
            "**HOST:** Welcome.\n"
            "**ANALYST:** Grounded detail one.\n"
            "1. HOST - What changed?\n"
            "2. ANALYST - Grounded detail two.\n"
            "HOST: Question three.\n"
            "ANALYST: Detail three.\n"
            "HOST: Question four.\n"
            "ANALYST: Detail four.\n"
            "HOST: Question five.\n"
            "ANALYST: Detail five.\n"
            "HOST: Question six.\n"
            "ANALYST: Detail six.",
            {"provider": "test"},
        )

    generator = ScriptGenerator()
    monkeypatch.setattr(generator.router, "generate", _fake_generate)
    script, info = generator.generate(title="Markdown", source_context="context")
    assert info["provider"] == "test"
    assert len(script.turns) == 12
    assert script.turns[1].speaker == "ANALYST"
