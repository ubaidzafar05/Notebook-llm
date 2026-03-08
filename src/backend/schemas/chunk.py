from __future__ import annotations

from pydantic import BaseModel


class ChunkOut(BaseModel):
    id: str
    source_id: str
    chunk_index: int
    text: str
    token_count: int
    citation: dict[str, str | int | float | None]
