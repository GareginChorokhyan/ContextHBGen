import re
from typing import List, Optional, Tuple
from domain.services.chunkingStrategy import ChunkingStrategy
from domain.value_objects.chunk import Chunk
from domain.value_objects.chunkPosition import ChunkPosition
from domain.value_objects.metadata import Metadata


# Patterns for artifacts that should be removed from content
PAGE_ARTIFACT_PATTERNS = [
    r'^\s*\d+\s*$',                      # Standalone page numbers
    r'^\s*-\s*\d+\s*-\s*$',              # "- 42 -" style page numbers
    r'^\s*–\s*\d+\s*–\s*$',              # "– 42 –" en-dash style
    r'^\s*page\s+\d+\s*$',               # "Page 42"
    r'^\s*p\.\s*\d+\s*$',                # "p. 42"
    r'^\s*\d+\s+of\s+\d+\s*$',           # "42 of 100"
    r'^\s*\[\s*\d+\s*\]\s*$',            # "[42]"
]

_COMPILED_PAGE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in PAGE_ARTIFACT_PATTERNS]


def _chunk_metadata(document, position, section: Optional[str] = None, page: Optional[int] = None):
    return Metadata(
        document_id=document.document_id,
        document_name=document.metadata.document_name,
        doc_format=document.metadata.format,
        source=document.metadata.source,
        section=section, 
        page=page or getattr(position, "page", None),
    )


class ParagraphChunking(ChunkingStrategy):
    def __init__(self, min_words: int = 200, max_words: int = 500):
        self.min_words = min_words
        self.max_words = max_words

    def _normalize_content(self, content: str) -> str:
        if not content:
            return content
        
        lines = content.split('\n')
        filtered_lines = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                filtered_lines.append('')
                continue
            
            is_artifact = False
            for pattern in _COMPILED_PAGE_PATTERNS:
                if pattern.match(stripped):
                    is_artifact = True
                    break
            
            if not is_artifact:
                filtered_lines.append(line)
        
        content = '\n'.join(filtered_lines)
        
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        content = content.strip()
        
        return content
    
    def _is_valid_chunk_text(self, text: str) -> bool:
        if not text:
            return False
        
        stripped = text.strip()
        if not stripped:
            return False
        
        words = stripped.split()
        if len(words) < 1:
            return False
        
        return True

    def chunk_by_chapters(self, document, chapters: List) -> Tuple[List[Chunk], List]:
        all_chunks: List[Chunk] = []
        chunk_counter = 1
        
        for chapter in chapters:
            chapter_name = chapter.get_chapter_name()
            chapter_page = chapter.page
            
            chapter_chunks, chunk_counter = self._chunk_chapter_content(
                document=document,
                content=chapter.content,
                chapter_name=chapter_name,
                chapter_page=chapter_page,
                start_chunk_id=chunk_counter
            )
            
            chapter.chunk_ids = [c.chunk_id for c in chapter_chunks]
            
            all_chunks.extend(chapter_chunks)
        
        return all_chunks, chapters

    def _chunk_chapter_content(
        self,
        document,
        content: str,
        chapter_name: str,
        chapter_page: Optional[int],
        start_chunk_id: int
    ) -> Tuple[List[Chunk], int]:
      
        chunks: List[Chunk] = []
        chunk_counter = start_chunk_id
        
        normalized_content = self._normalize_content(content)
        
        
        paragraphs = [p.strip() for p in normalized_content.split("\n\n") if p.strip()]
        
       
        current_text = ""
        
        for para in paragraphs:
            words = para.split()
            
            while len(words) > self.max_words:
                sub_text = " ".join(words[:self.max_words])
                
                pos = ChunkPosition(order=chunk_counter, page=chapter_page)
                meta = _chunk_metadata(document, pos, section=chapter_name, page=chapter_page)
                
                chunk = Chunk(
                    chunk_id=f"{document.document_id}_{chunk_counter}",
                    text=sub_text,
                    position=pos,
                    metadata=meta,
                )
                chunks.append(chunk)
                chunk_counter += 1
                words = words[self.max_words:]
            
            if len(words) < self.min_words:
                if current_text:
                    current_text += " " + " ".join(words)
                else:
                    current_text = " ".join(words)
                
                if len(current_text.split()) >= self.max_words:
                    pos = ChunkPosition(order=chunk_counter, page=chapter_page)
                    meta = _chunk_metadata(document, pos, section=chapter_name, page=chapter_page)
                    
                    chunk = Chunk(
                        chunk_id=f"{document.document_id}_{chunk_counter}",
                        text=current_text,
                        position=pos,
                        metadata=meta,
                    )
                    chunks.append(chunk)
                    chunk_counter += 1
                    current_text = ""
            else:
                if current_text:
                    para = current_text + " " + " ".join(words)
                    current_text = ""
                else:
                    para = " ".join(words)
                
                pos = ChunkPosition(order=chunk_counter, page=chapter_page)
                meta = _chunk_metadata(document, pos, section=chapter_name, page=chapter_page)
                
                chunk = Chunk(
                    chunk_id=f"{document.document_id}_{chunk_counter}",
                    text=para,
                    position=pos,
                    metadata=meta,
                )
                chunks.append(chunk)
                chunk_counter += 1
        
        if current_text and self._is_valid_chunk_text(current_text):
            pos = ChunkPosition(order=chunk_counter, page=chapter_page)
            meta = _chunk_metadata(document, pos, section=chapter_name, page=chapter_page)
            
            chunk = Chunk(
                chunk_id=f"{document.document_id}_{chunk_counter}",
                text=current_text.strip(),
                position=pos,
                metadata=meta,
            )
            chunks.append(chunk)
            chunk_counter += 1
        
        return chunks, chunk_counter

    def chunk(self, document) -> List[Chunk]:
        chunks, _ = self._chunk_chapter_content(
            document=document,
            content=document.content,
            chapter_name=None,  
            chapter_page=None,
            start_chunk_id=1
        )
        return chunks
