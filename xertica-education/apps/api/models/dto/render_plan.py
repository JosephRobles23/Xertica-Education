from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID
from models.common import JobStatus
from models.dto.requests import StoryboardRequest

class RenderStage(BaseModel):
    stage_type: str
    status: JobStatus = JobStatus.QUEUED
    inputs: Dict[str, Any] = {}
    outputs: Dict[str, Any] = {}
    error: Optional[str] = None

class RenderPlan(BaseModel):
    job_id: UUID
    storyboard: StoryboardRequest
    stages: List[RenderStage]
    edit_decisions: Optional[Dict[str, Any]] = None
    final_url: Optional[str] = None
