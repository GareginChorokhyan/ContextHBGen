import hashlib
from typing import List


class LocalHashEmbedder:
    def __init__(self, dim: int = 128):
        self.dim = dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        tokens = text.split()
        if not tokens:
            return vec
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = digest[0] % self.dim
            vec[idx] += 1.0
        # Normalize
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec
