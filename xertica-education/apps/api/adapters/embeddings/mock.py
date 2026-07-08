import hashlib
import math

from .base import BaseEmbedder


class MockEmbedder(BaseEmbedder):
    """Embedder determinista sin red (regla de oro · ADR-0002).

    Deriva un vector estable por hash del texto y lo normaliza, de modo que el
    coseno de un texto consigo mismo sea 1.0 — suficiente para ejercitar el
    pipeline RAG y los tests sin depender de OpenAI.
    """

    def __init__(self, dimension: int = 1536):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        seed = text.encode("utf-8")
        vec: list[float] = []
        counter = 0
        while len(vec) < self._dimension:
            digest = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            for byte in digest:
                if len(vec) >= self._dimension:
                    break
                vec.append((byte / 255.0) * 2.0 - 1.0)  # → [-1, 1]
            counter += 1
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]
