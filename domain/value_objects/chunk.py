from domain.value_objects.chunkPosition import ChunkPosition
from domain.value_objects.metadata import Metadata

class Chunk:
    def __init__(self, chunk_id: str, text: str, position: ChunkPosition, metadata: Metadata):
        if not text.strip():
            raise ValueError("Chunk text cannot be empty")
        
        self.chunk_id = chunk_id
        self.text = text
        self.position = position
        self.metadata = metadata