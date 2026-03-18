import pytest

from app.core.redis_client import _get_test_redis
from app.retrieval.semantic_cache import SemanticCacheService


def test_semantic_cache_hit_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.retrieval.semantic_cache.get_redis_client", lambda: _get_test_redis())
    cache = SemanticCacheService()
    question = "What is NotebookLLM?"
    chunk_ids = ["chunk_1", "chunk_2"]

    # Should be a miss initially
    assert cache.get_cached_answer(question, chunk_ids) is None

    # Store it
    answer_text = "NotebookLLM is an AI research assistant."
    citations = [{"chunk_id": "chunk_1", "document_id": "doc_1", "text": "test"}]

    cache.store_answer(question, chunk_ids, answer_text, citations)

    # Should be a hit now
    hit = cache.get_cached_answer(question, chunk_ids)
    assert hit is not None
    assert hit[0] == answer_text
    assert len(hit[1]) == 1
    assert hit[1][0]["chunk_id"] == "chunk_1"

    # Slightly different question should still hit exact match due to normalization
    hit2 = cache.get_cached_answer("what is notebookllm?", chunk_ids)
    assert hit2 is not None

    # Different chunks should be a miss
    miss = cache.get_cached_answer(question, ["chunk_3"])
    assert miss is None
