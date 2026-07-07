"""Factory del repositorio de chunks (ADR-0004): real con credenciales, memory si placeholder."""
from config.settings import settings
from .interface import KbChunkRepositoryInterface
from .memory import InMemoryKbChunkRepository


def get_kb_chunk_repository() -> KbChunkRepositoryInterface:
    if "placeholder" in settings.supabase_key or "placeholder" in settings.supabase_url:
        return InMemoryKbChunkRepository()
    from .repository import SupabaseKbChunkRepository  # lazy: solo con credenciales

    return SupabaseKbChunkRepository()


__all__ = ["KbChunkRepositoryInterface", "InMemoryKbChunkRepository", "get_kb_chunk_repository"]
