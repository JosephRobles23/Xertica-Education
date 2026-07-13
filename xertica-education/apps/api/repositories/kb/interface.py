from abc import ABC, abstractmethod
from uuid import UUID

from models.domain.kb import Chunk


class KbChunkRepositoryInterface(ABC):
    """Persistencia de chunks + búsqueda por similitud (ADR-0006 §4)."""

    @abstractmethod
    async def upsert_chunks(self, chunks: list[Chunk]) -> None:
        ...

    @abstractmethod
    async def clear_by_learning_path(self, learning_path_id: UUID) -> None:
        """Borra todos los chunks de una ruta (clear-and-reingest · ADR-0006)."""
        ...

    @abstractmethod
    async def similarity_search(
        self,
        learning_path_id: UUID,
        embedding: list[float],
        k: int,
        verified_only: bool,
    ) -> list[tuple[Chunk, float]]:
        """Top-k por coseno, filtrado por ruta. Devuelve (chunk, score) desc."""
        ...
