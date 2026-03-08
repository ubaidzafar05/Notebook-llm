from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ChunkPolicy:
    chunk_size: int
    chunk_overlap: int


def default_policy() -> ChunkPolicy:
    return ChunkPolicy(chunk_size=300, chunk_overlap=60)


def markdown_policy() -> ChunkPolicy:
    return ChunkPolicy(chunk_size=220, chunk_overlap=40)
