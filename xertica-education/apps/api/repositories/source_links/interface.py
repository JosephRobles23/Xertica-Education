from abc import ABC, abstractmethod
from uuid import UUID

from models.domain.source_module_link import SourceModuleLink


class SourceLinkRepositoryInterface(ABC):
    """Persistencia de la vinculación Source↔Módulo (ADR-0012)."""

    @abstractmethod
    async def upsert_links(self, links: list[SourceModuleLink]) -> list[SourceModuleLink]:
        """UPSERT idempotente por (source_id, module_id). Devuelve las filas con id."""
        ...

    @abstractmethod
    async def list_by_learning_path(self, learning_path_id: UUID) -> list[SourceModuleLink]:
        ...
