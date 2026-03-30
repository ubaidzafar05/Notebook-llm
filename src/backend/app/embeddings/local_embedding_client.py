from __future__ import annotations

import hashlib
import math


def _token_to_index(token: str, dimension: int) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % dimension


def embed_text_locally(text: str, dimension: int = 768) -> list[float]:
    vector = [0.0] * dimension
    tokens = [token for token in text.lower().split() if token]
    for token in tokens:
        idx = _token_to_index(token, dimension)
        vector[idx] += 1.0

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
