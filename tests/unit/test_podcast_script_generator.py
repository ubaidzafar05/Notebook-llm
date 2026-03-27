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
