"""Spec del linker Source↔Módulo (ADR-0012): heurística + persistencia + endpoint."""
import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient

import main
from adapters.linker.mock import MockLinker
from repositories.source_links.memory import InMemorySourceLinkRepository
from repositories.sourcing.memory import InMemorySourcingRepository
from models.domain.source import Source
from models.domain.source_module_link import SourceModuleLink
from config.dependencies import (
    get_route_service, get_sourcing_repository, get_source_link_repository, get_linker,
)

MODULES = [
    {"id": "r1m1", "name": "Fundamentos de Gemini", "type": "intro",
     "contents": [{"kind": "video", "summary": "Cápsula introductoria a Gemini"}]},
    {"id": "r1m2", "name": "Laboratorio de Veo", "type": "laboratorio",
     "contents": [{"kind": "video", "summary": "Práctica con Veo para generar video"}]},
]


def _sources(lp):
    return [
        Source(id=uuid4(), learning_path_id=lp, url="https://youtube.com/watch?v=g",
               title="Tutorial oficial de Gemini", tipo="youtube", verificada_google=True),
        Source(id=uuid4(), learning_path_id=lp, url="https://youtube.com/watch?v=v",
               title="Demo de Veo para video", tipo="youtube", verificada_google=True),
    ]


def test_mock_linker_assigns_best_source_per_module():
    lp = uuid4()
    srcs = _sources(lp)
    links = asyncio.run(MockLinker().link(lp, MODULES, srcs))
    by_module = {l.module_id: l for l in links}
    # cada módulo se vincula a la fuente que comparte su tema
    assert by_module["r1m1"].source_id == srcs[0].id  # Gemini
    assert by_module["r1m2"].source_id == srcs[1].id  # Veo
    assert all(l.origin == "llm" for l in links)


def test_mock_linker_empty_when_no_sources():
    assert asyncio.run(MockLinker().link(uuid4(), MODULES, [])) == []


def test_source_link_repo_upsert_is_idempotent():
    repo = InMemorySourceLinkRepository()
    lp, sid = uuid4(), uuid4()
    link = SourceModuleLink(learning_path_id=lp, source_id=sid, module_id="r1m1", score=0.5)
    asyncio.run(repo.upsert_links([link]))
    asyncio.run(repo.upsert_links([link.model_copy(update={"score": 0.9})]))
    rows = asyncio.run(repo.list_by_learning_path(lp))
    assert len(rows) == 1 and rows[0].score == 0.9  # UPSERT por (source_id, module_id)


def test_link_sources_endpoint_persists_and_returns():
    lp = uuid4()
    route = {"id": str(lp), "modules": MODULES, "sources": []}
    srcs = _sources(lp)

    class _RouteSvc:
        async def get_route(self, rid):
            return route

    class _Sourcing(InMemorySourcingRepository):
        async def list_by_learning_path(self, learning_path_id):
            return srcs

    link_repo = InMemorySourceLinkRepository()
    main.app.dependency_overrides[get_route_service] = lambda: _RouteSvc()
    main.app.dependency_overrides[get_sourcing_repository] = lambda: _Sourcing()
    main.app.dependency_overrides[get_source_link_repository] = lambda: link_repo
    main.app.dependency_overrides[get_linker] = lambda: MockLinker()
    try:
        client = TestClient(main.app)
        resp = client.post(f"/learning-paths/{lp}/link-sources", json={})
        assert resp.status_code == 200
        links = resp.json()["links"]
        assert len(links) == 2
        assert {l["module_id"] for l in links} == {"r1m1", "r1m2"}
        # se persistió
        assert len(asyncio.run(link_repo.list_by_learning_path(lp))) == 2
    finally:
        main.app.dependency_overrides.clear()


def test_link_sources_endpoint_single_module():
    lp = uuid4()
    route = {"id": str(lp), "modules": MODULES, "sources": []}
    srcs = _sources(lp)

    class _RouteSvc:
        async def get_route(self, rid):
            return route

    class _Sourcing(InMemorySourcingRepository):
        async def list_by_learning_path(self, learning_path_id):
            return srcs

    main.app.dependency_overrides[get_route_service] = lambda: _RouteSvc()
    main.app.dependency_overrides[get_sourcing_repository] = lambda: _Sourcing()
    main.app.dependency_overrides[get_source_link_repository] = lambda: InMemorySourceLinkRepository()
    main.app.dependency_overrides[get_linker] = lambda: MockLinker()
    try:
        client = TestClient(main.app)
        resp = client.post(f"/learning-paths/{lp}/link-sources", json={"module_id": "r1m2"})
        assert resp.status_code == 200
        links = resp.json()["links"]
        assert len(links) == 1 and links[0]["module_id"] == "r1m2"
    finally:
        main.app.dependency_overrides.clear()
