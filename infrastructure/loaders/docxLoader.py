from docx import Document
from domain.ports.documentLoader import DocumentLoader

class DocxLoader(DocumentLoader):
    def load(self, path: str) -> str:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
