"""Spec del endpoint de subida POST /learning-paths/{id}/documents (Vía 2 · ADR-0008)."""
from uuid import uuid4

from fastapi.testclient import TestClient

import main
from config.dependencies import (
    get_storage_adapter, get_documents_repository, get_sourcing_repository,
)
from adapters.storage.memory import InMemoryStorageAdapter
from repositories.documents.memory import InMemoryDocumentRepository
from repositories.sourcing.memory import InMemorySourcingRepository


def test_upload_creates_document_and_source_when_use_as_source():
    main.app.dependency_overrides[get_storage_adapter] = lambda: InMemoryStorageAdapter()
    main.app.dependency_overrides[get_documents_repository] = lambda: InMemoryDocumentRepository()
    main.app.dependency_overrides[get_sourcing_repository] = lambda: InMemorySourcingRepository()
    try:
        client = TestClient(main.app)
        resp = client.post(
            f"/learning-paths/{uuid4()}/documents",
            files={"file": ("notas.md", b"# Titulo\n\ncuerpo", "text/markdown")},
            data={"use_as_source": "true"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["document_id"]
        assert body["use_as_source"] is True
        assert body["source_id"]  # se creó el Source Vía 2
    finally:
        main.app.dependency_overrides.clear()


def test_upload_without_use_as_source_creates_no_source():
    main.app.dependency_overrides[get_storage_adapter] = lambda: InMemoryStorageAdapter()
    main.app.dependency_overrides[get_documents_repository] = lambda: InMemoryDocumentRepository()
    main.app.dependency_overrides[get_sourcing_repository] = lambda: InMemorySourcingRepository()
    try:
        client = TestClient(main.app)
        resp = client.post(
            f"/learning-paths/{uuid4()}/documents",
            files={"file": ("notas.txt", b"solo contexto", "text/plain")},
            data={"use_as_source": "false"},
        )
        assert resp.status_code == 200
        assert resp.json()["source_id"] is None
    finally:
        main.app.dependency_overrides.clear()


def test_upload_rejects_legacy_format():
    client = TestClient(main.app)
    resp = client.post(
        f"/learning-paths/{uuid4()}/documents",
        files={"file": ("viejo.doc", b"x", "application/msword")},
        data={"use_as_source": "false"},
    )
    assert resp.status_code == 415
