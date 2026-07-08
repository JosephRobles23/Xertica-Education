"""RED-first spec del puerto Embedder (ADR-0006 §1)."""
import asyncio
import math

from adapters.embeddings.mock import MockEmbedder
from adapters.embeddings import get_embedder


def test_mock_embedder_dimension_and_shape():
    emb = MockEmbedder(dimension=1536)
    [vec] = asyncio.run(emb.embed(["hola mundo"]))
    assert len(vec) == 1536
    assert all(isinstance(x, float) for x in vec)


def test_mock_embedder_is_deterministic():
    emb = MockEmbedder()
    a = asyncio.run(emb.embed(["texto igual"]))
    b = asyncio.run(emb.embed(["texto igual"]))
    assert a == b


def test_mock_embedder_is_normalized():
    emb = MockEmbedder()
    [vec] = asyncio.run(emb.embed(["cualquier cosa"]))
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-6


def test_different_texts_give_different_vectors():
    emb = MockEmbedder()
    [a] = asyncio.run(emb.embed(["uno"]))
    [b] = asyncio.run(emb.embed(["dos"]))
    assert a != b


def test_factory_selects_mock_vs_openrouter_by_key(monkeypatch):
    from config.settings import settings
    from adapters.embeddings.openai_embedder import OpenAIEmbedder

    # placeholder → mock (sin red)
    monkeypatch.setattr(settings, "openrouter_key", "placeholder-key")
    assert isinstance(get_embedder(), MockEmbedder)

    # clave real → adapter OpenRouter (construcción sin importar el SDK; no hay red aquí)
    monkeypatch.setattr(settings, "openrouter_key", "sk-or-v1-fake")
    emb = get_embedder()
    assert isinstance(emb, OpenAIEmbedder)
    assert emb.dimension == 1536
    assert emb._base_url == settings.openrouter_base_url
    assert emb._model == "openai/text-embedding-3-small"
