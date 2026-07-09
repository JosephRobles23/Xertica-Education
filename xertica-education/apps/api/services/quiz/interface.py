from abc import ABC, abstractmethod
from uuid import UUID
from typing import Dict, Any

class QuizServiceInterface(ABC):
    @abstractmethod
    async def generate_quiz(
        self,
        route_id: UUID,
        module_id: str,
        module_name: str,
        module_description: str,
        company_name: str,
        user_prompt: str | None = None
    ) -> Dict[str, Any]:
        """
        Generates a quiz based on the module details and context.
        Returns a dictionary containing the questions, pdfUrl, and txtUrl.
        """
        pass
