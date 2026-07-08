from uuid import UUID, uuid4
from typing import Optional

from models.domain.document import Document
from .interface import DocumentRepositoryInterface


class InMemoryDocumentRepository(DocumentRepositoryInterface):
    def __init__(self) -> None:
        self._docs: dict[UUID, Document] = {}

    async def create(self, document: Document) -> Document:
        doc = document.model_copy(update={"id": document.id or uuid4()})
        self._docs[doc.id] = doc
        return doc

    async def get(self, document_id: UUID) -> Optional[Document]:
        return self._docs.get(document_id)

    async def list_by_learning_path(self, learning_path_id: UUID) -> list[Document]:
        return [d for d in self._docs.values() if d.learning_path_id == learning_path_id]
