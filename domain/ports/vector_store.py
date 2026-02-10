from abc import ABC, abstractmethod

class VectoreStore(ABC):
    @abstractmethod
    def add(self, vector_id: str, embedding: list[float], metadata: dict):
        pass

    @abstractmethod
    def similarity_search(self, embedding: list[float], top_k: int) -> list[dict]:
        pass

    @abstractmethod
    def delete(self, vector_id: str):
        pass

    @abstractmethod
    def clear(self):
        pass