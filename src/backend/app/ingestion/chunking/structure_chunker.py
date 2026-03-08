from __future__ import annotations

from app.ingestion.chunking.chunk_policy import ChunkPolicy


def chunk_markdown_sections(text: str, policy: ChunkPolicy) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("#") and current:
            sections.extend(_split_with_policy("\n".join(current), policy))
            current = [line]
            continue
        current.append(line)
    if current:
        sections.extend(_split_with_policy("\n".join(current), policy))
    return [section for section in sections if section.strip()]


def _split_with_policy(text: str, policy: ChunkPolicy) -> list[str]:
    words = text.split()
    if not words:
        return []
    result: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + policy.chunk_size, len(words))
        result.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(end - policy.chunk_overlap, 0)
    return result
