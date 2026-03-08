from __future__ import annotations

from app.retrieval.reranker import rerank
from app.vector_store.collections import VectorRecord


def test_rerank_prefers_higher_term_overlap() -> None:
    candidates = [
        VectorRecord(
            chunk_id="c1",
            source_id="s1",
            user_id="u1",
            text="vector database retrieval context",
            vector=[],
            metadata={},
        ),
        VectorRecord(
            chunk_id="c2",
            source_id="s1",
            user_id="u1",
            text="podcast generation script voice",
            vector=[],
            metadata={},
        ),
    ]
    ranked = rerank(query="retrieval vector", candidates=candidates, final_k=1)
    assert len(ranked) == 1
    assert ranked[0].chunk_id == "c1"
