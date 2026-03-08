from __future__ import annotations

from app.retrieval.citation_guard import filter_citations_by_chunk_ids
from schemas.citation import Citation


def test_filter_citations_by_chunk_ids_strips_invalid_ids() -> None:
    citations = [
        Citation(source_id="s1", chunk_id="c1", excerpt="ok"),
        Citation(source_id="s2", chunk_id="c2", excerpt="remove"),
    ]

    filtered = filter_citations_by_chunk_ids(citations=citations, valid_chunk_ids={"c1"})

    assert [item.chunk_id for item in filtered] == ["c1"]
