from __future__ import annotations

from pathlib import Path

from app.ingestion.source_registry import ParsedSegment


def parse_text(file_path: Path) -> list[ParsedSegment]:
    text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return []
    return [ParsedSegment(text=text, citation={"source": file_path.name})]
