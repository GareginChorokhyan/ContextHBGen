from domain.ports.documentLoader import DocumentLoader
from infrastructure.loaders.loaderFactory import LoaderFactory


class PathBasedLoader(DocumentLoader):
    def load(self, path: str) -> str:
        loader = LoaderFactory.create(path)
        return loader.load(path)
