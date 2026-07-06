from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime


class AssetVersion(BaseModel):
    id: Optional[UUID] = None
    asset_id: UUID
    version: int
    created_at: Optional[datetime] = None
