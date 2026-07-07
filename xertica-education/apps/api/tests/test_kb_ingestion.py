"""RED-first spec del coordinador de ingesta (Gate 1 → KB). Slice del Job de ingesta."""
import asyncio
from uuid import uuid4

from adapters.embeddings.mock import MockEmbedder
from repositories.kb.memory import InMemoryKbChunkRepository
from services.kb.service import KBService
from services.kb.ingestion import (
    KbIngestionCoordinator,
    MockDocumentProvider,
    map_route_sources,
)

# forma de las fuentes tal como las persiste el deep-research en route["sources"]
ROUTE_SOURCES = [
    {"title": "Doc oficial Gemini", "url": "https://ai.google.dev/x", "kind": "documentation",
     "verified": True, "status": "approved"},
    {"title": "Video oficial Veo", "url": "https://youtube.com/watch?v=abc", "kind": "youtube",
     "verified": True, "status": "approved"},
    {"title": "Ejemplo comunitario", "url": "https://youtube.com/results?q=tips", "kind": "youtube",
     "verified": False, "status": "requires-review"},
]


def _coordinator():
    kb = KBService(embedder=MockEmbedder(), repository=InMemoryKbChunkRepository())
    return kb, KbIngestionCoordinator(kb, MockDocumentProvider())


def test_map_route_sources_keeps_only_verified():
    sources = map_route_sources(ROUTE_SOURCES)
    assert len(sources) == 2  # descarta la fuente 'requires-review' / no verificada
    assert all(s.verificada_google for s in sources)
    assert all(s.id is not None for s in sources)


def test_ingest_route_creates_chunks_from_approved_sources():
    lp = uuid4()
    _kb, coord = _coordinator()
    report = asyncio.run(coord.ingest_route(lp, ROUTE_SOURCES))
    assert report.sources_processed == 2
    assert report.chunks_created >= 2
    assert report.tokens_embedded > 0


def test_ingested_corpus_is_queryable_with_citations():
    lp = uuid4()
    kb, coord = _coordinator()
    asyncio.run(coord.ingest_route(lp, ROUTE_SOURCES))
    results = asyncio.run(kb.query(lp, "Gemini documentación oficial", k=5))
    assert results
    assert all(r.citation.verificada_google for r in results)
    assert any("gemini" in (r.citation.title or "").lower() for r in results)


def test_empty_or_all_unverified_sources_ingest_nothing():
    lp = uuid4()
    _kb, coord = _coordinator()
    only_unverified = [ROUTE_SOURCES[2]]
    report = asyncio.run(coord.ingest_route(lp, only_unverified))
    assert report.sources_processed == 0
    assert report.chunks_created == 0


# --- glue del Job en background (Gate 1) ---
from models.common import JobStatus  # noqa: E402
from routers.learning_paths import _run_kb_ingestion_job  # noqa: E402


class _FakeJobs:
    def __init__(self):
        self.status = None

    async def update_job_status(self, job_id, status):
        self.status = status


def test_background_job_marks_completed_and_populates_kb():
    kb, coord = _coordinator()
    jobs = _FakeJobs()
    lp = uuid4()
    asyncio.run(_run_kb_ingestion_job(coord, jobs, uuid4(), lp, ROUTE_SOURCES))
    assert jobs.status == JobStatus.COMPLETED
    assert asyncio.run(kb.query(lp, "Gemini", k=3))  # el corpus quedó consultable


def test_background_job_swallows_failure_and_marks_failed():
    class _Boom:
        async def ingest_route(self, *args):
            raise RuntimeError("infra no lista")

    jobs = _FakeJobs()
    # no debe propagar: Gate 1 no se bloquea aunque la ingesta falle
    asyncio.run(_run_kb_ingestion_job(_Boom(), jobs, uuid4(), uuid4(), []))
    assert jobs.status == JobStatus.FAILED
