import os
from pathlib import Path
from typing import Optional

import httpx

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    aiofiles = None
    AIOFILES_AVAILABLE = False

from config.settings import settings


class PixabayMusicAdapter:
    PIXABAY_URL = "https://pixabay.com/api/"

    _STATIC_FALLBACK = str(
        Path(__file__).resolve().parent.parent.parent / "static" / "bg_music.mp3"
    )

    async def search_and_download(
        self,
        query: str = "corporate educational",
        output_path: str = "/tmp/bg_music.mp3",
    ) -> Optional[str]:
        key = settings.pixabay_api_key
        if not key or key == "placeholder-key" or key.startswith("placeholder"):
            return self._static_fallback()

        try:
            params = {
                "key": settings.pixabay_api_key,
                "q": query,
                "category": "music",
                "per_page": 5,
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self.PIXABAY_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                hits = data.get("hits", [])
                if not hits:
                    return self._static_fallback()

                first = hits[0]
                audio_url = first.get("previewURL") or first.get("largeAudioURL")
                if not audio_url:
                    return self._static_fallback()

                async with httpx.AsyncClient(timeout=30) as dl_client:
                    dl_resp = await dl_client.get(audio_url)
                    dl_resp.raise_for_status()

                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                if AIOFILES_AVAILABLE:
                    async with aiofiles.open(output_path, "wb") as f:
                        await f.write(dl_resp.content)
                else:
                    with open(output_path, "wb") as f:
                        f.write(dl_resp.content)

                return output_path

        except Exception as e:
            print(f"Pixabay music search/download failed: {e}")
            return self._static_fallback()

    def _static_fallback(self) -> Optional[str]:
        if os.path.exists(self._STATIC_FALLBACK):
            return self._STATIC_FALLBACK
        return None
