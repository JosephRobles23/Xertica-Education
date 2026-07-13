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


def _mock_markdown(source: Source) -> str:
    title = source.title or "Fuente"
    ref = source.url or f"documento {source.document_id}"
    return (
        f"# {title}\n\n"
        f"Resumen de la fuente {title} ({ref}).\n\n"
        f"## Puntos clave\n\n"
        f"Contenido simulado para el grounding del MVP, sustituible por el "
        f"fetch/parse real.\n\n"
        f"## Detalle\n\n"
        f"Material de referencia asociado a {ref}."
    )


class MockDocumentProvider(DocumentProvider):
    """Sintetiza Markdown de relleno; reemplazable por fetch/parse real."""

    async def fetch(self, source: Source) -> str:
        return _mock_markdown(source)


class RealDocumentProvider(DocumentProvider):
    """Solo Vía 2 (upload · ADR-0011): entrega el Markdown del documento. Prefiere el
    `parsed_md` cacheado en la subida (parse-at-upload · ADR-0013); si falta, cae al
    fetch+parse del binario. Las fuentes de Vía 1 (url) NO se ingestan — devuelve ""."""

    def __init__(self, storage, documents_repo, parser, bucket: str):
        self._storage = storage
        self._documents = documents_repo
        self._parser = parser
        self._bucket = bucket

    async def fetch(self, source: Source) -> str:
        if source.origin == "upload" and source.document_id:
            doc = await self._documents.get(source.document_id)
            if doc is None:
                return ""
            if doc.parsed_md:  # parse-at-upload (ADR-0013): reutiliza sin re-parsear
                return doc.parsed_md
            data = await self._storage.download_file(self._bucket, doc.storage_path)
            return await self._parser.parse_document(data, doc.filename)
        return ""  # Vía 1 no alimenta la KB (ADR-0011)


class KbIngestionCoordinator:
    """Orquesta: fuentes (persistidas) → documentos → `KnowledgeBase.ingest`."""

    def __init__(self, knowledge_base: KnowledgeBaseInterface, document_provider: DocumentProvider):
        self._kb = knowledge_base
        self._provider = document_provider

    async def ingest_sources(self, learning_path_id, sources: list[Source]) -> IngestReport:
        lp = as_uuid(learning_path_id)
        # clear-and-reingest (decisión del grill): el índice refleja el corpus
        # actual; re-proponer estructura o re-aprobar Gate 1 no acumula duplicados.
        await self._kb.clear_learning_path(lp)
        documents = {s.id: await self._provider.fetch(s) for s in sources}
        return await self._kb.ingest(lp, sources, documents)
