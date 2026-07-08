from abc import ABC, abstractmethod
from uuid import UUID

from models.domain.source import Source


class SourcingRepositoryInterface(ABC):
    """Persistencia de fuentes route-céntricas (ADR-0007)."""

    @abstractmethod
    async def upsert_sources(self, sources: list[Source]) -> list[Source]:
        """UPSERT idempotente por (learning_path_id, url). Refresca metadata pero
        preserva `estado` y `verificada_google` en conflicto. Devuelve las filas con id."""
        ...

    @abstractmethod
    async def list_by_learning_path(self, learning_path_id: UUID) -> list[Source]:
        ...
