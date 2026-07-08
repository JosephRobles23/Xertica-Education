"""Repo Supabase de documentos (ADR-0008). Cliente perezoso."""
from uuid import UUID
from typing import Optional

from config.settings import settings
from models.domain.document import Document
from .interface import DocumentRepositoryInterface

_COLS = "id,learning_path_id,storage_path,filename,mime,use_as_source"


class SupabaseDocumentRepository(DocumentRepositoryInterface):
    def __init__(self) -> None:
        from supabase import create_client  # lazy

        self._client = create_client(settings.supabase_url, settings.supabase_key)

    async def create(self, document: Document) -> Document:
        resp = self._client.table("documents").insert({
            "learning_path_id": str(document.learning_path_id),
            "storage_path": document.storage_path,
            "filename": document.filename,
            "mime": document.mime,
            "use_as_source": document.use_as_source,
        }).execute()
        return _to_domain(resp.data[0])

    async def get(self, document_id: UUID) -> Optional[Document]:
        resp = (
            self._client.table("documents").select(_COLS)
            .eq("id", str(document_id)).limit(1).execute()
        )
        return _to_domain(resp.data[0]) if resp.data else None

    async def list_by_learning_path(self, learning_path_id: UUID) -> list[Document]:
        resp = (
            self._client.table("documents").select(_COLS)
            .eq("learning_path_id", str(learning_path_id)).execute()
        )
        return [_to_domain(row) for row in (resp.data or [])]


def _to_domain(row: dict) -> Document:
    return Document(
        id=row["id"], learning_path_id=row["learning_path_id"],
        storage_path=row["storage_path"], filename=row["filename"],
        mime=row.get("mime"), use_as_source=bool(row.get("use_as_source")),
    )
