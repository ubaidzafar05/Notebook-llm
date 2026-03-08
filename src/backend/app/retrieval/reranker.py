from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.vector_store.collections import VectorRecord


def rerank(query: str, candidates: list[VectorRecord], final_k: int = 5) -> list[VectorRecord]:
    settings = get_settings()
    if settings.enable_cross_encoder_rerank:
        cross_ranked = _cross_encoder_rerank(
            query=query,
            candidates=candidates,
            model_name=settings.cross_encoder_model,
        )
        if cross_ranked is not None:
            return cross_ranked[:final_k]
    return _lexical_rerank(query=query, candidates=candidates, final_k=final_k)


def _lexical_rerank(query: str, candidates: list[VectorRecord], final_k: int) -> list[VectorRecord]:
    query_terms = set(query.lower().split())
    scored: list[tuple[float, VectorRecord]] = []
    for candidate in candidates:
        terms = set(candidate.text.lower().split())
        overlap = len(query_terms.intersection(terms))
        length_penalty = max(len(terms), 1)
        score = overlap / length_penalty
        scored.append((score, candidate))

    scored.sort(key=lambda row: row[0], reverse=True)
    return [item for _, item in scored[:final_k]]


def _cross_encoder_rerank(
    query: str,
    candidates: list[VectorRecord],
    model_name: str,
) -> list[VectorRecord] | None:
    if not candidates:
        return []
    try:
        model = _get_cross_encoder_model(model_name)
    except Exception:  # noqa: BLE001
        return None

    pairs = [(query, candidate.text[:1500]) for candidate in candidates]
    raw_scores = model.predict(pairs)
    scored: list[tuple[float, VectorRecord]] = []
    for idx, candidate in enumerate(candidates):
        score = float(raw_scores[idx])
        scored.append((score, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [candidate for _, candidate in scored]


@lru_cache(maxsize=2)
def _get_cross_encoder_model(model_name: str) -> Any:
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)
