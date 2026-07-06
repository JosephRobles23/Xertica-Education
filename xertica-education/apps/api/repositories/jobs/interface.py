from abc import ABC, abstractmethod
from uuid import UUID
from typing import Dict, Any, Optional

class JobRepositoryInterface(ABC):
    @abstractmethod
    async def create(self, job_id: UUID, task_name: str) -> Dict[str, Any]:
        """Create a new job row."""
        pass

    @abstractmethod
    async def get_by_id(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieve a job by ID."""
        pass

    @abstractmethod
    async def update(self, job_id: UUID, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update fields on a job row."""
        pass
