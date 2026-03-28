from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class PredictionCreate(BaseModel):
    """Log a new prediction."""
    input_data: dict[str, Any] = Field(
        ...,
        description="Feature inputs sent to the model",
        examples=[{"age": 34, "tenure_months": 12, "monthly_charge": 65.5}]
    )
    prediction_output: dict[str, Any] = Field(
        ...,
        description="Model output/prediction",
        examples=[{"label": "churn", "probability": 0.87}]
    )
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    latency_ms: Optional[float] = Field(None, ge=0.0)


class PredictionUpdate(BaseModel):
    """Attach ground truth label to an existing prediction."""
    actual_output: dict[str, Any] = Field(
        ...,
        examples=[{"label": "churn"}]
    )


class PredictionResponse(BaseModel):
    id: int
    input_data: dict[str, Any]
    prediction_output: dict[str, Any]
    actual_output: Optional[dict[str, Any]]
    confidence_score: Optional[float]
    drift_score: Optional[float]
    latency_ms: Optional[float]
    ml_model_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PredictionListResponse(BaseModel):
    """Paginated prediction list."""
    items: list[PredictionResponse]
    total: int
    skip: int
    limit: int


class PredictionStats(BaseModel):
    """Aggregated stats across all predictions for a model."""
    model_id: int
    total_predictions: int
    labelled_predictions: int
    drifted_predictions: int
    avg_confidence: float
    min_confidence: float
    max_confidence: float
    avg_latency_ms: float
    max_latency_ms: float
    avg_drift_score: float
    max_drift_score: float