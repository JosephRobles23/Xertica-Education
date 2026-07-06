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
    tipo: ComponentType
    orden: int
