from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseLLMAdapter(ABC):
    @abstractmethod
    async def chat_completion(self, role: str, prompt: str, **kwargs) -> str:
        """Sends a completion request mapped to a specific system role."""
        pass
