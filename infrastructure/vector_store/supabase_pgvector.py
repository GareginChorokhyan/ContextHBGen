from supabase import create_client
from infrastructure.config.settings import Settings
from domain.ports.vector_store import VectoreStore


class VectorStore(VectoreStore):
    """
    Supabase pgvector-backed vector store.
    """

    def __init__(self):
        self.client = create_client(Settings.SUPABASE_URL, Settings.SUPABASE_KEY)

    # Legacy helpers
    def insert_vector(self, vector, metadata):
        self.client.table("documents").insert({
            "vector": vector,
            "metadata": metadata
        }).execute()

    def query_vector(self, query_vector, top_k=5):
        return self.client.rpc("match_documents", {"query_vector": query_vector, "top_k": top_k}).execute()

    # Port implementation
    def add(self, vector_id: str, embedding: list[float], metadata: dict):
        payload = {
            "vector": embedding,
            "metadata": metadata,
        }
        # Store id in metadata for portability
        payload["metadata"]["chunk_id"] = vector_id
        self.client.table("documents").insert(payload).execute()

    def similarity_search(self, embedding: list[float], top_k: int) -> list[dict]:
        result = self.client.rpc(
            "match_documents",
            {"query_vector": embedding, "top_k": top_k},
        ).execute()
        data = getattr(result, "data", None) or []
        # Normalize to {metadata, score}
        normalized = []
        for item in data:
            normalized.append({
                "metadata": item.get("metadata", {}),
                "score": item.get("similarity", item.get("score", 0.0)),
            })
        return normalized

    def delete(self, vector_id: str):
        # Best-effort deletion by stored metadata key
        self.client.table("documents").delete().eq("metadata->>chunk_id", vector_id).execute()

    def clear(self):
        # Best-effort clear; consider scoping by document_id in production
        self.client.table("documents").delete().neq("metadata", {}).execute()
