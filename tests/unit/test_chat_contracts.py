from __future__ import annotations

import json

from app.api.v1.chat_routes import _stream_answer
from app.retrieval.citation_guard import filter_citations_by_chunk_ids
from schemas.citation import Citation


def test_validate_citations_filters_out_unknown_chunk_ids() -> None:
    citations = [
        Citation(source_id="s1", chunk_id="c1", excerpt="alpha"),
        Citation(source_id="s1", chunk_id="c2", excerpt="beta"),
    ]
    validated = filter_citations_by_chunk_ids(citations=citations, valid_chunk_ids={"c1"})
    assert len(validated) == 1
    assert validated[0].chunk_id == "c1"


def test_stream_final_event_includes_required_contract_fields() -> None:
    stream = _stream_answer(
        answer_text="hello world",
        citations=[{"source_id": "s1", "chunk_id": "c1", "excerpt": "x"}],
        model_info={"provider": "ollama", "fallback_used": "false"},
        confidence="medium",
    )
    events = list(stream)
    final_line = next(line for line in events if '"type": "final"' in line)
    payload = json.loads(final_line.replace("data: ", "").strip())

    assert payload["type"] == "final"
    assert "content" in payload
    assert "citations" in payload
    assert "model_info" in payload
    assert "confidence" in payload
