"""Coordinación sourcing → KB: ingesta las fuentes ya persistidas de una ruta (ADR-0006 §3).

El upsert a `sources` (ADR-0007) ocurre en el router antes de llamar aquí; este coordinador
recibe las `Source` con id real y produce sus documentos + los ingesta. El contenido real
(fetch de URL / parse de archivo) llega con los crawlers de Arantza y el parser; por ahora
`MockDocumentProvider` cumple el contrato (regla de oro · ADR-0002).
"""
from abc import ABC, abstractmethod

from models.common import as_uuid
from models.domain.kb import IngestReport
from models.domain.source import Source
from .interface import KnowledgeBaseInterface


class DocumentProvider(ABC):
    """Puerto: dada una fuente, entrega su contenido en Markdown para la KB."""

    @abstractmethod
    async def fetch(self, source: Source) -> str:
        ...


class MockDocumentProvider(DocumentProvider):
    """Sintetiza Markdown de relleno; reemplazable por fetch/parse real."""

    async def fetch(self, source: Source) -> str:
        title = source.title or "Fuente"
        return (
            f"# {title}\n\n"
            f"Resumen de la fuente {title} ({source.url}).\n\n"
            f"## Puntos clave\n\n"
            f"Contenido simulado para el grounding del MVP, sustituible por el "
            f"fetch/parse real (crawlers + parser).\n\n"
            f"## Detalle\n\n"
            f"Material de referencia asociado a {source.url}."
        )


class KbIngestionCoordinator:
    """Orquesta: fuentes (persistidas) → documentos → `KnowledgeBase.ingest`."""

    def __init__(self, knowledge_base: KnowledgeBaseInterface, document_provider: DocumentProvider):
        self._kb = knowledge_base
        self._provider = document_provider

    async def ingest_sources(self, learning_path_id, sources: list[Source]) -> IngestReport:
        documents = {s.id: await self._provider.fetch(s) for s in sources}
        return await self._kb.ingest(as_uuid(learning_path_id), sources, documents)
