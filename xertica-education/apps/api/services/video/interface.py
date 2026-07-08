from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional, List
from models.dto.requests import StoryboardRequest
from models.dto.responses import VideoJobResponse

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
    async def get_video_job_status(self, job_id: UUID) -> Optional[VideoJobResponse]:
        """Returns the job status details."""
        pass

    @abstractmethod
    async def segment_video(self, video_url: str) -> List[dict]:
        """Ingests an existing video and segments it into timestamped sub-topics."""
        pass

