from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class Source(BaseModel):
    id: Optional[UUID] = None
    url: str
    title: str
    tipo: str  # e.g., "youtube", "google_docs", "blog_oficial"
    verified: bool
