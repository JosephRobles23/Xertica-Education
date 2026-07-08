"""Factory del StorageAdapter (ADR-0004): real con credenciales, memory si placeholder."""
from config.settings import settings
from .base import BaseStorageAdapter
from .memory import InMemoryStorageAdapter


def get_storage_adapter() -> BaseStorageAdapter:
    if "placeholder" in settings.supabase_key or "placeholder" in settings.supabase_url:
        return InMemoryStorageAdapter()
    from .supabase_storage import SupabaseStorageAdapter  # lazy

    return SupabaseStorageAdapter()


__all__ = ["BaseStorageAdapter", "InMemoryStorageAdapter", "get_storage_adapter"]
