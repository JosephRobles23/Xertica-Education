from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """Puerto de embeddings (ADR-0006). Intercambiable: mock ↔ OpenAI ↔ futuro."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Devuelve un vector por cada texto de entrada, en el mismo orden."""
        ...
