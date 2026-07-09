from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Dict, Any, Literal

AspectRatio = Literal["vertical", "horizontal", "square", "auto"]

class InfographicServiceInterface(ABC):
    @abstractmethod
    async def generate_infographic(
        self,
        component_id: UUID,
        sources: List[Dict[str, Any]],
        company_name: str,
        word_budget: int,
        user_prompt: str | None = None,
        aspect_ratio: AspectRatio = "auto",
        route_name: str | None = None
    ) -> Dict[str, Any]:
        """
        Generates infographic PNG (using gpt-image-2 via OpenAI API Key) and wraps it as a single-page PDF.
        Registers the assets, stores them, and returns metadata.
        """
        pass

