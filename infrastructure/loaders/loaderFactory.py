from domain.ports.documentLoader import DocumentLoader
from infrastructure.loaders.pdfLoader import PdfLoader
from infrastructure.loaders.docxLoader import DocxLoader
from infrastructure.loaders.txtLoader import TxtLoader

class LoaderFactory:
    @staticmethod
    def create(path: str) -> DocumentLoader:
        if path.endswith(".pdf"):
            return PdfLoader()
        if path.endswith(".docx"):
            return DocxLoader()
        if path.endswith(".txt"):
            return TxtLoader()
        raise ValueError("Unsupported format")