from __future__ import annotations

from app.ingestion.chunking.chunk_policy import ChunkPolicy


def chunk_text(text: str, policy: ChunkPolicy) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    total = len(words)
    while start < total:
        end = min(start + policy.chunk_size, total)
        slice_words = words[start:end]
        chunk = " ".join(slice_words).strip()
        if chunk:
            chunks.append(chunk)
        if end == total:
            break
        start = max(end - policy.chunk_overlap, 0)
    return chunks
