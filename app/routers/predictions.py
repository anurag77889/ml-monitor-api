from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.prediction import (PredictionCreate, PredictionListResponse,
                                    PredictionResponse, PredictionStats,
                                    PredictionUpdate)
from app.services.prediction_service import (get_prediction_by_id,
                                             get_prediction_stats,
                                             get_predictions, label_prediction,
                                             log_prediction)

router = APIRouter(
    prefix="/models/{model_id}/predictions",
    tags=["Predictions"],
)


@router.post("/", response_model=PredictionResponse, status_code=201)
def log_prediction_route(
    model_id: int,
    payload: PredictionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Log a new prediction for a model.
    Call this every time your ML model makes an inference.
    """
    return log_prediction(db, model_id, payload, current_user.id)


@router.get("/", response_model=PredictionListResponse)
def list_predictions_route(
    model_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    min_confidence: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    max_confidence: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    has_drift: Optional[bool] = Query(default=None),
    labelled: Optional[bool] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List predictions for a model with rich filtering.

    - **min_confidence / max_confidence** — filter by confidence range
    - **has_drift** — `true` returns only drifted predictions
    - **labelled** — `true` returns only labelled predictions
    - **start_date / end_date** — ISO 8601 datetime range filter
    """
    predictions, total = get_predictions(
        db,
        model_id=model_id,
        current_user_id=current_user.id,
        skip=skip,
        limit=limit,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        has_drift=has_drift,
        labelled=labelled,
        start_date=start_date,
        end_date=end_date,
    )
    return PredictionListResponse(
        items=predictions,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=PredictionStats)
def prediction_stats_route(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get aggregated stats for all predictions on this model.
    Useful for dashboard cards — confidence, latency, drift overview.
    """
    return get_prediction_stats(db, model_id, current_user.id)


@router.get("/{prediction_id}", response_model=PredictionResponse)
def get_prediction_route(
    model_id: int,
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch a single prediction by ID."""
    return get_prediction_by_id(db, model_id, prediction_id, current_user.id)


@router.patch("/{prediction_id}/label", response_model=PredictionResponse)
def label_prediction_route(
    model_id: int,
    prediction_id: int,
    payload: PredictionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Attach a ground truth label to an existing prediction.
    Call this when real-world outcomes become known.
    """
    return label_prediction(
        db, model_id, prediction_id, payload, current_user.id
    )
