from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseRendererAdapter(ABC):
    @abstractmethod
    async def render_video(self, script: str, storyboard: Dict[str, Any]) -> str:
        """Invokes external video renderer (e.g. Veo) and returns public storage path/ID."""
        pass
