from abc import ABC, abstractmethod

class BaseStorageAdapter(ABC):
    @abstractmethod
    async def upload_file(self, bucket: str, path: str, file_bytes: bytes) -> str:
        """Uploads file bytes to storage and returns the public url."""
        pass

    @abstractmethod
    async def download_file(self, bucket: str, path: str) -> bytes:
        """Downloads file bytes from storage."""
        pass
