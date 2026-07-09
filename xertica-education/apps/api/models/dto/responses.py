from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from models.common import JobStatus

class JobResponse(BaseModel):
    id: UUID
    type: str
    status: JobStatus
    progress: int
    created_at: datetime
    updated_at: datetime
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class VideoJobResult(BaseModel):
    video_url: str
    duration_seconds: float
    cost_usd: float

class VideoJobResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    progress: int
    result: Optional[VideoJobResult] = None
    error: Optional[str] = None


class GroundingInfo(BaseModel):
    """Provenance for a KB-grounded storyboard (ADR-0015). Returned alongside the
    storyboard so the human reviewing the script can see which chunks grounded it.
    Defer `asset_sources` persistence (ADR-0007) to a later ticket; this block is
    exposed now so the data exists when that ticket lands."""
    query: str
    k: int
    chunks: list  # list[GroundedChunk] (kept loose to avoid a domain↔dto cycle)


class StoryboardResponse(BaseModel):
    """Output of `POST /videos/storyboard` (ADR-0015).

    The `storyboard` field is a `StoryboardRequest` so the frontend can pass it
    (edited or not) straight back into `POST /videos/generate` with zero reshaping.
    `grounding` carries the KB provenance that produced it.
    """
    storyboard: dict
    grounding: GroundingInfo

