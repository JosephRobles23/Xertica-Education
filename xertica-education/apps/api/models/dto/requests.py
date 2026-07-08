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

class KbQueryRequest(BaseModel):
    """Consulta grounded a la KB (ADR-0006 §6). Aislada por ruta."""
    learning_path_id: UUID
    query: str
    k: int = 8
    verified_only: bool = False
