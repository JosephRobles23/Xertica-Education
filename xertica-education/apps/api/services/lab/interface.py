from abc import ABC, abstractmethod
from uuid import UUID
from typing import Any, Dict, List


class LabServiceInterface(ABC):
    @abstractmethod
    async def generate_lab(
        self,
        route_id: UUID,
        module_id: str,
        route_name: str,
        route_objective: str,
        module_name: str,
        module_description: str,
        module_objective: str,
        company_name: str,
        customer_context: Dict[str, Any],
        approved_sources: List[Dict[str, Any]],
        user_prompt: str | None = None,
    ) -> Dict[str, Any]:
        ...
