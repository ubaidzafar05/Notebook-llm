from __future__ import annotations

from dataclasses import dataclass

from app.vector_store.collections import VectorRecord
from schemas.citation import Citation


@dataclass(frozen=True, slots=True)
class ScoredCitation:
    citation: Citation
    score: float
    quality_label: str


def score_citations(
    *,
    question: str,
    records: list[VectorRecord],
    citations: list[Citation],
) -> list[Citation]:
    if not citations:
        return citations
    rank_by_chunk = {record.chunk_id: idx for idx, record in enumerate(records)}
    text_by_chunk = {record.chunk_id: record.text for record in records}
    question_terms = _tokenize(question)
    scored: list[ScoredCitation] = []
    for citation in citations:
        chunk_text = text_by_chunk.get(citation.chunk_id, "")
        overlap = _overlap_score(question_terms, _tokenize(chunk_text))
        rank_score = _rank_score(rank_by_chunk.get(citation.chunk_id), len(records))
        score = (overlap * 0.7) + (rank_score * 0.3)
        scored.append(
            ScoredCitation(
                citation=citation,
                score=score,
                quality_label=_quality_label(score),
            )
        )
    return [
        citation.model_copy(update={"score": item.score, "quality_label": item.quality_label})
        for item in scored
    ]


def _tokenize(text: str) -> set[str]:
    return {token for token in text.lower().split() if token}


def _overlap_score(query_terms: set[str], doc_terms: set[str]) -> float:
    if not query_terms or not doc_terms:
        return 0.0
    overlap = len(query_terms.intersection(doc_terms))
    return overlap / max(len(query_terms), 1)


def _rank_score(rank: int | None, total: int) -> float:
    if rank is None or total <= 0:
        return 0.0
    return max(0.0, 1.0 - (rank / max(total - 1, 1)))


def _quality_label(score: float) -> str:
    if score >= 0.66:
        return "high"
    if score >= 0.33:
        return "medium"
    return "low"
