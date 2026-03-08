from __future__ import annotations

from pydantic import BaseModel


class MemorySummaryOut(BaseModel):
    session_id: str
    summary: str
    provider: str
