"""Repo Supabase de la vinculación Source↔Módulo (ADR-0012). Cliente perezoso."""
from uuid import UUID

from config.settings import settings
from models.domain.source_module_link import SourceModuleLink
from .interface import SourceLinkRepositoryInterface

_COLS = "id,learning_path_id,source_id,module_id,score,origin"


class SupabaseSourceLinkRepository(SourceLinkRepositoryInterface):
    def __init__(self) -> None:
        from supabase import create_client  # lazy

        self._client = create_client(settings.supabase_url, settings.supabase_key)

    async def upsert_links(self, links: list[SourceModuleLink]) -> list[SourceModuleLink]:
        if not links:
            return []
        payload = [{
            "learning_path_id": str(l.learning_path_id),
            "source_id": str(l.source_id),
            "module_id": l.module_id,
            "score": l.score,
            "origin": l.origin,
        } for l in links]
        resp = (
            self._client.table("source_module_links")
            .upsert(payload, on_conflict="source_id,module_id").execute()
        )
        return [_to_domain(row) for row in (resp.data or [])]

    async def list_by_learning_path(self, learning_path_id: UUID) -> list[SourceModuleLink]:
        resp = (
            self._client.table("source_module_links").select(_COLS)
            .eq("learning_path_id", str(learning_path_id)).execute()
        )
        return [_to_domain(row) for row in (resp.data or [])]


def _to_domain(row: dict) -> SourceModuleLink:
    return SourceModuleLink(
        id=row["id"], learning_path_id=row["learning_path_id"],
        source_id=row["source_id"], module_id=row["module_id"],
        score=row.get("score"), origin=row.get("origin", "llm"),
    )
