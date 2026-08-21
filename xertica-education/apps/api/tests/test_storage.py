import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import adapters.storage as storage_pkg
from adapters.storage import get_storage_adapter
from adapters.storage.memory import InMemoryStorageAdapter


class TestGCSStorageAdapter(unittest.TestCase):
    def _adapter_with_fake_client(self):
        fake_blob = MagicMock()
        fake_bucket = MagicMock()
        fake_bucket.blob.return_value = fake_blob
        fake_client = MagicMock()
        fake_client.bucket.return_value = fake_bucket
        with patch("google.cloud.storage.Client", return_value=fake_client):
            from adapters.storage.gcs import GCSStorageAdapter
            adapter = GCSStorageAdapter()
        return adapter, fake_bucket, fake_blob

    def test_upload_returns_public_url_and_cleans_path(self):
        adapter, fake_bucket, _ = self._adapter_with_fake_client()
        url = asyncio.run(adapter.upload_file("my-bucket", "/videos/j/capsule.mp4", b"data"))
        self.assertEqual(url, "https://storage.googleapis.com/my-bucket/videos/j/capsule.mp4")
        fake_bucket.blob.assert_called_once_with("videos/j/capsule.mp4")

    def test_upload_sets_content_type_from_extension(self):
        adapter, _, fake_blob = self._adapter_with_fake_client()
        asyncio.run(adapter.upload_file("b", "videos/j/capsule.mp4", b"data"))
        _, kwargs = fake_blob.upload_from_string.call_args
        self.assertEqual(kwargs.get("content_type"), "video/mp4")


class TestStorageFactory(unittest.TestCase):
    def test_factory_returns_gcs_when_backend_is_gcs(self):
        from adapters.storage.gcs import GCSStorageAdapter
        with patch.object(storage_pkg.settings, "storage_backend", "gcs"), \
             patch("google.cloud.storage.Client", return_value=MagicMock()):
            adapter = get_storage_adapter()
        self.assertIsInstance(adapter, GCSStorageAdapter)

    def test_factory_falls_back_to_memory_on_supabase_placeholders(self):
        # En el entorno de test supabase_url/key son placeholders → InMemory.
        with patch.object(storage_pkg.settings, "storage_backend", "supabase"):
            adapter = get_storage_adapter()
        self.assertIsInstance(adapter, InMemoryStorageAdapter)


if __name__ == "__main__":
    unittest.main()
