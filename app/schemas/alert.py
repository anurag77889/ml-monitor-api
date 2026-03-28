from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    """Used internally by background tasks."""
    alert_type: str
    message: str
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    triggered_value: Optional[float] = None
    ml_model_id: int


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    message: str
    severity: str
    triggered_value: Optional[float]
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime]
    ml_model_id: int

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """Paginated alert list."""
    items: list[AlertResponse]
    total: int
    skip: int
    limit: int


class AlertStats(BaseModel):
    """Alert counts broken down by severity and type."""
    model_id: int
    total_alerts: int
    unresolved_alerts: int
    resolved_alerts: int
    by_severity: dict[str, int]
    by_type: dict[str, int]


class BulkResolveResponse(BaseModel):
    """Response for bulk resolve operation."""
    resolved_count: int
    message: str