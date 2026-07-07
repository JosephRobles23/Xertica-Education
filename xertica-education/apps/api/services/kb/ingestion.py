"""Coordinación Gate 1 → KB: convierte las fuentes aprobadas de la ruta en corpus
ingestado (ADR-0006 §3). Se dispara como Job tras `/sourcing/approve`.

El contenido real de cada fuente (fetch de URL / parse de archivo subido) llega con
los crawlers de Arantza y el parser; aquí `MockDocumentProvider` cumple el contrato
mientras tanto (regla de oro · ADR-0002).
"""
from abc import ABC, abstractmethod
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from adapters.embeddings.base import BaseEmbedder  # noqa: F401  (documenta la dependencia del puerto)
from models.domain.kb import IngestReport
from models.domain.source import Source
from .interface import KnowledgeBaseInterface

# kind del deep-research → tipo canónico de Source (ADR-0005)
_KIND_TO_TIPO = {
    "youtube": "youtube",
    "documentation": "blog_oficial",
    "article": "blog_oficial",
}


def map_route_sources(route_sources: list[dict]) -> list[Source]:
    """Mapea las fuentes de `route["sources"]` a `Source`, quedándose solo con las
    verificadas (las que superan Gate 1 y pueden alimentar la KB)."""
    sources: list[Source] = []
    for raw in route_sources or []:
        if not raw.get("verified"):
            continue
        sources.append(Source(
            id=uuid4(),
            url=raw.get("url", ""),
            title=raw.get("title"),
            tipo=_KIND_TO_TIPO.get(raw.get("kind"), "blog_oficial"),
            verificada_google=True,
        ))
    return sources


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
    """Orquesta: fuentes aprobadas → documentos → `KnowledgeBase.ingest`."""

    def __init__(self, knowledge_base: KnowledgeBaseInterface, document_provider: DocumentProvider):
        self._kb = knowledge_base
        self._provider = document_provider

    async def ingest_route(self, learning_path_id, route_sources: list[dict]) -> IngestReport:
        sources = map_route_sources(route_sources)
        documents = {s.id: await self._provider.fetch(s) for s in sources}
        return await self._kb.ingest(_as_uuid(learning_path_id), sources, documents)


def _as_uuid(value) -> UUID:
    """Normaliza el id de ruta (str|UUID) a UUID; deriva uno estable si no lo es."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return uuid5(NAMESPACE_URL, str(value))
