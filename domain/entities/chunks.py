from domain.value_objects.chunk import Chunk

class Chunks:
    def __init__(self):
        self._chunks: list[Chunk] = []

    def add_chunk(self, chunk: Chunk):
        if not chunk.text.strip():
            raise ValueError("Chunk text cannot be empty")
        if any(c.chunk_id == chunk.chunk_id for c in self._chunks):
            raise ValueError(f"Chunk with id {chunk.chunk_id} already exists")
        self._chunks.append(chunk)


    def remove_chunk(self, chunk_id):
        self._chunks = [c for c in self._chunks if getattr(c, "chunk_id", None) != chunk_id]

    def get_chunks(self) -> list[Chunk]:
        return self._chunks

    def count_chunks(self) -> int:
        return len(self._chunks)
