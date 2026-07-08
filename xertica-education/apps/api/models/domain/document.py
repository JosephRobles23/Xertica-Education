"""Documento subido por el usuario (Vía 2 · ADR-0008)."""
from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class Document(BaseModel):
    id: Optional[UUID] = None
    learning_path_id: UUID
    storage_path: str
    filename: str
    mime: Optional[str] = None
    use_as_source: bool = False  # doble rol: contexto de personalización vs fuente de la KB
