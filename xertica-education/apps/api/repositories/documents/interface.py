from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional

from models.domain.document import Document


class DocumentRepositoryInterface(ABC):
    """Persistencia de documentos subidos (Vía 2 · ADR-0008)."""

    @abstractmethod
    async def create(self, document: Document) -> Document:
        ...

    @abstractmethod
    async def get(self, document_id: UUID) -> Optional[Document]:
        ...

    @abstractmethod
    async def list_by_learning_path(self, learning_path_id: UUID) -> list[Document]:
        ...
