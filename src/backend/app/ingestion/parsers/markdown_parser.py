from __future__ import annotations

from pathlib import Path

from app.ingestion.source_registry import ParsedSegment


def parse_markdown(file_path: Path) -> list[ParsedSegment]:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    segments: list[ParsedSegment] = []
    current_heading = "root"
    buffer: list[str] = []

    for line in content.splitlines():
        if line.startswith("#"):
            if buffer:
                text = "\n".join(buffer).strip()
                if text:
                    segments.append(
                        ParsedSegment(text=text, citation={"source": file_path.name, "section": current_heading})
                    )
                buffer = []
            current_heading = line.lstrip("#").strip() or "untitled"
            continue
        buffer.append(line)

    if buffer:
        text = "\n".join(buffer).strip()
        if text:
            segments.append(
                ParsedSegment(text=text, citation={"source": file_path.name, "section": current_heading})
            )
    return segments
