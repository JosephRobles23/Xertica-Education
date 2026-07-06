from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from enum import Enum

class ComponentType(str, Enum):
    LESSON = "lesson"
    VIDEO = "video"
    LAB = "lab"
    INFOGRAFIA = "infografia"
    QUIZ = "quiz"

class Component(BaseModel):
    id: Optional[UUID] = None
    modulo_id: UUID
    titulo: str
    tema: Optional[str] = None  # sub-tema sugerido, editable en Gate 0
    tipo: ComponentType
    orden: int = 0
