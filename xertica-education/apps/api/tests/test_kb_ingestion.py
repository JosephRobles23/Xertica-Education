"""Spec del flujo sourcing → KB: persistir fuentes y luego ingestar las verificadas."""
import asyncio
from uuid import uuid4

from adapters.embeddings.mock import MockEmbedder
from repositories.kb.memory import InMemoryKbChunkRepository
from repositories.sourcing.memory import InMemorySourcingRepository
from repositories.sourcing.mapping import route_sources_to_domain
from services.kb.service import KBService
from services.kb.ingestion import KbIngestionCoordinator, MockDocumentProvider
from models.common import JobStatus
from routers.learning_paths import _run_kb_ingestion_job

ROUTE_SOURCES = [
    {"title": "Doc oficial Gemini", "url": "https://ai.google.dev/x", "kind": "documentation",
     "verified": True, "status": "approved"},
    {"title": "Video oficial Veo", "url": "https://youtube.com/watch?v=abc", "kind": "youtube",
     "verified": True, "status": "approved"},
    {"title": "Ejemplo comunitario", "url": "https://youtube.com/results?q=tips", "kind": "youtube",
     "verified": False, "status": "requires-review"},
]


def _setup():
    kb = KBService(embedder=MockEmbedder(), repository=InMemoryKbChunkRepository())
    return kb, KbIngestionCoordinator(kb, MockDocumentProvider()), InMemorySourcingRepository()


async def _persist_verified(repo, lp):
    persisted = await repo.upsert_sources(route_sources_to_domain(ROUTE_SOURCES, lp))
    return [s for s in persisted if s.verificada_google]


class _FakeJobs:
    def __init__(self):
        self.status = None
        self.error = None
        self.result = None

    async def update_job_status(self, job_id, status, error=None, result=None):
        self.status = status
        self.error = error
        if result is not None:
            self.result = result


def test_ingest_sources_creates_chunks_from_verified():
    lp = uuid4()
    kb, coord, repo = _setup()
    verified = asyncio.run(_persist_verified(repo, lp))
    report = asyncio.run(coord.ingest_sources(lp, verified))
    assert report.sources_processed == 2  # solo las 2 verificadas
    assert report.chunks_created >= 2
    assert report.tokens_embedded > 0


def test_ingested_corpus_is_queryable_with_citations():
    lp = uuid4()
    kb, coord, repo = _setup()
    verified = asyncio.run(_persist_verified(repo, lp))
    asyncio.run(coord.ingest_sources(lp, verified))
    results = asyncio.run(kb.query(lp, "documentación oficial de Gemini", k=5))
    assert results
    assert all(r.citation.verificada_google for r in results)
    # las citas apuntan a las fuentes persistidas (id real del repo)
    persisted_ids = {s.id for s in asyncio.run(repo.list_by_learning_path(lp))}
    assert all(r.citation.source_id in persisted_ids for r in results)


def test_background_job_marks_completed_and_populates_kb():
    lp = uuid4()
    kb, coord, repo = _setup()
    verified = asyncio.run(_persist_verified(repo, lp))
    jobs = _FakeJobs()
    asyncio.run(_run_kb_ingestion_job(coord, jobs, uuid4(), lp, verified))
    assert jobs.status == JobStatus.COMPLETED
    # El IngestReport queda en job.result para observabilidad de la ingesta.
    assert jobs.result["chunks_created"] >= 2
    assert jobs.result["corpus_size"] == 2
    assert asyncio.run(kb.query(lp, "Gemini", k=3))


def test_background_job_with_empty_corpus_marks_failed_with_report():
    # Un Gate 1 sin fuentes Vía-2 era un no-op silencioso; ahora queda visible.
    kb, coord, repo = _setup()
    jobs = _FakeJobs()
    asyncio.run(_run_kb_ingestion_job(coord, jobs, uuid4(), uuid4(), []))
    assert jobs.status == JobStatus.FAILED
    assert "origin='upload'" in jobs.error
    assert jobs.result["chunks_created"] == 0
    assert jobs.result["corpus_size"] == 0


def test_reingest_is_clear_and_replace_not_append():
    # Re-proponer estructura / re-aprobar Gate 1 no debe duplicar chunks (decisión del grill).
    lp = uuid4()
    kb, coord, repo = _setup()
    verified = asyncio.run(_persist_verified(repo, lp))
    first = asyncio.run(coord.ingest_sources(lp, verified))
    second = asyncio.run(coord.ingest_sources(lp, verified))
    assert second.chunks_created == first.chunks_created  # reemplaza, no acumula
    # El store tiene exactamente una copia, no dos.
    assert len(kb._repo._chunks) == second.chunks_created


class _EmptyDocProvider:
    """Simula un documento sin texto extraíble (PDF escaneado)."""

    async def fetch(self, source):
        return ""


def test_skipped_sources_reported_and_job_failed():
    from services.kb.ingestion import KbIngestionCoordinator

    lp = uuid4()
    kb, _, repo = _setup()
    coord = KbIngestionCoordinator(kb, _EmptyDocProvider())
    verified = asyncio.run(_persist_verified(repo, lp))
    jobs = _FakeJobs()
    asyncio.run(_run_kb_ingestion_job(coord, jobs, uuid4(), lp, verified))
    assert jobs.status == JobStatus.FAILED
    assert "texto extraíble" in jobs.error
    assert len(jobs.result["skipped_sources"]) == 2


def test_background_job_swallows_failure_and_marks_failed():
    class _Boom:
        async def ingest_sources(self, *args):
            raise RuntimeError("infra no lista")

    jobs = _FakeJobs()
    asyncio.run(_run_kb_ingestion_job(_Boom(), jobs, uuid4(), uuid4(), []))
    assert jobs.status == JobStatus.FAILED
