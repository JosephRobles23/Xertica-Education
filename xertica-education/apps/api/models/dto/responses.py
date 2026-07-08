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

