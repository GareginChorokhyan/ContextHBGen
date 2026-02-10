class Document:
    def __init__(self, document_id, content=None,
                 metadata=None, status=None,
                 chunks=None, validation=None,
                 history=None):
        self.document_id = document_id
        self.content = content

        self.metadata = metadata
        self.status = status
        self.chunks = chunks
        self.validation = validation
        self.history = history
        self.outline = []

    @property
    def id(self):
        return self.document_id

    @property
    def file_name(self):
        return self.metadata.document_name if self.metadata else None