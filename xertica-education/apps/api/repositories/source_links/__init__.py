"""Factory del repo de vinculación Source↔Módulo (ADR-0004): real con credenciales,
memory si placeholder."""
from config.settings import settings
from .interface import SourceLinkRepositoryInterface
from .memory import InMemorySourceLinkRepository


def get_source_link_repository() -> SourceLinkRepositoryInterface:
    if "placeholder" in settings.supabase_key or "placeholder" in settings.supabase_url:
        return InMemorySourceLinkRepository()
    from .repository import SupabaseSourceLinkRepository  # lazy: solo con credenciales

    return SupabaseSourceLinkRepository()


__all__ = [
    "SourceLinkRepositoryInterface",
    "InMemorySourceLinkRepository",
    "get_source_link_repository",
]
