from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MLModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    version: str = Field(..., max_length=50)
    description: Optional[str] = None
    model_type: str = Field(..., description="e.g. classification, regression, nlp")
    drift_threshold: float = Field(default=0.05, ge=0.0, le=1.0)


class MLModelUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    version: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(production|staging|retired)$")
    drift_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class MLModelResponse(BaseModel):
    id: int
    name: str
    version: str
    description: Optional[str]
    model_type: str
    status: str
    drift_threshold: float
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MLModelListResponse(BaseModel):
    """Paginated list response — always wrap lists like this in production."""
    items: list[MLModelResponse]
    total: int
    skip: int
    limit: int


class MLModelSummary(BaseModel):
    """Stats summary for a single model."""
    model_id: int
    model_name: str
    status: str
    total_predictions: int
    avg_confidence: float
    avg_latency_ms: float
    avg_drift_score: float
    unresolved_alerts: int
    latest_prediction_at: Optional[datetime]