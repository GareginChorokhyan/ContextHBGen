from typing import List, Dict, Optional

from domain.entities.document import Document
from infrastructure.config.settings import Settings


class RagService:
    def __init__(
        self,
        embedder,
        vector_store,
        top_k: Optional[int] = None,
        fallback_embedder=None,
        fallback_vector_store=None,
    ):
        self.embedder = embedder
        self.fallback_embedder = fallback_embedder
        self.vector_store = vector_store
        self.fallback_vector_store = fallback_vector_store
        self.top_k = top_k or Settings.RAG_TOP_K

    def index_document(self, document: Document) -> None:
        chunks = document.chunks.get_chunks()
        if not chunks:
            return

        texts = [c.text for c in chunks]
        try:
            embeddings = self.embedder.embed(texts)
        except Exception:
            if not self.fallback_embedder:
                return
            self.embedder = self.fallback_embedder
            embeddings = self.embedder.embed(texts)

        for chunk, embedding in zip(chunks, embeddings):
            metadata = {
                "document_id": document.document_id,
                "document_name": document.metadata.document_name,
                "section": getattr(chunk.metadata, "section", None),
                "page": getattr(chunk.metadata, "page", None),
                "text": chunk.text,
            }
            try:
                self.vector_store.add(chunk.chunk_id, embedding, metadata)
            except Exception:
                if not self.fallback_vector_store:
                    continue
                self.vector_store = self.fallback_vector_store
                self.vector_store.add(chunk.chunk_id, embedding, metadata)

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        try:
            query_embedding = self.embedder.embed([query])[0]
        except Exception:
            if not self.fallback_embedder:
                return []
            self.embedder = self.fallback_embedder
            query_embedding = self.embedder.embed([query])[0]
        try:
            results = self.vector_store.similarity_search(query_embedding, top_k or self.top_k)
        except Exception:
            if not self.fallback_vector_store:
                return []
            self.vector_store = self.fallback_vector_store
            results = self.vector_store.similarity_search(query_embedding, top_k or self.top_k)
        min_score = Settings.RAG_MIN_SCORE
        return [r for r in results if r.get("score", 0.0) >= min_score]
