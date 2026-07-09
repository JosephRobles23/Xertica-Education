from datetime import datetime, timezone
from uuid import UUID

from config.settings import settings
from models.domain.approved_research_source import ApprovedResearchSource
from .interface import ApprovedResearchSourceRepositoryInterface


class SupabaseApprovedResearchSourceRepository(ApprovedResearchSourceRepositoryInterface):
    def __init__(self) -> None:
        from supabase import create_client

        self._client = create_client(settings.supabase_url, settings.supabase_key)

    async def upsert(self, sources: list[ApprovedResearchSource]) -> list[ApprovedResearchSource]:
        if not sources:
            return []
        updated_at = datetime.now(timezone.utc).isoformat()
        payload = []
        for source in sources:
            row = source.model_dump(
                mode="json",
                exclude_none=True,
                exclude={"id", "created_at", "updated_at"},
            )
            row["updated_at"] = updated_at
            payload.append(row)
        response = (
            self._client.table("approved_research_sources")
            .upsert(payload, on_conflict="route_id,module_id,url")
            .execute()
        )
        return [ApprovedResearchSource(**row) for row in (response.data or [])]

    async def list_by_route(
        self,
        route_id: UUID,
        module_id: str | None = None,
    ) -> list[ApprovedResearchSource]:
        query = self._client.table("approved_research_sources").select("*").eq("route_id", str(route_id))
        if module_id is not None:
            query = query.or_(f"module_id.is.null,module_id.eq.{module_id}")
        response = query.eq("status", "approved").execute()
        return [ApprovedResearchSource(**row) for row in (response.data or [])]
