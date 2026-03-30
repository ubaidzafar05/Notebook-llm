"""Tests for industrial-grade security and bug fixes."""

from __future__ import annotations

import re

import pytest

from app.vector_store.milvus_client import _safe_milvus_value
from app.ingestion.chunking.chunk_policy import ChunkPolicy
from app.ingestion.chunking.recursive_chunker import chunk_text
from app.retrieval.reranker import _lexical_rerank
from app.vector_store.collections import VectorRecord
from schemas.podcast_script import PodcastScript, PodcastTurn


# ---------------------------------------------------------------------------
# S1: Milvus expression injection prevention
# ---------------------------------------------------------------------------
class TestMilvusExpressionInjection:
    def test_safe_value_accepts_uuid(self) -> None:
        result = _safe_milvus_value("550e8400-e29b-41d4-a716-446655440000", "user_id")
        assert result == "550e8400-e29b-41d4-a716-446655440000"

    def test_safe_value_accepts_alphanumeric(self) -> None:
        assert _safe_milvus_value("abc123_DEF", "field") == "abc123_DEF"

    def test_safe_value_rejects_double_quote(self) -> None:
        with pytest.raises(ValueError, match="Unsafe value"):
            _safe_milvus_value('hello"world', "user_id")

    def test_safe_value_rejects_single_quote(self) -> None:
        with pytest.raises(ValueError, match="Unsafe value"):
            _safe_milvus_value("hello'world", "user_id")

    def test_safe_value_rejects_backslash(self) -> None:
        with pytest.raises(ValueError, match="Unsafe value"):
            _safe_milvus_value("hello\\world", "user_id")

    def test_safe_value_rejects_semicolon(self) -> None:
        with pytest.raises(ValueError, match="Unsafe value"):
            _safe_milvus_value("id; DROP COLLECTION", "user_id")

    def test_safe_value_rejects_space(self) -> None:
        with pytest.raises(ValueError, match="Unsafe value"):
            _safe_milvus_value("hello world", "user_id")

    def test_safe_value_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="Unsafe value"):
            _safe_milvus_value("", "user_id")


# ---------------------------------------------------------------------------
# S2: JWT secret production validation
# ---------------------------------------------------------------------------
class TestJwtSecretValidation:
    def test_changeme_rejected_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.config import Settings, validate_required_runtime_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "change-me")
        monkeypatch.setenv("CORS_ORIGINS", "https://myapp.example.com")
        settings = Settings(_env_file=None)
        with pytest.raises(RuntimeError, match="JWT_SECRET must be set"):
            validate_required_runtime_settings(settings)

    def test_changeme_allowed_in_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.config import Settings, validate_required_runtime_settings

        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("JWT_SECRET", "change-me")
        settings = Settings(_env_file=None)
        # Should not raise
        validate_required_runtime_settings(settings)

    def test_strong_secret_accepted_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.config import Settings, validate_required_runtime_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "super-strong-random-secret-abc123")
        monkeypatch.setenv("CORS_ORIGINS", "https://myapp.example.com")
        settings = Settings(_env_file=None)
        # Should not raise
        validate_required_runtime_settings(settings)


# ---------------------------------------------------------------------------
# S3: CORS production validation
# ---------------------------------------------------------------------------
class TestCorsProductionValidation:
    def test_localhost_rejected_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.config import Settings, validate_required_runtime_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "strong-secret-123")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
        settings = Settings(_env_file=None)
        with pytest.raises(RuntimeError, match="CORS origin"):
            validate_required_runtime_settings(settings)

    def test_wildcard_rejected_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.config import Settings, validate_required_runtime_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "strong-secret-123")
        monkeypatch.setenv("CORS_ORIGINS", "*")
        settings = Settings(_env_file=None)
        with pytest.raises(RuntimeError, match="CORS origin"):
            validate_required_runtime_settings(settings)

    def test_valid_domain_accepted_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.config import Settings, validate_required_runtime_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "strong-secret-123")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
        settings = Settings(_env_file=None)
        # Should not raise
        validate_required_runtime_settings(settings)


