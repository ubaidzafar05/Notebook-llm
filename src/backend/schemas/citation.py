from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_id: str
    chunk_id: str
    excerpt: str = Field(min_length=1)
    page_number: int | None = None
    start_timestamp: float | None = None
    end_timestamp: float | None = None
    score: float | None = None
    quality_label: str | None = None
