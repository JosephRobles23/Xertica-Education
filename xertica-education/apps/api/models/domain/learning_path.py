from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class LearningPath(BaseModel):
    id: Optional[UUID] = None
    titulo: str
    tema: str
    storytelling: Optional[str] = None
    industria: Optional[str] = None
    # INTERINO (ADR-0005): vocab de aprobación del frontend (ContentStatus).
    # Migrará a ciclo de vida ("borrador"|"en_produccion"|"publicada") cuando se
    # desacople RouteStatus del ContentStatus.
    estado: str = "borrador"  # "borrador" | "generado" | "en-revision" | "aprobado"
