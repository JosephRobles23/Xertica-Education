"""Fallback in-memory del repo de vinculación Source↔Módulo (ADR-0004: mismo patrón)."""
from uuid import UUID, uuid4

from models.domain.source_module_link import SourceModuleLink
from .interface import SourceLinkRepositoryInterface


class InMemorySourceLinkRepository(SourceLinkRepositoryInterface):
    def __init__(self) -> None:
        self._rows: dict[tuple, SourceModuleLink] = {}  # (source_id, module_id) -> link

    async def upsert_links(self, links: list[SourceModuleLink]) -> list[SourceModuleLink]:
        result: list[SourceModuleLink] = []
        for link in links:
            key = (link.source_id, link.module_id)
            existing = self._rows.get(key)
            if existing is not None:
                existing.score = link.score
                existing.origin = link.origin
                result.append(existing)
            else:
                row = link.model_copy(update={"id": link.id or uuid4()})
                self._rows[key] = row
                result.append(row)
        return result

    async def list_by_learning_path(self, learning_path_id: UUID) -> list[SourceModuleLink]:
        return [l for l in self._rows.values() if l.learning_path_id == learning_path_id]
