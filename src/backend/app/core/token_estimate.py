from __future__ import annotations


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    rough = max(len(text) // 4, 1)
    words = len(text.split())
    return max(rough, words)
