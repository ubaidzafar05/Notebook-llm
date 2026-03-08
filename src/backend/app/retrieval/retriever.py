from __future__ import annotations

from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.collections import VectorRecord
from app.vector_store.milvus_client import VectorStoreClient


class Retriever:
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStoreClient) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(self, user_id: str, notebook_id: str, query: str, top_k: int = 8, buffer: int = 4) -> list[VectorRecord]:
        query_vector = self.embedding_service.embed_texts([query])[0]
        return self.vector_store.search(
            user_id=user_id,
            notebook_id=notebook_id,
            query_vector=query_vector,
            top_k=top_k + buffer,
        )
