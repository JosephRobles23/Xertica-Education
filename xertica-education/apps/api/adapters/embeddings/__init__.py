"""Factory del puerto Embedder (ADR-0006).

Sirve embeddings vía OpenRouter (OpenAI-compatible) con `openrouter_key`. Mientras
la clave sea placeholder, todo corre con `MockEmbedder` (regla de oro #1).
"""
from config.settings import settings
from .base import BaseEmbedder
from .mock import MockEmbedder


def get_embedder() -> BaseEmbedder:
    key = settings.openrouter_key
    if not key or "placeholder" in key:
        return MockEmbedder(dimension=settings.embedding_dimension)
    from .openai_embedder import OpenAIEmbedder  # lazy import del SDK real

    return OpenAIEmbedder(
        api_key=key,
        dimension=settings.embedding_dimension,
        base_url=settings.openrouter_base_url,
        model=settings.embedding_model,
    )


__all__ = ["BaseEmbedder", "MockEmbedder", "get_embedder"]
