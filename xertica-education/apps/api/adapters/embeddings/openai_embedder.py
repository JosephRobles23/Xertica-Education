from .base import BaseEmbedder


class OpenAIEmbedder(BaseEmbedder):
    """Adapter real de embeddings, OpenAI-compatible (ADR-0006 §1).

    Por defecto apunta a **OpenRouter** (`base_url` + `openrouter_key`) con el modelo
    `openai/text-embedding-3-small`. Import perezoso del SDK `openai`: el camino mock
    no lo requiere. Instala el extra con `uv sync --extra rag`.
    """

    def __init__(
        self,
        api_key: str,
        dimension: int = 1536,
        base_url: str | None = None,
        model: str = "openai/text-embedding-3-small",
    ):
        self._api_key = api_key
        self._dimension = dimension
        self._base_url = base_url
        self._model = model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        from openai import AsyncOpenAI  # lazy: solo cuando se usa el path real

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        resp = await client.embeddings.create(
            model=self._model, input=texts, dimensions=self._dimension
        )
        return [item.embedding for item in resp.data]
