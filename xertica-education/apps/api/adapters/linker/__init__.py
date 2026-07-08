"""Factory del puerto Linker Source↔Módulo (ADR-0012).

Sirve el linker vía OpenRouter (OpenAI-compatible) con `openrouter_key`. Mientras la
clave sea placeholder, corre con `MockLinker` (heurística determinista · regla de oro #1).
"""
from config.settings import settings
from .base import BaseLinker
from .mock import MockLinker


def get_linker() -> BaseLinker:
    key = settings.openrouter_key
    if not key or "placeholder" in key:
        return MockLinker()
    from .openrouter_linker import RealLinker  # lazy import del SDK real

    return RealLinker(
        api_key=key,
        base_url=settings.openrouter_base_url,
        model=settings.linker_model,
    )


__all__ = ["BaseLinker", "MockLinker", "get_linker"]
