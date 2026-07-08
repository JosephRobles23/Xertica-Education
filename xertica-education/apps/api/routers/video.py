from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from config.dependencies import get_video_service
from services.video.service import VideoService
from models.dto.requests import GenerateVideoRequest
from models.dto.responses import VideoJobResponse
from typing import Dict

router = APIRouter(prefix="/videos", tags=["videos"])

@router.post("/generate", response_model=Dict[str, UUID])
async def generate_video(
    request: GenerateVideoRequest,
    video_service: VideoService = Depends(get_video_service)
):
    """
    Triggers video rendering asynchronously.
    """
    job_id = await video_service.generate_video(
        component_id=request.component_id,
        custom_storyboard=request.custom_storyboard,
        use_mock=request.use_mock
    )
    return {"job_id": job_id}

@router.get("/jobs/{job_id}", response_model=VideoJobResponse)
async def get_video_job(
    job_id: UUID,
    video_service: VideoService = Depends(get_video_service)
):
    """
    Retrieves the status of a video rendering job.
    """
    status = await video_service.get_video_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Video rendering job not found")
    return status

from pydantic import BaseModel

class SegmentVideoRequest(BaseModel):
    video_url: str

@router.post("/preview")
async def preview_video(
    request: GenerateVideoRequest,
    video_service: VideoService = Depends(get_video_service)
):
    """
    Generates a quick storyboard preview without full rendering.
    """
    # Placeholder for preview logic
    return {"message": "Preview generated successfully.", "scenes_count": 0}

@router.post("/segment")
async def segment_existing_video(
    request: SegmentVideoRequest,
    video_service: VideoService = Depends(get_video_service)
):
    """
    Segment an existing video into timestamped chunks.
    """
    segments = await video_service.segment_video(request.video_url)
    return {"segments": segments}

