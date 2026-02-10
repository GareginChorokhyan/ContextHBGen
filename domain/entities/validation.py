class Validation:
    def is_document_valid(self, document):
        return bool(document.content) and self.is_valid_type(document)

    def is_valid_type(self, document):
        return document.metadata.format in ["PDF", "DOCX", "TXT"]

    def can_be_chunked(self, document):
        return bool(document.content)

    def is_ready_for_rag(self, document):
        return document.chunks.count_chunks() > 0
