from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class Source(BaseModel):
    """Fuente de referencia. Route-céntrica desde Gate 1 (ADR-0007): pertenece a una
    Ruta; la citación a assets concretos es M:N vía `asset_sources`."""
    id: Optional[UUID] = None
    learning_path_id: Optional[UUID] = None
    url: Optional[str] = None  # Vía 1 (deep research); en uploads (Vía 2) es None
    title: Optional[str] = None
    tipo: Optional[str] = None  # "youtube" | "google_docs" | "blog_oficial" | "soporte_google"
    estado: Optional[str] = None  # "approved" | "requires-review" | "rejected"
    verificada_google: bool = False
    origin: str = "deep_research"  # "deep_research" (Vía 1) | "upload" (Vía 2 · ADR-0008)
    document_id: Optional[UUID] = None  # enlace al Document si origin == "upload"
