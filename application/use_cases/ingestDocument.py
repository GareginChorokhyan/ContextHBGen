from typing import List, Union
from domain.entities.document import Document
from domain.entities.documentFactory import DocumentFactory
from domain.services.chunkingService import ChunkingService
from domain.services.outlineService import OutlineService
from domain.ports.documentLoader import DocumentLoader


def _format_from_path(path: str) -> str:
    path_lower = path.lower()
    if path_lower.endswith(".pdf"):
        return "PDF"
    if path_lower.endswith(".docx"):
        return "DOCX"
    if path_lower.endswith(".txt"):
        return "TXT"
    return "PDF"


class IngestDocument:
    def __init__(
        self,
        document_loader: DocumentLoader,
        chunking_service: ChunkingService,
        outline_service: OutlineService,
        rag_service=None,
        lightrag_service=None,
    ):
        self.document_loader = document_loader
        self.chunking_service = chunking_service
        self.outline_service = outline_service
        self.rag_service = rag_service
        self.lightrag_service = lightrag_service

    def execute(
        self,
        files: Union[str, List[str]],
        doc_names: Union[str, List[str]],
        doc_format=None,
        use_chapter_aware_chunking: bool = True
    ) -> List[Document]:
    
        if isinstance(files, str):
            files = [files]
        if isinstance(doc_names, str):
            doc_names = [doc_names]

        documents: List[Document] = []

        for file_path, file_name in zip(files, doc_names):
            text = self.document_loader.load(file_path)
            fmt = doc_format or _format_from_path(file_path)
            
            document = DocumentFactory.create(
                file_name=file_name,
                content=text,
                doc_format=fmt,
                source=file_path,
            )
            
            if use_chapter_aware_chunking:
                chapters = self.outline_service.extract_chapters(document)

                updated_chapters = self.chunking_service.chunk_document_by_chapters(
                    document, chapters
                )
                outline = self.outline_service.generate_outline(
                    document, updated_chapters
                )
            else:
                self.chunking_service.chunk_document(document)
                outline = self.outline_service.generate_outline(document)
            
            document.outline = outline
            if self.rag_service:
                self.rag_service.index_document(document)
            documents.append(document)

        return documents