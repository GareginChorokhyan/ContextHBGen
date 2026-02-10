import math
from typing import List, Dict, Any

from domain.ports.vector_store import VectoreStore


class InMemoryVectorStore(VectoreStore):
    """
    Simple in-memory vector store for local testing.
    """

    def __init__(self):
        self._items: List[Dict[str, Any]] = []

    def add(self, vector_id: str, embedding: list[float], metadata: dict):
        self._items.append({
            "id": vector_id,
            "embedding": embedding,
            "metadata": metadata,
        })

    def similarity_search(self, embedding: list[float], top_k: int) -> list[dict]:
        scored = []
        for item in self._items:
            score = _cosine_similarity(embedding, item["embedding"])
            scored.append({
                "metadata": item["metadata"],
                "score": score,
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def delete(self, vector_id: str):
        self._items = [i for i in self._items if i["id"] != vector_id]

    def clear(self):
        self._items = []


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
