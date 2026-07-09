from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional, List
from models.dto.requests import StoryboardRequest
from models.dto.responses import VideoJobResponse
from services.kb.interface import KnowledgeBaseInterface

class VideoServiceInterface(ABC):
    @abstractmethod
    async def generate_video(
        self,
        component_id: Optional[UUID] = None,
        custom_storyboard: Optional[StoryboardRequest] = None,
        use_mock: bool = False
    ) -> UUID:
        """Starts video generation job, returns job_id."""
        pass

    @abstractmethod
    async def generate_storyboard(
        self,
        route_id: UUID,
        module_id: UUID,
        component_kind: str = "video",
        component_id: Optional[UUID] = None,
        k: int = 8,
        kb: Optional[KnowledgeBaseInterface] = None,
    ) -> dict:
        """Generates a KB-grounded storyboard for the given Render Target.

        Pure: consults the KB, calls the scriptwriter LLM, returns JSON. Does NOT
        persist an Asset nor create a Job (ADR-0015). Returns a dict with shape:
        ``{"storyboard": <StoryboardRequest-as-dict>, "grounding": GroundingInfo}``.
        """
        pass

    @abstractmethod
    async def get_video_job_status(self, job_id: UUID) -> Optional[VideoJobResponse]:
        """Returns the job status details."""
        pass

    @abstractmethod
    async def segment_video(self, video_url: str) -> List[dict]:
        """Ingests an existing video and segments it into timestamped sub-topics."""
        pass
