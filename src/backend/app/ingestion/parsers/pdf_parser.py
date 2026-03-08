from __future__ import annotations

from pathlib import Path

import fitz

from app.core.exceptions import AppError
from app.ingestion.source_registry import ParsedSegment


def parse_pdf(file_path: Path) -> list[ParsedSegment]:
    segments: list[ParsedSegment] = []
    try:
        doc = fitz.open(file_path)
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            code="PDF_OPEN_FAILED",
            message=f"Failed to open or parse PDF: {file_path.name}",
            status_code=400,
            details={"failure_stage": "parse"},
        ) from exc

    try:
        with doc:
            for page_index, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                if not text:
                    continue
                citation: dict[str, str | int | float | None] = {
                    "page_number": page_index,
                    "source": file_path.name,
                }
                segments.append(ParsedSegment(text=text, citation=citation))
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            code="PDF_PARSE_FAILED",
            message=f"Failed to parse PDF content: {file_path.name}",
            status_code=400,
            details={"failure_stage": "parse"},
        ) from exc
    if not segments:
        raise AppError(
            code="PDF_EMPTY",
            message="PDF contains no extractable text",
            status_code=400,
            details={"failure_stage": "parse"},
        )
    return segments
