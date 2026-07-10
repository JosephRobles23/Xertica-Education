"""Repo Supabase de sourcing (ADR-0007). UPSERT que preserva estado humano.

Como Supabase/PostgREST no permite un UPSERT parcial (sobre-escribe todas las columnas),
separamos: las urls existentes se ACTUALIZAN solo en metadata (title, tipo); las nuevas
se INSERTAN con estado/verificada del payload. Cliente perezoso (solo con credenciales).
"""
from uuid import UUID

from config.settings import settings
from models.domain.source import Source
from .interface import SourcingRepositoryInterface


class SupabaseSourcingRepository(SourcingRepositoryInterface):
    def __init__(self) -> None:
        from supabase import create_client  # lazy: solo con credenciales reales

        self._client = create_client(settings.supabase_url, settings.supabase_key)

    async def upsert_sources(self, sources: list[Source]) -> list[Source]:
        if not sources:
            return []
        lp = sources[0].learning_path_id
        url_sources = [s for s in sources if s.url]
        document_sources = [s for s in sources if s.document_id]

        by_url = {}
        if url_sources:
            existing = (
                self._client.table("sources")
                .select("id,url,estado,verificada_google,origin,document_id")
                .eq("learning_path_id", str(lp))
                .in_("url", [s.url for s in url_sources])
                .execute()
            )
            by_url = {row["url"]: row for row in (existing.data or [])}

        by_document_id = {}
        if document_sources:
            existing_docs = (
                self._client.table("sources")
                .select("id,url,estado,verificada_google,origin,document_id")
                .eq("learning_path_id", str(lp))
                .in_("document_id", [str(s.document_id) for s in document_sources])
                .execute()
            )
            by_document_id = {row["document_id"]: row for row in (existing_docs.data or [])}

        result: list[Source] = []
        to_insert: list[dict] = []
        for src in sources:
            row = by_url.get(src.url) if src.url else by_document_id.get(str(src.document_id))
            if row is not None:
                # refresca metadata; preserva estado + verificada_google
                self._client.table("sources").update(
                    {"title": src.title, "tipo": src.tipo}
                ).eq("id", row["id"]).execute()
                result.append(Source(
                    id=row["id"], learning_path_id=lp, url=src.url, title=src.title,
                    tipo=src.tipo, estado=row.get("estado"),
                    verificada_google=bool(row.get("verificada_google")),
                    origin=row.get("origin", src.origin),
                    document_id=row.get("document_id") or src.document_id,
                ))
            else:
                to_insert.append({
                    "learning_path_id": str(lp), "url": src.url, "title": src.title,
                    "tipo": src.tipo, "estado": src.estado,
                    "verificada_google": src.verificada_google,
                    "origin": src.origin,
                    "document_id": str(src.document_id) if src.document_id else None,
                })

        if to_insert:
            inserted = self._client.table("sources").insert(to_insert).execute()
            for row in (inserted.data or []):
                result.append(Source(
                    id=row["id"], learning_path_id=lp, url=row["url"], title=row.get("title"),
                    tipo=row.get("tipo"), estado=row.get("estado"),
                    verificada_google=bool(row.get("verificada_google")),
                    origin=row.get("origin", "deep_research"),
                    document_id=row.get("document_id"),
                ))
        return result

    async def list_by_learning_path(self, learning_path_id: UUID) -> list[Source]:
        resp = (
            self._client.table("sources")
            .select("*")
            .eq("learning_path_id", str(learning_path_id))
            .execute()
        )
        return [Source(**row) for row in (resp.data or [])]
