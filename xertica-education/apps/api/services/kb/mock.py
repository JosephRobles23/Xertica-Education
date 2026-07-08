"""MockKBService: grounding placeholder para consumidores (regla de oro · ADR-0002).

Permite a Santiago/Sebas/Shared construir generadores contra el puerto
`KnowledgeBase` sin ingesta real: devuelve chunks sintéticos con cita.
"""
from uuid import UUID, uuid4

from models.domain.kb import Citation, GroundedChunk, IngestReport
from models.domain.source import Source
from .interface import KnowledgeBaseInterface


class MockKBService(KnowledgeBaseInterface):
    async def ingest(
        self,
        learning_path_id: UUID,
        sources: list[Source],
        documents: dict[UUID, str],
    ) -> IngestReport:
        return IngestReport(
            learning_path_id=learning_path_id,
            sources_processed=len(documents),
            chunks_created=len(documents),
            tokens_embedded=len(documents) * 100,
        )

    async def query(
        self,
        learning_path_id: UUID,
        text: str,
        k: int = 8,
        verified_only: bool = False,
    ) -> list[GroundedChunk]:
        return [
            GroundedChunk(
                content=f"[mock grounding] Fragmento relevante para: {text}",
                citation=Citation(
                    source_id=uuid4(),
                    title="Fuente mock",
                    url="https://example.dev/mock",
                    snippet=f"Contexto simulado sobre {text}",
                    score=1.0 - i * 0.1,
                    verificada_google=True,
                ),
            )
            for i in range(min(k, 3))
        ]
