"""Fallback in-memory del repo de sourcing (ADR-0004: mismo patrón que el resto)."""
from uuid import UUID, uuid4

from models.domain.source import Source
from .interface import SourcingRepositoryInterface


class InMemorySourcingRepository(SourcingRepositoryInterface):
    def __init__(self) -> None:
        self._rows: dict[tuple, Source] = {}  # (learning_path_id, url) -> Source

    async def upsert_sources(self, sources: list[Source]) -> list[Source]:
        result: list[Source] = []
        for src in sources:
            # dedup por url (Vía 1) o por document_id (Vía 2, sin url)
            key = (src.learning_path_id, src.url or f"doc:{src.document_id}")
            existing = self._rows.get(key)
            if existing is not None:
                # refresca metadata; PRESERVA estado + verificada_google (decisión #4)
                existing.title = src.title
                existing.tipo = src.tipo
                result.append(existing)
            else:
                row = src.model_copy(update={"id": uuid4()})
                self._rows[key] = row
                result.append(row)
        return result

    async def list_by_learning_path(self, learning_path_id: UUID) -> list[Source]:
        return [s for (lp, _), s in self._rows.items() if lp == learning_path_id]
