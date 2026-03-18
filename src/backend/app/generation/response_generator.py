from __future__ import annotations

from typing import Literal

from schemas.citation import Citation

from app.generation.llm_router import LlmRouter
from app.generation.prompt_loader import load_prompt
from app.retrieval.semantic_cache import SemanticCacheService
from app.vector_store.collections import VectorRecord


class ResponseGenerator:
    def __init__(self) -> None:
        self.router = LlmRouter()
        self.answer_prompt = load_prompt("answer_system_prompt.md")
        self.cache = SemanticCacheService()

    def generate_answer(
        self,
        question: str,
        contexts: list[VectorRecord],
        citations: list[Citation],
        memory_context: str = "",
    ) -> tuple[str, dict[str, str], Literal["low", "medium", "high"]]:
        chunk_ids = [item.chunk_id for item in contexts]
        cached = self.cache.get_cached_answer(question=question, chunk_ids=chunk_ids)
        if cached is not None:
            cached_text, raw_citations = cached
            recovered_citations = [Citation(**c) for c in raw_citations]
            confidence_val = _compute_confidence(citations=recovered_citations, contexts=contexts)
            return cached_text, {"provider": "cache", "fallback_used": "false"}, confidence_val

        support_score = _support_score(question=question, contexts=contexts, citations=citations)
        if support_score < 0.18:
            return (
                "I do not have enough information in your sources to answer that.",
                {"provider": "none", "fallback_used": "false", "support_score": f"{support_score:.3f}"},
                "low",
            )

        context_block = "\n\n".join(
            f"[chunk:{item.chunk_id}] {item.text[:1000]}" for item in contexts
        )
        user_prompt = (
            f"Question:\n{question}\n\n"
            f"Conversation Memory:\n{memory_context[:2000]}\n\n"
            f"Context:\n{context_block}\n\n"
            "Answer using only the context."
        )
        answer_text, model_info = self.router.generate(system_prompt=self.answer_prompt, user_prompt=user_prompt)
        final_answer = _append_missing_citations(answer_text=answer_text, citations=citations)
        confidence = _compute_confidence(citations=citations, contexts=contexts)

        # Write to cache asynchronously or fire-and-forget
        self.cache.store_answer(
            question=question,
            chunk_ids=chunk_ids,
            answer=final_answer,
            citations=[c.model_dump() for c in citations]
        )

        return final_answer, model_info, confidence


def _append_missing_citations(answer_text: str, citations: list[Citation]) -> str:
    if not citations:
        return answer_text
    first_chunk_id = citations[0].chunk_id
    if f"[chunk:{first_chunk_id}]" in answer_text:
        return answer_text
    citation_suffix = " ".join(f"[chunk:{citation.chunk_id}]" for citation in citations[:3])
    return f"{answer_text}\n\nSources: {citation_suffix}".strip()


def _compute_confidence(
    citations: list[Citation],
    contexts: list[VectorRecord],
) -> Literal["low", "medium", "high"]:
    if not contexts or not citations:
        return "low"
    # Factor 1: citation count
    citation_score = min(len(citations), 5) / 5.0
    # Factor 2: average citation quality score (if available)
    scored = [c.score for c in citations if c.score is not None and c.score > 0]
    avg_score = sum(scored) / len(scored) if scored else 0.0
    # Factor 3: coverage — cited chunks as fraction of retrieved contexts
    cited_ids = {c.chunk_id for c in citations}
    coverage = len(cited_ids.intersection(ctx.chunk_id for ctx in contexts)) / max(len(contexts), 1)
    composite = (citation_score * 0.4) + (avg_score * 0.3) + (coverage * 0.3)
    if composite >= 0.55:
        return "high"
    if composite >= 0.25:
        return "medium"
    return "low"


def _support_score(
    *,
    question: str,
    contexts: list[VectorRecord],
    citations: list[Citation],
) -> float:
    if not contexts or not citations:
        return 0.0
    query_terms = {item for item in question.lower().split() if len(item) > 2}
    if not query_terms:
        return 0.25 if citations else 0.0
    best_overlap = 0.0
    cited_chunk_ids = {citation.chunk_id for citation in citations}
    for context in contexts[:6]:
        terms = {item for item in context.text.lower().split() if len(item) > 2}
        overlap = len(query_terms.intersection(terms)) / max(len(query_terms), 1)
        if context.chunk_id in cited_chunk_ids:
            overlap = overlap * 1.15
        if overlap > best_overlap:
            best_overlap = overlap
    citation_factor = min(len(citations), 3) / 3
    return (best_overlap * 0.75) + (citation_factor * 0.25)
