"""RED-first spec del repo de sourcing y el mapeo route[sources] -> Source (ADR-0007)."""
import asyncio
from uuid import uuid4

from repositories.sourcing.memory import InMemorySourcingRepository
from repositories.sourcing.mapping import route_sources_to_domain

ROUTE_SOURCES = [
    {"title": "Doc oficial", "url": "https://ai.google.dev/x", "kind": "documentation",
     "verified": True, "status": "approved"},
    {"title": "Comunitario", "url": "https://youtube.com/results?q=tips", "kind": "youtube",
     "verified": False, "status": "requires-review"},
]


def test_mapping_keeps_all_candidates_with_estado():
    lp = uuid4()
    sources = route_sources_to_domain(ROUTE_SOURCES, lp)
    assert len(sources) == 2  # todas las candidatas, no solo verificadas (decisión #3)
    approved = next(s for s in sources if s.url.endswith("/x"))
    assert approved.learning_path_id == lp
    assert approved.estado == "approved"
    assert approved.verificada_google is True
    assert approved.id is None  # el id lo asigna el repo


def test_upsert_assigns_ids_and_is_idempotent():
    lp = uuid4()
    repo = InMemorySourcingRepository()
    first = asyncio.run(repo.upsert_sources(route_sources_to_domain(ROUTE_SOURCES, lp)))
    assert all(s.id is not None for s in first)
    # segundo upsert de las mismas urls → mismos ids, sin duplicar
    second = asyncio.run(repo.upsert_sources(route_sources_to_domain(ROUTE_SOURCES, lp)))
    assert {s.id for s in first} == {s.id for s in second}
    assert len(asyncio.run(repo.list_by_learning_path(lp))) == 2


def test_upsert_preserves_human_estado_on_conflict():
    lp = uuid4()
    repo = InMemorySourcingRepository()
    asyncio.run(repo.upsert_sources(route_sources_to_domain(ROUTE_SOURCES, lp)))
    # un re-run del deep-research trae la misma url con estado distinto (auto)
    rerun = route_sources_to_domain(
        [{**ROUTE_SOURCES[0], "status": "requires-review", "verified": False, "title": "Doc v2"}], lp
    )
    out = asyncio.run(repo.upsert_sources(rerun))
    saved = out[0]
    assert saved.estado == "approved"          # preserva la decisión humana previa
    assert saved.verificada_google is True     # preserva verificación
    assert saved.title == "Doc v2"             # pero refresca metadata


def test_scoped_by_learning_path():
    repo = InMemorySourcingRepository()
    lp_a, lp_b = uuid4(), uuid4()
    asyncio.run(repo.upsert_sources(route_sources_to_domain(ROUTE_SOURCES, lp_a)))
    asyncio.run(repo.upsert_sources(route_sources_to_domain(ROUTE_SOURCES, lp_b)))
    assert len(asyncio.run(repo.list_by_learning_path(lp_a))) == 2
    assert len(asyncio.run(repo.list_by_learning_path(lp_b))) == 2
