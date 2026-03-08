from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.models import SourceType


@dataclass(slots=True)
class ParsedSegment:
    text: str
    citation: dict[str, str | int | float | None]


def infer_source_type_from_filename(filename: str) -> SourceType:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return SourceType.PDF
    if suffix == ".txt":
        return SourceType.TEXT
    if suffix == ".md":
        return SourceType.MARKDOWN
    if suffix in {".mp3", ".wav", ".m4a", ".flac"}:
        return SourceType.AUDIO
    return SourceType.TEXT
