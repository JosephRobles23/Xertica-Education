"""Repositorio Supabase de chunks (ADR-0006 §4).

upsert vía insert; búsqueda vía la función SQL `match_kb_chunks` (coseno con HNSW).
Cliente perezoso; se usa solo cuando hay credenciales reales (ver factory).
"""
from uuid import UUID

from config.settings import settings
from models.domain.kb import Chunk
from .interface import KbChunkRepositoryInterface


class SupabaseKbChunkRepository(KbChunkRepositoryInterface):
    def __init__(self) -> None:
        from supabase import create_client  # lazy: solo con credenciales reales

        self._client = create_client(settings.supabase_url, settings.supabase_key)

    async def upsert_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        rows = [{
            "source_id": str(c.source_id),
            "learning_path_id": str(c.learning_path_id),
            "content": c.content,
            "embedding": c.embedding,
            "metadata": c.metadata,
            "token_count": c.token_count,
        } for c in chunks]
        self._client.table("kb_chunks").insert(rows).execute()

    async def similarity_search(
        self,
        learning_path_id: UUID,
        embedding: list[float],
        k: int,
        verified_only: bool,
    ) -> list[tuple[Chunk, float]]:
        resp = self._client.rpc("match_kb_chunks", {
            "query_embedding": embedding,
            "p_learning_path_id": str(learning_path_id),
            "match_count": k,
            "verified_only": verified_only,
        }).execute()
        results: list[tuple[Chunk, float]] = []
        for row in (resp.data or []):
            chunk = Chunk(
                id=row["id"],
                source_id=row["source_id"],
                learning_path_id=learning_path_id,
                content=row["content"],
                metadata=row.get("metadata") or {},
            )
            results.append((chunk, float(row["score"])))
        return results
