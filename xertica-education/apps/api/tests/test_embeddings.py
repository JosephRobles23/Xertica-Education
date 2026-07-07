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


def test_factory_returns_mock_when_key_is_placeholder():
    # settings trae openai_key = 'placeholder-key' por defecto → mock, sin red
    emb = get_embedder()
    assert isinstance(emb, MockEmbedder)
    assert emb.dimension == 1536
