from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Dict, Any
from models.domain.component import ComponentType

class Asset(BaseModel):
    id: Optional[UUID] = None
    componente_id: UUID
    tipo: ComponentType
    estado: str  # "draft", "generado", "en_revision", "aprobado"
    storage_path: Optional[str] = None
    word_budget: int
    provenance: Optional[Dict[str, Any]] = None
