from domain.ports.documentLoader import DocumentLoader
from langchain_community.document_loaders import PyPDFLoader

class PdfLoader(DocumentLoader):
    def load(self, path: str) -> str:
        loader = PyPDFLoader(path)
        docs = loader.load()

        return "\n".join(d.page_content for d in docs)

        