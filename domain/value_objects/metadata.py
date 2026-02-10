from typing import Optional

class Metadata:
    def __init__(self,document_id, document_name, doc_format="PDF", source="unknown", section:Optional[str] = None, page: Optional[int] = None):
        self.document_id = document_id
        self.document_name = document_name
        self.format = doc_format
        self.source = source
        self.section = section
        self.page = page

    @property
    def format(self):
        return self._format

    @format.setter
    def format(self, value):
        allowed_formats = ["PDF", "DOCX", "TXT"]
        if value not in allowed_formats:
            raise ValueError(f"Unsupported format: {value}")
        self._format = value

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        self._source = value


    @classmethod
    def from_document(cls, document, *, section: Optional[str] = None, page: Optional[int] = None) -> "Metadata":
        return cls(
            document_id=document.id,
            document_name=document.file_name,
            doc_format=document.metadata.format,
            source=document.metadata.source,
            section=section,
            page=page,
        )

    @classmethod
    def from_chunk(cls, document, chunk, *, section: Optional[str] = None) -> "Metadata":
        return cls(
            document_id=document.id,
            document_name=document.file_name,
            doc_format=document.metadata.format,
            source=document.metadata.source,
            section=section,
            page=chunk.position.page,
        )

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "doc_format": getattr(self, "_format", self.format),
            "source": self.source,
            "section": self.section,
            "page": self.page,
        }