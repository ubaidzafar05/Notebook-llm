from __future__ import annotations

from schemas.citation import Citation

from app.db.models import Chunk
from app.vector_store.collections import VectorRecord


def build_citations(records: list[VectorRecord], chunk_lookup: dict[str, Chunk]) -> list[Citation]:
    citations: list[Citation] = []
    for record in records:
        chunk = chunk_lookup.get(record.chunk_id)
        if chunk is None:
            continue
        citation_data = chunk.citation_json
        citations.append(
            Citation(
                source_id=chunk.source_id,
                chunk_id=chunk.id,
                excerpt=chunk.text[:280],
                page_number=_as_int(citation_data.get("page_number")),
                start_timestamp=_as_float(citation_data.get("start_timestamp")),
                end_timestamp=_as_float(citation_data.get("end_timestamp")),
            )
        )
    return citations


def _as_int(value: object) -> int | None:
    return int(value) if isinstance(value, int) else None


def _as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None
