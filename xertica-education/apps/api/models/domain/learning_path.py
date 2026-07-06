from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class LearningPath(BaseModel):
    id: Optional[UUID] = None
    titulo: str
    tema: str
    industria: Optional[str] = None
    estado: str = "borrador"  # "borrador", "en_produccion", "publicada"
