"""Factory del repo de sourcing (ADR-0004): real con credenciales, memory si placeholder."""
from config.settings import settings
from .interface import SourcingRepositoryInterface
from .memory import InMemorySourcingRepository


def get_sourcing_repository() -> SourcingRepositoryInterface:
    if "placeholder" in settings.supabase_key or "placeholder" in settings.supabase_url:
        return InMemorySourcingRepository()
    from .repository import SupabaseSourcingRepository  # lazy: solo con credenciales

    return SupabaseSourcingRepository()


__all__ = [
    "SourcingRepositoryInterface",
    "InMemorySourcingRepository",
    "get_sourcing_repository",
]
