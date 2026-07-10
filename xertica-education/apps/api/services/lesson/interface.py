from abc import ABC, abstractmethod
from uuid import UUID
from typing import Dict, Any

class LessonServiceInterface(ABC):
    @abstractmethod
    async def generate_lesson(
        self,
        route_id: UUID,
        module_id: str,
        module_name: str,
        module_description: str,
        company_name: str,
        user_prompt: str | None = None
    ) -> Dict[str, Any]:
        pass
