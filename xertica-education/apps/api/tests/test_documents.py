"""Spec de storage + repo de documentos + RealDocumentProvider (Vía 2 · ADR-0008)."""
import asyncio
from uuid import uuid4

from adapters.storage.memory import InMemoryStorageAdapter
from repositories.documents.memory import InMemoryDocumentRepository
from adapters.parser.simple import SimpleParserAdapter
from services.kb.ingestion import RealDocumentProvider
from models.domain.document import Document
from models.domain.source import Source


def test_storage_roundtrip():
    st = InMemoryStorageAdapter()
    asyncio.run(st.upload_file("bucket", "lp/x.txt", b"hola"))
    assert asyncio.run(st.download_file("bucket", "lp/x.txt")) == b"hola"


def test_documents_repo_create_get_list():
    repo = InMemoryDocumentRepository()
    lp = uuid4()
    doc = asyncio.run(repo.create(Document(
        learning_path_id=lp, storage_path="lp/a.txt", filename="a.txt", use_as_source=True)))
    assert doc.id is not None
    assert asyncio.run(repo.get(doc.id)).filename == "a.txt"
    assert len(asyncio.run(repo.list_by_learning_path(lp))) == 1


def test_real_provider_parses_uploaded_file():
    lp = uuid4()
    st = InMemoryStorageAdapter()
    repo = InMemoryDocumentRepository()
    asyncio.run(st.upload_file("bucket", "lp/notas.md", b"# Kubernetes\n\nUn pod es la unidad."))
    doc = asyncio.run(repo.create(Document(
        learning_path_id=lp, storage_path="lp/notas.md", filename="notas.md", use_as_source=True)))

    provider = RealDocumentProvider(st, repo, SimpleParserAdapter(), "bucket")
    src = Source(learning_path_id=lp, origin="upload", document_id=doc.id, title="notas.md")
    md = asyncio.run(provider.fetch(src))
    assert "Kubernetes" in md  # texto verbatim del archivo, no mock


def test_real_provider_ignores_via1_url_source():
    # ADR-0011: las fuentes de Vía 1 (url de YouTube) no se ingestan → "".
    provider = RealDocumentProvider(
        InMemoryStorageAdapter(), InMemoryDocumentRepository(), SimpleParserAdapter(), "bucket")
    src = Source(learning_path_id=uuid4(), origin="deep_research", url="https://x.dev/a", title="Doc oficial")
    md = asyncio.run(provider.fetch(src))
    assert md == ""


def test_real_provider_prefers_parsed_md_cache():
    # ADR-0013: si el doc trae parsed_md (parse-at-upload), se reutiliza sin tocar Storage.
    lp = uuid4()
    repo = InMemoryDocumentRepository()
    doc = asyncio.run(repo.create(Document(
        learning_path_id=lp, storage_path="lp/x.pdf", filename="x.pdf",
        use_as_source=True, parsed_md="## Página 1\n\nContenido cacheado.")))
    # Storage vacío a propósito: si intentara descargar, no habría binario.
    provider = RealDocumentProvider(InMemoryStorageAdapter(), repo, SimpleParserAdapter(), "bucket")
    src = Source(learning_path_id=lp, origin="upload", document_id=doc.id, title="x.pdf")
    md = asyncio.run(provider.fetch(src))
    assert md == "## Página 1\n\nContenido cacheado."