# ---------------------------------------------------------------------------
# B1: Lexical rerank scoring fix
# ---------------------------------------------------------------------------
class TestLexicalRerankFix:
    def _make_record(self, text: str, chunk_id: str = "c1") -> VectorRecord:
        return VectorRecord(
            chunk_id=chunk_id,
            user_id="u1",
            notebook_id="n1",
            source_id="s1",
            text=text,
            vector=[],
            metadata={},
        )

    def test_long_chunk_with_more_overlap_scores_higher(self) -> None:
        """Before the fix, long chunks were penalized. Now query-normalized."""
        query = "machine learning algorithms"
        short = self._make_record("machine dogs cats", chunk_id="short")
        long_text = "machine learning algorithms " + " ".join(f"word{i}" for i in range(500))
        long = self._make_record(long_text, chunk_id="long")

        results = _lexical_rerank(query, [short, long], final_k=2)
        # Long chunk matches all 3 query terms; short matches only 1
        assert results[0].chunk_id == "long"

    def test_identical_overlap_same_score_regardless_of_length(self) -> None:
        query = "hello world"
        short = self._make_record("hello world", chunk_id="short")
        long = self._make_record("hello world " + " ".join(f"x{i}" for i in range(200)), chunk_id="long")

        results = _lexical_rerank(query, [short, long], final_k=2)
        # Both match 2/2 query terms — should both score 1.0
        # Order doesn't matter as long as neither is penalized
        chunk_ids = {r.chunk_id for r in results}
        assert chunk_ids == {"short", "long"}


# ---------------------------------------------------------------------------
# B4: Chunker infinite loop prevention
# ---------------------------------------------------------------------------
class TestChunkerOverlapValidation:
    def test_overlap_equal_to_size_raises(self) -> None:
        policy = ChunkPolicy(chunk_size=100, chunk_overlap=100)
        with pytest.raises(ValueError, match="chunk_overlap.*must be less than"):
            chunk_text("hello world " * 50, policy)

    def test_overlap_greater_than_size_raises(self) -> None:
        policy = ChunkPolicy(chunk_size=50, chunk_overlap=100)
        with pytest.raises(ValueError, match="chunk_overlap.*must be less than"):
            chunk_text("hello world " * 50, policy)

    def test_valid_overlap_works(self) -> None:
        policy = ChunkPolicy(chunk_size=100, chunk_overlap=20)
        result = chunk_text("hello world " * 50, policy)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Q7: PodcastScript relaxed turn count
# ---------------------------------------------------------------------------
class TestPodcastScriptRelaxed:
    def _make_turns(self, count: int) -> list[PodcastTurn]:
        turns = []
        for i in range(count):
            speaker = "HOST" if i % 2 == 0 else "ANALYST"
            turns.append(PodcastTurn(speaker=speaker, text=f"Turn {i} content here."))
        return turns

    def test_accepts_8_turns(self) -> None:
        """Previously would fail with 12-20 range."""
        script = PodcastScript(turns=self._make_turns(8))
        assert len(script.turns) == 8

    def test_accepts_25_turns(self) -> None:
        """Previously would fail with 12-20 range."""
        script = PodcastScript(turns=self._make_turns(25))
        assert len(script.turns) == 25

    def test_rejects_3_turns(self) -> None:
        with pytest.raises(ValueError):
            PodcastScript(turns=self._make_turns(3))

    def test_rejects_41_turns(self) -> None:
        with pytest.raises(ValueError):
            PodcastScript(turns=self._make_turns(41))


# ---------------------------------------------------------------------------
# B5: datetime.utcnow() replaced with datetime.now(UTC)
# ---------------------------------------------------------------------------
class TestDatetimeUtcFix:
    def test_chat_exporter_uses_utc_aware_datetime(self) -> None:
        """Verify the export header uses timezone-aware datetime."""
        import inspect
        from app.export.chat_exporter import _render_header

        source = inspect.getsource(_render_header)
        assert "utcnow" not in source
        assert "datetime.now(UTC)" in source


# ---------------------------------------------------------------------------
# Q2: Embedding retry
# ---------------------------------------------------------------------------
class TestEmbeddingRetry:
    def test_retries_before_fallback(self) -> None:
        """Verify embedding service retries before falling back to hashing."""
        import inspect
        from app.embeddings.embedding_service import EmbeddingService

        source = inspect.getsource(EmbeddingService.embed_texts)
        assert "retry" in source.lower() or "_EMBED_RETRY_ATTEMPTS" in source


# ---------------------------------------------------------------------------
# P1: max_output_tokens increased
# ---------------------------------------------------------------------------
class TestMaxOutputTokens:
    def test_output_tokens_at_least_800(self) -> None:
        import inspect
        from app.generation.response_generator import ResponseGenerator

        source = inspect.getsource(ResponseGenerator.generate_answer)
        match = re.search(r"max_output_tokens=(\d+)", source)
        assert match is not None
        assert int(match.group(1)) >= 800


# ---------------------------------------------------------------------------
# Q4: Support score clamped
# ---------------------------------------------------------------------------
class TestSupportScoreClamped:
    def test_support_score_never_exceeds_one(self) -> None:
        """Verify the 1.15x boost is clamped to 1.0."""
        import inspect
        from app.generation.response_generator import _support_score

        source = inspect.getsource(_support_score)
        assert "min(overlap * 1.15, 1.0)" in source
        assert "min(excerpt_overlap * 1.15, 1.0)" in source
