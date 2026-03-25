"""Integration tests for SemanticCacheService with reverse index."""

from __future__ import annotations

import pytest

from app.core.redis_client import _get_test_redis
from app.retrieval.semantic_cache import SemanticCacheService


@pytest.fixture()
def cache(monkeypatch: pytest.MonkeyPatch) -> SemanticCacheService:
    monkeypatch.setattr("app.retrieval.semantic_cache.get_redis_client", lambda: _get_test_redis())
    return SemanticCacheService()


class TestSemanticCacheReverseIndex:
    def test_store_and_retrieve_with_source_ids(self, cache: SemanticCacheService) -> None:
        cache.store_answer(
            question="What is RAG?",
            chunk_ids=["c1", "c2"],
            answer="RAG is retrieval-augmented generation.",
            citations=[{"chunk_id": "c1", "source_id": "s1"}],
            source_ids=["s1"],
        )
        hit = cache.get_cached_answer("What is RAG?", ["c1", "c2"])
        assert hit is not None
        assert "RAG" in hit[0]

    def test_targeted_invalidation_removes_only_affected_entries(self, cache: SemanticCacheService) -> None:
        # Store two entries from different sources
        cache.store_answer(
            question="Q from source A",
            chunk_ids=["ca1"],
            answer="Answer A",
            citations=[],
            source_ids=["source_a"],
        )
        cache.store_answer(
            question="Q from source B",
            chunk_ids=["cb1"],
            answer="Answer B",
            citations=[],
            source_ids=["source_b"],
        )

        # Both should be cached
        assert cache.get_cached_answer("Q from source A", ["ca1"]) is not None
        assert cache.get_cached_answer("Q from source B", ["cb1"]) is not None

        # Invalidate source_a
        cache.invalidate_for_source("source_a")

        # source_a entry gone, source_b still present
        assert cache.get_cached_answer("Q from source A", ["ca1"]) is None
        assert cache.get_cached_answer("Q from source B", ["cb1"]) is not None

    def test_invalidation_without_index_falls_back_to_flush(self, cache: SemanticCacheService) -> None:
        # Store without source_ids (no reverse index)
        cache.store_answer(
            question="No index question",
            chunk_ids=["cx1"],
            answer="Answer X",
            citations=[],
        )
        assert cache.get_cached_answer("No index question", ["cx1"]) is not None

        # Invalidate unknown source — triggers full flush
        cache.invalidate_for_source("unknown_source")

        # After full flush, entry should be gone
        assert cache.get_cached_answer("No index question", ["cx1"]) is None

    def test_cache_miss_returns_none(self, cache: SemanticCacheService) -> None:
        assert cache.get_cached_answer("nonexistent", ["c99"]) is None
