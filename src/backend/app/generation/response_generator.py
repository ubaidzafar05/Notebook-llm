from __future__ import annotations

import re
from typing import Literal

from schemas.citation import Citation

from app.generation.llm_router import LlmRouter
from app.generation.prompt_loader import load_prompt
from app.retrieval.semantic_cache import SemanticCacheService
from app.vector_store.collections import VectorRecord

STOPWORDS = {
    "about",
    "answer",
    "answers",
    "does",
    "from",
    "have",
    "into",
    "just",
    "mention",
    "mentions",
    "more",
    "notebook",
    "only",
    "says",
    "should",
    "source",
    "sources",
    "that",
    "their",
    "there",
    "these",
    "this",
    "what",
    "when",
    "where",
    "which",
    "with",
    "your",
}


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
        if support_score < 0.12:
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
        answer_text, model_info = self.router.generate(
            system_prompt=self.answer_prompt,
            user_prompt=user_prompt,
            max_output_tokens=240,
        )
        answer_text, model_info = _normalize_generated_answer(
            answer_text=answer_text,
            model_info=model_info,
            citations=citations,
            contexts=contexts,
        )
        final_answer = _append_missing_citations(answer_text=answer_text, citations=citations)
        confidence = _compute_confidence(citations=citations, contexts=contexts)

        # Write to cache asynchronously or fire-and-forget
        self.cache.store_answer(
            question=question,
            chunk_ids=chunk_ids,
            answer=final_answer,
            citations=[c.model_dump() for c in citations],
            source_ids=list({c.source_id for c in citations}),
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


def _normalize_generated_answer(
    *,
    answer_text: str,
    model_info: dict[str, str],
    citations: list[Citation],
    contexts: list[VectorRecord],
) -> tuple[str, dict[str, str]]:
    cleaned = answer_text.strip()
    if cleaned:
        return cleaned, model_info
    fallback = _extractive_fallback_answer(citations=citations, contexts=contexts)
    if fallback:
        next_info = dict(model_info)
        next_info["fallback_used"] = "extractive"
        return fallback, next_info
    return cleaned, model_info


def _extractive_fallback_answer(
    *,
    citations: list[Citation],
    contexts: list[VectorRecord],
) -> str:
    excerpts = [citation.excerpt.strip() for citation in citations if citation.excerpt and citation.excerpt.strip()]
    if excerpts:
        return " ".join(excerpts[:2]).strip()
    context_text = [context.text.strip() for context in contexts if context.text.strip()]
    if context_text:
        return " ".join(context_text[:1]).strip()[:600]
    return ""


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
    query_terms = _meaningful_terms(question)
    if not query_terms:
        return 0.25 if citations else 0.0
    best_overlap = 0.0
    best_excerpt_overlap = 0.0
    cited_chunk_ids = {citation.chunk_id for citation in citations}
    excerpt_by_chunk = {
        citation.chunk_id: citation.excerpt
        for citation in citations
        if citation.excerpt
    }
    for context in contexts[:6]:
        terms = _meaningful_terms(context.text)
        overlap = len(query_terms.intersection(terms)) / max(len(query_terms), 1)
        excerpt_terms = _meaningful_terms(excerpt_by_chunk.get(context.chunk_id, ""))
        excerpt_overlap = len(query_terms.intersection(excerpt_terms)) / max(len(query_terms), 1)
        if context.chunk_id in cited_chunk_ids:
            overlap = overlap * 1.15
            excerpt_overlap = excerpt_overlap * 1.15
        if overlap > best_overlap:
            best_overlap = overlap
        if excerpt_overlap > best_excerpt_overlap:
            best_excerpt_overlap = excerpt_overlap
    citation_factor = min(len(citations), 3) / 3
    return (best_overlap * 0.55) + (best_excerpt_overlap * 0.2) + (citation_factor * 0.25)


def _meaningful_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for match in re.finditer(r"[a-z0-9]+", text.lower()):
        token = _normalize_token(match.group(0))
        if len(token) > 2 and token not in STOPWORDS:
            terms.add(token)
    return terms


def _normalize_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]
    return token
