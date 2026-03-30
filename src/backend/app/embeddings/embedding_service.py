from __future__ import annotations

import logging
import time

import requests

from app.core.config import get_settings
from app.embeddings.local_embedding_client import embed_text_locally

logger = logging.getLogger(__name__)

_EMBED_RETRY_ATTEMPTS = 2
_EMBED_RETRY_BACKOFF_SECONDS = 2.0


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        last_error: Exception | None = None
        for attempt in range(_EMBED_RETRY_ATTEMPTS):
            try:
                return [self._embed_with_ollama(text=text) for text in texts]
            except requests.RequestException as exc:
                last_error = exc
                if attempt < _EMBED_RETRY_ATTEMPTS - 1:
                    logger.warning(
                        "Embedding attempt %d/%d failed, retrying in %.1fs: %s",
                        attempt + 1,
                        _EMBED_RETRY_ATTEMPTS,
                        _EMBED_RETRY_BACKOFF_SECONDS,
                        exc,
                    )
                    time.sleep(_EMBED_RETRY_BACKOFF_SECONDS)

        logger.warning("All %d embedding attempts failed; using local hashing fallback: %s", _EMBED_RETRY_ATTEMPTS, last_error)
        return [embed_text_locally(text) for text in texts]

    def _embed_with_ollama(self, text: str) -> list[float]:
        payload = {"model": self.settings.ollama_embed_model, "prompt": text}
        response = requests.post(
            f"{self.settings.ollama_base_url}/api/embeddings",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        embedding = body.get("embedding")
        if not isinstance(embedding, list):
            raise requests.RequestException("Embedding payload missing")
        return [float(value) for value in embedding]
