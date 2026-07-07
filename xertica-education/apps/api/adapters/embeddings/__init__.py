"""Factory del puerto Embedder (ADR-0006).

Selecciona mock vs real según la clave: mientras `openai_key` sea placeholder,
todo corre con `MockEmbedder` (regla de oro #1). Con una clave real, usa OpenAI.
"""
from config.settings import settings
from .base import BaseEmbedder
from .mock import MockEmbedder


def get_embedder() -> BaseEmbedder:
    key = settings.openai_key
    if not key or "placeholder" in key:
        return MockEmbedder(dimension=settings.embedding_dimension)
    from .openai_embedder import OpenAIEmbedder  # lazy import del SDK real

    return OpenAIEmbedder(api_key=key, dimension=settings.embedding_dimension)


__all__ = ["BaseEmbedder", "MockEmbedder", "get_embedder"]
