import uuid
from domain.entities.document import Document
from domain.value_objects.metadata import Metadata
from domain.entities.status import Status
from domain.entities.chunks import Chunks
from domain.entities.validation import Validation
from domain.entities.history import History

class DocumentFactory:
    @staticmethod
    def create(file_name, content, doc_format="PDF", source=None):
        document_id = str(uuid.uuid4())
        source = source if source is not None else file_name
        metadata = Metadata(
            document_id=document_id,
            document_name=file_name,
            doc_format=doc_format,
            source=source,
        )

        status = Status()
        chunks = Chunks()
        validation = Validation()
        history = History()

        return Document(
            document_id=document_id,
            content=content,
            metadata=metadata,
            status=status,
            chunks=chunks,
            validation=validation,
            history=history
        )
