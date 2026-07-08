from abc import ABC, abstractmethod
from uuid import UUID

from models.domain.kb import GroundedChunk, IngestReport
from models.domain.source import Source


class KnowledgeBaseInterface(ABC):
    """Puerto `KnowledgeBase` (ADR-0006 §6). Consumido por los generadores de contenido."""

    @abstractmethod
    async def ingest(
        self,
        learning_path_id: UUID,
        sources: list[Source],
        documents: dict[UUID, str],
    ) -> IngestReport:
        """Trocea, embebe e indexa los `documents` (source_id → Markdown) de la ruta."""
        ...

    @abstractmethod
    async def query(
        self,
        learning_path_id: UUID,
        text: str,
        k: int = 8,
        verified_only: bool = False,
    ) -> list[GroundedChunk]:
        """Búsqueda semántica grounded con citas, aislada por `learning_path_id`."""
        ...
