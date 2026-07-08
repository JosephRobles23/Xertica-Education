"""Factory del repo de documentos (ADR-0004): real con credenciales, memory si placeholder."""
from config.settings import settings
from .interface import DocumentRepositoryInterface
from .memory import InMemoryDocumentRepository


def get_documents_repository() -> DocumentRepositoryInterface:
    if "placeholder" in settings.supabase_key or "placeholder" in settings.supabase_url:
        return InMemoryDocumentRepository()
    from .repository import SupabaseDocumentRepository  # lazy

    return SupabaseDocumentRepository()


__all__ = [
    "DocumentRepositoryInterface",
    "InMemoryDocumentRepository",
    "get_documents_repository",
]
