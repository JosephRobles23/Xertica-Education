"""Spec del endpoint POST /kb/query (grounding para los generadores · ADR-0006)."""
import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient

import main
from config.dependencies import get_knowledge_base
from services.kb.service import KBService
from adapters.embeddings.mock import MockEmbedder
from repositories.kb.memory import InMemoryKbChunkRepository
from models.domain.source import Source

_TEXT = "# Kubernetes\n\nUn pod es la unidad mínima de despliegue."


def _kb_with_data(lp):
    kb = KBService(embedder=MockEmbedder(), repository=InMemoryKbChunkRepository())
    src = Source(id=uuid4(), learning_path_id=lp, url="https://x.dev/a",
                 title="Fuente A", tipo="youtube", verificada_google=True)
    asyncio.run(kb.ingest(lp, [src], {src.id: _TEXT}))
    return kb


def test_query_endpoint_returns_grounded_chunks():
    lp = uuid4()
    main.app.dependency_overrides[get_knowledge_base] = lambda: _kb_with_data(lp)
    try:
        client = TestClient(main.app)
        resp = client.post("/kb/query", json={
            "learning_path_id": str(lp), "query": _TEXT, "k": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data
        top = data[0]
        assert "content" in top and "citation" in top
        assert top["citation"]["source_id"]
        assert top["citation"]["verificada_google"] is True
        assert top["citation"]["score"] > 0.99  # el mismo texto ⇒ coseno ~1
    finally:
        main.app.dependency_overrides.clear()


def test_query_endpoint_validates_body():
    client = TestClient(main.app)
    resp = client.post("/kb/query", json={"query": "falta learning_path_id"})
    assert resp.status_code == 422  # validación antes de tocar la KB (no golpea DB real)
