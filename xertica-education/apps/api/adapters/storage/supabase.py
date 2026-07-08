import os
from typing import Optional
from supabase import create_client
from config.settings import settings
from adapters.storage.base import BaseStorageAdapter

class SupabaseStorageAdapter(BaseStorageAdapter):
    def __init__(self):
        self._supabase = None
        self.is_mock = True

        url = settings.supabase_url
        key = settings.supabase_key
        if url and "placeholder" not in url and key and "placeholder" not in key:
            try:
                self._supabase = create_client(url, key)
                self.is_mock = False
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase client in StorageAdapter: {e}")

    async def upload_file(self, bucket: str, path: str, file_bytes: bytes) -> str:
        """
        Uploads file bytes to Supabase Storage and returns the public URL.
        In mock/fallback mode, saves the file in the local 'static' folder and returns a local URL.
        """
        if not self.is_mock and self._supabase:
            try:
                # Clean path to avoid double slashes
                clean_path = path.lstrip("/")
                # Supabase storage upload
                # Note: using upsert=true or handling existing file
                self._supabase.storage.from_(bucket).upload(
                    path=clean_path,
                    file=file_bytes,
                    file_options={"cache-control": "3600", "upsert": "true"}
                )
                # Get public url
                public_url = self._supabase.storage.from_(bucket).get_public_url(clean_path)
                return public_url
            except Exception as e:
                print(f"Supabase storage upload failed, falling back to local storage: {e}")

        # Local storage fallback
        local_dir = os.path.join(os.getcwd(), "static", bucket)
        os.makedirs(local_dir, exist_ok=True)
        
        file_name = os.path.basename(path)
        local_file_path = os.path.join(local_dir, file_name)
        
        with open(local_file_path, "wb") as f:
            f.write(file_bytes)
            
        # Return a relative static URL (fastapi mounts static directory to serve these)
        local_url = f"http://localhost:8000/static/{bucket}/{file_name}"
        return local_url

    async def download_file(self, bucket: str, path: str) -> bytes:
        if not self.is_mock and self._supabase:
            try:
                res = self._supabase.storage.from_(bucket).download(path)
                return res
            except Exception as e:
                print(f"Supabase storage download failed: {e}")

        # Local fallback
        local_file_path = os.path.join(os.getcwd(), "static", bucket, os.path.basename(path))
        if os.path.exists(local_file_path):
            with open(local_file_path, "rb") as f:
                return f.read()
        return b""
