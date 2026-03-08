from __future__ import annotations

from schemas.citation import Citation


def filter_citations_by_chunk_ids(
    citations: list[Citation],
    valid_chunk_ids: set[str],
) -> list[Citation]:
    return [citation for citation in citations if citation.chunk_id in valid_chunk_ids]
