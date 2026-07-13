"""Fallback in-memory del repositorio de chunks (ADR-0004: mismo patrón que el resto).

Coseno en Python; como los embeddings vienen normalizados, el producto punto ya
es el coseno. Suficiente para el MVP y para los tests sin Supabase.
"""
from uuid import UUID

from models.domain.kb import Chunk
from .interface import KbChunkRepositoryInterface


class InMemoryKbChunkRepository(KbChunkRepositoryInterface):
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []

    async def upsert_chunks(self, chunks: list[Chunk]) -> None:
        self._chunks.extend(chunks)

    async def clear_by_learning_path(self, learning_path_id: UUID) -> None:
        self._chunks = [c for c in self._chunks if c.learning_path_id != learning_path_id]

    async def similarity_search(
        self,
        learning_path_id: UUID,
        embedding: list[float],
        k: int,
        verified_only: bool,
    ) -> list[tuple[Chunk, float]]:
        candidates = [
            c for c in self._chunks
            if c.learning_path_id == learning_path_id
            and c.embedding is not None
            and (not verified_only or bool(c.metadata.get("verificada_google")))
        ]
        scored = [(c, _dot(embedding, c.embedding)) for c in candidates]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
