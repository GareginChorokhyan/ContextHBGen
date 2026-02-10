from typing import List, Optional
from domain.services.chunkingStrategy import ChunkingStrategy


class ChunkingService: 
    def __init__(self, strategy: ChunkingStrategy):
        self.strategy = strategy

    def chunk_document_by_chapters(self, document, chapters: List) -> List:
        if hasattr(self.strategy, 'chunk_by_chapters'):
            all_chunks, updated_chapters = self.strategy.chunk_by_chapters(document, chapters)
        else:
            all_chunks = []
            chunk_counter = 1
            
            for chapter in chapters:
                class ChapterContent:
                    pass
                temp_doc = ChapterContent()
                temp_doc.document_id = document.document_id
                temp_doc.content = chapter.content
                temp_doc.metadata = document.metadata
                
                chapter_chunks = self.strategy.chunk(temp_doc)
                
                for chunk in chapter_chunks:
                    old_id = chunk.chunk_id
                    chunk.chunk_id = f"{document.document_id}_{chunk_counter}"
                    chunk.position.order = chunk_counter
                    if hasattr(chunk.metadata, 'section'):
                        chunk.metadata.section = chapter.get_chapter_name()
                    chunk_counter += 1
                
                chapter.chunk_ids = [c.chunk_id for c in chapter_chunks]
                all_chunks.extend(chapter_chunks)
            
            updated_chapters = chapters
        
        for chunk in all_chunks:
            document.chunks.add_chunk(chunk)
        
        return updated_chapters

    def chunk_document(self, document):
        chunks = self.strategy.chunk(document)
        for c in chunks:
            document.chunks.add_chunk(c)
        return chunks
