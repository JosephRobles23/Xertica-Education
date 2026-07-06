from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from uuid import UUID

class CreateLearningPathRequest(BaseModel):
    titulo: str
    tema: str
    brief: Optional[str] = None
    document_urls: Optional[List[HttpUrl]] = None

class CreateJobRequest(BaseModel):
    type: str  # e.g., "video_generation", "sourcing"
    payload: dict
