"""RED-first spec de KBService: ingest + query grounded con citas (ADR-0006 §6)."""
import asyncio
from uuid import uuid4

from adapters.embeddings.mock import MockEmbedder
from repositories.kb.memory import InMemoryKbChunkRepository
from services.kb.service import KBService
from models.domain.source import Source


def _service():
    return KBService(embedder=MockEmbedder(), repository=InMemoryKbChunkRepository())


def _source(lp_id, verificada=False):
    return Source(id=uuid4(), learning_path_id=lp_id, url="https://x.dev/a",
                  title="Fuente A", tipo="youtube", verificada_google=verificada)


def test_ingest_reports_chunks_and_tokens():
    lp = uuid4()
    svc = _service()
    src = _source(lp)
    report = asyncio.run(svc.ingest(lp, [src], {src.id: "# Doc\n\nContenido sobre IA."}))
    assert report.chunks_created >= 1
    assert report.tokens_embedded > 0
    assert report.sources_processed == 1


def test_query_returns_grounded_chunk_with_citation():
    lp = uuid4()
    svc = _service()
    src = _source(lp, verificada=True)
    text = "# Kubernetes\n\nUn pod es la unidad mínima de despliegue."
    asyncio.run(svc.ingest(lp, [src], {src.id: text}))
    # MockEmbedder es determinista por texto → consultar el MISMO texto da coseno ~1.0
    results = asyncio.run(svc.query(lp, text, k=5))
    assert results
    top = results[0]
    assert "pod" in top.content
    assert top.citation.source_id == src.id
    assert top.citation.title == "Fuente A"
    assert top.citation.snippet  # cita con extracto
    assert top.citation.score > 0.99


def test_query_is_scoped_by_learning_path():
    svc = _service()
    lp_a, lp_b = uuid4(), uuid4()
    sa, sb = _source(lp_a), _source(lp_b)
    asyncio.run(svc.ingest(lp_a, [sa], {sa.id: "Contenido exclusivo de la ruta A."}))
    asyncio.run(svc.ingest(lp_b, [sb], {sb.id: "Contenido exclusivo de la ruta B."}))
    results = asyncio.run(svc.query(lp_a, "contenido", k=10))
    assert results
    assert all(r.citation.source_id == sa.id for r in results)


def test_verified_only_filters_unverified_sources():
    lp = uuid4()
    svc = _service()
    ok = _source(lp, verificada=True)
    no = _source(lp, verificada=False)
    asyncio.run(svc.ingest(lp, [ok, no], {
        ok.id: "Fuente verificada por Google.",
        no.id: "Fuente sin verificar.",
    }))
    results = asyncio.run(svc.query(lp, "fuente", k=10, verified_only=True))
    assert results
    assert all(r.citation.verificada_google for r in results)
