from domain.ports.documentLoader import DocumentLoader

class TxtLoader(DocumentLoader):
    def load(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

