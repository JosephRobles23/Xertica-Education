from .base import BaseEmbedder


class OpenAIEmbedder(BaseEmbedder):
    """Adapter real: OpenAI text-embedding-3-small (ADR-0006 §1).

    Import perezoso del SDK: el camino mock no requiere tener `openai` instalado.
    Instala el extra con `uv sync --extra rag`.
    """

    MODEL = "text-embedding-3-small"

    def __init__(self, api_key: str, dimension: int = 1536):
        self._api_key = api_key
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        from openai import AsyncOpenAI  # lazy: solo cuando se usa el path real

        client = AsyncOpenAI(api_key=self._api_key)
        resp = await client.embeddings.create(
            model=self.MODEL, input=texts, dimensions=self._dimension
        )
        return [item.embedding for item in resp.data]
