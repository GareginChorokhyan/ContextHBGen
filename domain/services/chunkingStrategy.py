from abc import ABC, abstractmethod
from domain.entities.document import Document
from domain.value_objects.chunk import Chunk

class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        pass
