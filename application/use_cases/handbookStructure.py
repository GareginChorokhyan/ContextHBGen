from typing import List, Union
from domain.entities.document import Document
from application.dto.handbookResult import HandbookResult

class HandbookStructure:
    def __init__(self, max_total_words=20000):
        self.max_total_words = max_total_words

    def build_for_document(self, document: Document) -> HandbookResult:
        return self._build([document])

    def build_for_documents(self, documents: List[Document]) -> HandbookResult:
        return self._build(documents)

    def _build(self, documents: list[Document]):
        handbook = []
        section_number = 1
        total_words = 0

        for doc in documents:
            outline = getattr(doc, "outline", [])
            chunks_dict = {
                c.chunk_id: c
                for c in doc.chunks.get_chunks()
                if c.metadata.document_id == doc.id
            }

            for chapter in outline:
                section_chunks = chapter["chunks"]
                section_word_count = sum(len(chunks_dict[cid].text.split()) for cid in section_chunks if cid in chunks_dict)

                if total_words + section_word_count > self.max_total_words:
                    break

                handbook.append({
                    "section": f"Section {section_number}: {chapter['chapter']}",
                    "chunks": section_chunks
                })
                section_number += 1
                total_words += section_word_count

            if total_words >= self.max_total_words:
                break

        return HandbookResult.from_handbook_structure(handbook)