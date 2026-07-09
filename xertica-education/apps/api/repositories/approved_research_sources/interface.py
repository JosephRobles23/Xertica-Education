from abc import ABC, abstractmethod
from uuid import UUID

from models.domain.approved_research_source import ApprovedResearchSource


class ApprovedResearchSourceRepositoryInterface(ABC):
    @abstractmethod
    async def upsert(self, sources: list[ApprovedResearchSource]) -> list[ApprovedResearchSource]:
        ...

    @abstractmethod
    async def list_by_route(
        self,
        route_id: UUID,
        module_id: str | None = None,
    ) -> list[ApprovedResearchSource]:
        ...
