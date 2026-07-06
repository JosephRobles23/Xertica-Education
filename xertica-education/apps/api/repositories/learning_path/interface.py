from abc import ABC, abstractmethod
from uuid import UUID
from typing import Dict, Any, List, Optional
from models.domain.learning_path import LearningPath

class LearningPathRepositoryInterface(ABC):
    @abstractmethod
    async def create(self, path: LearningPath) -> LearningPath:
        """Create a new learning path."""
        pass

    @abstractmethod
    async def get_by_id(self, path_id: UUID) -> Optional[LearningPath]:
        """Fetch a single learning path."""
        pass

    @abstractmethod
    async def list_all(self) -> List[LearningPath]:
        """List all learning paths."""
        pass

    @abstractmethod
    async def update(self, path_id: UUID, data: Dict[str, Any]) -> Optional[LearningPath]:
        """Modify learning path fields."""
        pass

    @abstractmethod
    async def delete(self, path_id: UUID) -> bool:
        """Delete a learning path."""
        pass
