from uuid import UUID, uuid4

from models.domain.approved_research_source import ApprovedResearchSource
from .interface import ApprovedResearchSourceRepositoryInterface


class InMemoryApprovedResearchSourceRepository(ApprovedResearchSourceRepositoryInterface):
    def __init__(self) -> None:
        self._rows: dict[tuple[UUID, str | None, str], ApprovedResearchSource] = {}

    async def upsert(self, sources: list[ApprovedResearchSource]) -> list[ApprovedResearchSource]:
        rows = []
        for source in sources:
            key = (source.route_id, source.module_id, source.url)
            existing = self._rows.get(key)
            row = source.model_copy(update={"id": existing.id if existing else source.id or uuid4()})
            self._rows[key] = row
            rows.append(row)
        return rows

    async def list_by_route(
        self,
        route_id: UUID,
        module_id: str | None = None,
    ) -> list[ApprovedResearchSource]:
        return [
            source
            for (saved_route_id, saved_module_id, _), source in self._rows.items()
            if saved_route_id == route_id
            and (module_id is None or saved_module_id in {None, module_id})
        ]
