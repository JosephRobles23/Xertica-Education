"""KBService: implementación real del puerto KnowledgeBase (ADR-0006).

Orquesta chunking → embedding → upsert (ingest) y embedding → similitud → cita
(query). El proveedor de embeddings y el store son inyectados (mock ↔ real).
"""
from uuid import UUID

from adapters.embeddings.base import BaseEmbedder
from models.domain.kb import Chunk, Citation, GroundedChunk, IngestReport
from models.domain.source import Source
from repositories.kb.interface import KbChunkRepositoryInterface
from .chunking import chunk_markdown, estimate_tokens
from .interface import KnowledgeBaseInterface

_SNIPPET_LEN = 200


class KBService(KnowledgeBaseInterface):
    def __init__(self, embedder: BaseEmbedder, repository: KbChunkRepositoryInterface):
        self._embedder = embedder
        self._repo = repository

    async def ingest(
        self,
        learning_path_id: UUID,
        sources: list[Source],
        documents: dict[UUID, str],
    ) -> IngestReport:
        source_by_id = {s.id: s for s in sources}
        chunks: list[Chunk] = []
        skipped: list[str] = []
        for source_id, markdown in documents.items():
            src = source_by_id.get(source_id)
            # Documento sin texto extraíble (p.ej. PDF escaneado): no aporta chunks.
            if not (markdown and markdown.strip()):
                skipped.append((src.title if src else None) or str(source_id))
                continue
            for text in chunk_markdown(markdown):
                chunks.append(Chunk(
                    source_id=source_id,
                    learning_path_id=learning_path_id,
                    content=text,
                    token_count=estimate_tokens(text),
                    metadata={
                        "title": src.title if src else None,
                        "url": src.url if src else None,
                        "verificada_google": bool(src.verificada_google) if src else False,
                    },
                ))

        if chunks:
            vectors = await self._embedder.embed([c.content for c in chunks])
            for chunk, vector in zip(chunks, vectors):
                chunk.embedding = vector
            await self._repo.upsert_chunks(chunks)

        return IngestReport(
            learning_path_id=learning_path_id,
            sources_processed=len(documents),
            chunks_created=len(chunks),
            tokens_embedded=sum(c.token_count for c in chunks),
            skipped_sources=skipped,
        )

    async def clear_learning_path(self, learning_path_id: UUID) -> None:
        await self._repo.clear_by_learning_path(learning_path_id)

    async def query(
        self,
        learning_path_id: UUID,
        text: str,
        k: int = 8,
        verified_only: bool = False,
    ) -> list[GroundedChunk]:
        vectors = await self._embedder.embed([text])
        hits = await self._repo.similarity_search(
            learning_path_id, vectors[0], k, verified_only
        )
        return [self._to_grounded(chunk, score) for chunk, score in hits]

    @staticmethod
    def _to_grounded(chunk: Chunk, score: float) -> GroundedChunk:
        meta = chunk.metadata or {}
        return GroundedChunk(
            content=chunk.content,
            citation=Citation(
                source_id=chunk.source_id,
                title=meta.get("title"),
                url=meta.get("url"),
                snippet=chunk.content[:_SNIPPET_LEN],
                score=score,
                verificada_google=bool(meta.get("verificada_google", False)),
            ),
        )
