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
    use_as_source: bool = True  # deprecado (ADR-0013): todo upload entra a la KB por default
    parsed_md: Optional[str] = None  # markdown verbatim; se llena en el upload (parse-at-upload · ADR-0013)
