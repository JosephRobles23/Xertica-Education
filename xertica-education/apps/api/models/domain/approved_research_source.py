from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ApprovedResearchSource(BaseModel):
    id: Optional[UUID] = None
    route_id: UUID
    module_id: Optional[str] = None
    tool_name: Optional[str] = None
    title: str
    url: str
    domain: str
    source_type: str = "documentation"
    is_verified: bool = False
    approval_source: Literal["automatic", "manual"]
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    status: Literal["approved", "rejected"] = "approved"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
