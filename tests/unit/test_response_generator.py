from __future__ import annotations

import pytest

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


def test_generate_answer_uses_llm_for_supported_context(monkeypatch: pytest.MonkeyPatch) -> None:
    contexts = [
        VectorRecord(
            chunk_id="c1",
            source_id="s1",
            user_id="u1",
            text="NotebookLM uses Ollama for generation and stores chunks in Postgres with vectors in Milvus.",
            vector=[],
            metadata={},
        )
    ]
    citations = [
        Citation(
            source_id="s1",
            chunk_id="c1",
            excerpt="uses Ollama for generation and stores chunks in Postgres with vectors in Milvus",
            page_number=1,
            score=0.45,
        )
    ]

    def _fake_generate(*args: object, **kwargs: object) -> tuple[str, dict[str, str]]:
        _ = (args, kwargs)
        return ("It uses Ollama, Postgres, and Milvus.", {"provider": "ollama", "fallback_used": "false"})

    monkeypatch.setattr("app.generation.response_generator.LlmRouter.generate", _fake_generate)
    answer, model_info, confidence = ResponseGenerator().generate_answer(
        question="What does the system architecture use for generation and storage?",
        contexts=contexts,
        citations=citations,
    )
    assert "Ollama" in answer
    assert model_info["provider"] == "ollama"
    assert confidence in {"medium", "high"}


def test_generate_answer_accepts_supported_listing_question(monkeypatch: pytest.MonkeyPatch) -> None:
    contexts = [
        VectorRecord(
            chunk_id="c1",
            source_id="s1",
            user_id="u1",
            text=(
                "NotebookLLM uses Postgres for state, Milvus for retrieval vectors, "
                "and Ollama qwen3:8b for grounded answers. The system exports markdown "
                "and pdf research reports."
            ),
            vector=[],
            metadata={},
        )
    ]
    citations = [
        Citation(
            source_id="s1",
            chunk_id="c1",
            excerpt="uses Postgres for state, Milvus for retrieval vectors, and Ollama qwen3:8b",
            page_number=1,
            score=0.4,
        )
    ]

    def _fake_generate(*args: object, **kwargs: object) -> tuple[str, dict[str, str]]:
        _ = (args, kwargs)
        return (
            "The notebook mentions Postgres, Milvus, Ollama qwen3:8b, markdown exports, and PDF reports.",
            {"provider": "ollama", "fallback_used": "false"},
        )

    monkeypatch.setattr("app.generation.response_generator.LlmRouter.generate", _fake_generate)
    answer, model_info, confidence = ResponseGenerator().generate_answer(
        question="What does the system architecture use for generation and storage?",
        contexts=contexts,
        citations=citations,
    )
    assert "Postgres" in answer
    assert model_info["provider"] == "ollama"
    assert confidence in {"medium", "high"}


def test_generate_answer_uses_extractive_fallback_for_blank_model_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contexts = [
        VectorRecord(
            chunk_id="c1",
            source_id="s1",
            user_id="u1",
            text="NotebookLM uses Postgres, Milvus, and Ollama qwen3:8b for grounded answers.",
            vector=[],
            metadata={},
        )
    ]
    citations = [
        Citation(
            source_id="s1",
            chunk_id="c1",
            excerpt="NotebookLM uses Postgres, Milvus, and Ollama qwen3:8b for grounded answers.",
            page_number=1,
            score=0.5,
        )
    ]

    def _fake_generate(*args: object, **kwargs: object) -> tuple[str, dict[str, str]]:
        _ = (args, kwargs)
        return ("   ", {"provider": "ollama", "fallback_used": "false"})

    monkeypatch.setattr("app.generation.response_generator.LlmRouter.generate", _fake_generate)
    answer, model_info, confidence = ResponseGenerator().generate_answer(
        question="What does the system architecture use for generation and storage?",
        contexts=contexts,
        citations=citations,
    )
    assert "Postgres" in answer
    assert model_info["fallback_used"] == "extractive"
    assert confidence in {"medium", "high"}
