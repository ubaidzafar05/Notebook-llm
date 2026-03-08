from __future__ import annotations

from app.generation.response_generator import ResponseGenerator
from schemas.citation import Citation
from app.vector_store.collections import VectorRecord


def test_generate_answer_returns_insufficient_context_without_valid_citations() -> None:
    contexts = [
        VectorRecord(
            chunk_id="c1",
            source_id="s1",
            user_id="u1",
            text="This is source context",
            vector=[],
            metadata={},
        )
    ]
    answer, model_info, confidence = ResponseGenerator().generate_answer(
        question="What is this about?",
        contexts=contexts,
        citations=[],
    )
    assert "enough information" in answer
    assert model_info["provider"] == "none"
    assert confidence == "low"


def test_generate_answer_returns_insufficient_context_when_overlap_is_weak() -> None:
    contexts = [
        VectorRecord(
            chunk_id="c1",
            source_id="s1",
            user_id="u1",
            text="This context discusses unrelated astronomy details.",
            vector=[],
            metadata={},
        )
    ]
    citations = [
        Citation(
            source_id="s1",
            chunk_id="c1",
            excerpt="unrelated astronomy details",
            page_number=1,
        )
    ]
    answer, model_info, confidence = ResponseGenerator().generate_answer(
        question="How does notebook citation integrity work?",
        contexts=contexts,
        citations=citations,
    )
    assert "enough information" in answer
    assert model_info["provider"] == "none"
    assert confidence == "low"
