from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class Source(BaseModel):
    id: Optional[UUID] = None
    asset_id: Optional[UUID] = None  # se asigna al citar un asset; en sourcing/Gate 1 aún no existe
    url: str
    title: Optional[str] = None
    tipo: Optional[str] = None  # "youtube" | "google_docs" | "blog_oficial" | "soporte_google"
    verificada_google: bool = False
