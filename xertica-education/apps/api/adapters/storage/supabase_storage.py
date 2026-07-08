"""Storage real sobre Supabase Storage (ADR-0008). Cliente perezoso."""
from config.settings import settings
from .base import BaseStorageAdapter


class SupabaseStorageAdapter(BaseStorageAdapter):
    def __init__(self) -> None:
        from supabase import create_client  # lazy: solo con credenciales reales

        self._client = create_client(settings.supabase_url, settings.supabase_key)

    async def upload_file(self, bucket: str, path: str, file_bytes: bytes) -> str:
        self._client.storage.from_(bucket).upload(
            path, file_bytes, {"upsert": "true"}
        )
        return self._client.storage.from_(bucket).get_public_url(path)

    async def download_file(self, bucket: str, path: str) -> bytes:
        return self._client.storage.from_(bucket).download(path)
