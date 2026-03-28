from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.prediction import Prediction
from app.models.ml_model import MLModel
from app.schemas.prediction import PredictionCreate, PredictionUpdate
from app.core.exceptions import NotFoundException, ForbiddenException
from app.services.model_service import get_model_by_id


def _assert_model_ownership(model: MLModel, user_id: int) -> None:
    """
    Reusable ownership guard.
    Centralised so we don't repeat this check in every function.
    """
    if model.owner_id != user_id:
        raise ForbiddenException


def log_prediction(
    db: Session,
    model_id: int,
    payload: PredictionCreate,
    current_user_id: int,
) -> Prediction:
    """
    Log a new prediction for a given model.
    Verifies the model exists and belongs to the user.
    """
    model = get_model_by_id(db, model_id)
    _assert_model_ownership(model, current_user_id)

    prediction = Prediction(
        ml_model_id=model_id,
        input_data=payload.input_data,
        prediction_output=payload.prediction_output,
        confidence_score=payload.confidence_score,
        latency_ms=payload.latency_ms,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def get_predictions(
    db: Session,
    model_id: int,
    current_user_id: int,
    skip: int = 0,
    limit: int = 50,
    min_confidence: float | None = None,
    max_confidence: float | None = None,
    has_drift: bool | None = None,
    labelled: bool | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> tuple[list[Prediction], int]:
    """
    Retrieve paginated predictions for a model.
    Supports rich filtering — confidence range, drift flag,
    labelled status, and date range.
    """
    model = get_model_by_id(db, model_id)
    _assert_model_ownership(model, current_user_id)

    query = db.query(Prediction).filter(Prediction.ml_model_id == model_id)

    # Build filters dynamically
    filters = []

    if min_confidence is not None:
        filters.append(Prediction.confidence_score >= min_confidence)

    if max_confidence is not None:
        filters.append(Prediction.confidence_score <= max_confidence)

    if has_drift is True:
        filters.append(Prediction.drift_score > model.drift_threshold)

    if has_drift is False:
        filters.append(
            (Prediction.drift_score == None) |  # noqa: E711
            (Prediction.drift_score <= model.drift_threshold)
        )

    if labelled is True:
        filters.append(Prediction.actual_output != None)  # noqa: E711

    if labelled is False:
        filters.append(Prediction.actual_output == None)  # noqa: E711

    if start_date:
        filters.append(Prediction.created_at >= start_date)

    if end_date:
        filters.append(Prediction.created_at <= end_date)

    if filters:
        query = query.filter(and_(*filters))

    total = query.count()
    predictions = (
        query.order_by(Prediction.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return predictions, total


def get_prediction_by_id(
    db: Session,
    model_id: int,
    prediction_id: int,
    current_user_id: int,
) -> Prediction:
    """Fetch a single prediction. Verifies ownership via the parent model."""
    model = get_model_by_id(db, model_id)
    _assert_model_ownership(model, current_user_id)

    prediction = db.query(Prediction).filter(
        Prediction.id == prediction_id,
        Prediction.ml_model_id == model_id,
    ).first()

    if not prediction:
        raise NotFoundException

    return prediction


def label_prediction(
    db: Session,
    model_id: int,
    prediction_id: int,
    payload: PredictionUpdate,
    current_user_id: int,
) -> Prediction:
    """
    Attach ground truth label to an existing prediction.
    This is a PATCH — only actual_output is updated.
    Used after real-world outcomes are known.
    """
    prediction = get_prediction_by_id(db, model_id, prediction_id, current_user_id)
    prediction.actual_output = payload.actual_output
    db.commit()
    db.refresh(prediction)
    return prediction


def get_prediction_stats(
    db: Session,
    model_id: int,
    current_user_id: int,
) -> dict:
    """
    Aggregate stats across all predictions for a model.
    Used by the frontend dashboard and the background drift checker.
    """
    model = get_model_by_id(db, model_id)
    _assert_model_ownership(model, current_user_id)

    stats = db.query(
        func.count(Prediction.id).label("total"),
        func.avg(Prediction.confidence_score).label("avg_confidence"),
        func.min(Prediction.confidence_score).label("min_confidence"),
        func.max(Prediction.confidence_score).label("max_confidence"),
        func.avg(Prediction.latency_ms).label("avg_latency_ms"),
        func.max(Prediction.latency_ms).label("max_latency_ms"),
        func.avg(Prediction.drift_score).label("avg_drift_score"),
        func.max(Prediction.drift_score).label("max_drift_score"),
    ).filter(Prediction.ml_model_id == model_id).one()

    labelled_count = db.query(func.count(Prediction.id)).filter(
        Prediction.ml_model_id == model_id,
        Prediction.actual_output != None,  # noqa: E711
    ).scalar()

    drifted_count = db.query(func.count(Prediction.id)).filter(
        Prediction.ml_model_id == model_id,
        Prediction.drift_score > model.drift_threshold,
    ).scalar()

    return {
        "model_id": model_id,
        "total_predictions": stats.total or 0,
        "labelled_predictions": labelled_count or 0,
        "drifted_predictions": drifted_count or 0,
        "avg_confidence": round(stats.avg_confidence or 0, 4),
        "min_confidence": round(stats.min_confidence or 0, 4),
        "max_confidence": round(stats.max_confidence or 0, 4),
        "avg_latency_ms": round(stats.avg_latency_ms or 0, 2),
        "max_latency_ms": round(stats.max_latency_ms or 0, 2),
        "avg_drift_score": round(stats.avg_drift_score or 0, 4),
        "max_drift_score": round(stats.max_drift_score or 0, 4),
    }