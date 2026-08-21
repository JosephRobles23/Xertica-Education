"""Storage real sobre Google Cloud Storage (ADR-0008).

Alternativa a Supabase Storage para artefactos grandes: Supabase Free limita los
objetos a 50 MiB y los videos renderizados (~50 MB) fallan con HTTP 413. GCS no
tiene ese tope pequeño.

Autenticación: Application Default Credentials — la misma service account que ya
usan Veo/Imagen vía ``GOOGLE_APPLICATION_CREDENTIALS``. Cliente perezoso.

URL pública: ``https://storage.googleapis.com/<bucket>/<path>``. Requiere que el
bucket permita lectura pública (``allUsers`` → ``roles/storage.objectViewer``),
igual que las URLs públicas que devolvía Supabase. Ver docs/deployment.
"""
import asyncio
import mimetypes

from .base import BaseStorageAdapter


class GCSStorageAdapter(BaseStorageAdapter):
    def __init__(self) -> None:
        from google.cloud import storage  # lazy: solo con credenciales reales

        self._client = storage.Client()

    async def upload_file(self, bucket: str, path: str, file_bytes: bytes) -> str:
        # google-cloud-storage es síncrono/bloqueante: lo sacamos del event loop.
        return await asyncio.to_thread(self._upload_sync, bucket, path, file_bytes)

    def _upload_sync(self, bucket: str, path: str, file_bytes: bytes) -> str:
        clean_path = path.lstrip("/")
        content_type = mimetypes.guess_type(clean_path)[0] or "application/octet-stream"
        blob = self._client.bucket(bucket).blob(clean_path)
        blob.upload_from_string(file_bytes, content_type=content_type)
        return f"https://storage.googleapis.com/{bucket}/{clean_path}"

    async def download_file(self, bucket: str, path: str) -> bytes:
        return await asyncio.to_thread(self._download_sync, bucket, path)

    def _download_sync(self, bucket: str, path: str) -> bytes:
        return self._client.bucket(bucket).blob(path.lstrip("/")).download_as_bytes()
