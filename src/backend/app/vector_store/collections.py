from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VectorRecord:
    chunk_id: str
    source_id: str
    user_id: str
    text: str
    vector: list[float]
    metadata: dict[str, str | int | float | None]
    notebook_id: str = ""
