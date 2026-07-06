from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from enum import Enum


class ModuleType(str, Enum):
    INTRO = "intro"
    CAPSULA = "capsula"
    LAB = "lab"
    EVALUACION = "evaluacion"
    CIERRE = "cierre"


class Module(BaseModel):
    id: Optional[UUID] = None
    learning_path_id: UUID
    titulo: str
    descripcion: Optional[str] = None
    tipo: ModuleType
    orden: int = 0
    duracion_objetivo_min: Optional[int] = None
