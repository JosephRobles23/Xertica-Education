"""Storage in-memory (fallback · ADR-0004). Round-trip de bytes para tests/MVP sin creds."""
from .base import BaseStorageAdapter


class InMemoryStorageAdapter(BaseStorageAdapter):
    def __init__(self) -> None:
        self._store: dict[tuple, bytes] = {}

    async def upload_file(self, bucket: str, path: str, file_bytes: bytes) -> str:
        self._store[(bucket, path)] = file_bytes
        return f"memory://{bucket}/{path}"

    async def download_file(self, bucket: str, path: str) -> bytes:
        return self._store[(bucket, path)]
