"""Vinculación Source↔Módulo (ADR-0012). Asigna una fuente (típicamente un video de
Vía 1) al módulo que le corresponde en la ruta. No es una cita (eso vive en
`asset_sources`), sino una recomendación de asignación."""
from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class SourceModuleLink(BaseModel):
    id: Optional[UUID] = None
    learning_path_id: UUID
    source_id: UUID
    module_id: str
    score: Optional[float] = None
    origin: str = "llm"  # "heuristic" (frontend) | "llm" (linker on-demand)
    why: Optional[str] = None  # justificación transitoria del linker; NO se persiste
