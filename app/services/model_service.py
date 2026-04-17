from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.alert import Alert
from app.models.ml_model import MLModel
from app.models.prediction import Prediction
from app.schemas.ml_model import MLModelCreate, MLModelUpdate


def create_model(
    db: Session, payload: MLModelCreate, owner_id: int
) -> MLModel:
    """Register a new ML model under the authenticated user."""
    model = MLModel(**payload.model_dump(), owner_id=owner_id)
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def get_model_by_id(db: Session, model_id: int) -> MLModel:
    """Fetch a single model by ID. Raises 404 if not found."""
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise NotFoundException
    return model


def get_models_by_owner(
    db: Session,
    owner_id: int,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    model_type: str | None = None,
) -> tuple[list[MLModel], int]:
    """
    List all models for a user with optional filters.
    Returns (models, total_count) for pagination.
    """
    query = db.query(MLModel).filter(MLModel.owner_id == owner_id)

    # Optional filters
    if status:
        query = query.filter(MLModel.status == status)
    if model_type:
        query = query.filter(MLModel.model_type == model_type)

    total = query.count()
    models = (
        query.order_by(MLModel.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return models, total


def update_model(
    db: Session,
    model_id: int,
    payload: MLModelUpdate,
    current_user_id: int,
) -> MLModel:
    """
    Update a model's fields.
    Only the owner can update their model.
    Only provided fields are updated (PATCH semantics).
    """
    model = get_model_by_id(db, model_id)

    if model.owner_id != current_user_id:
        raise ForbiddenException

    # Only update fields that were explicitly provided
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model, field, value)

    db.commit()
    db.refresh(model)
    return model


def delete_model(db: Session, model_id: int, current_user_id: int) -> None:
    """
    Delete a model and all its predictions/alerts (cascade).
    Only the owner can delete.
    """
    model = get_model_by_id(db, model_id)

    if model.owner_id != current_user_id:
        raise ForbiddenException

    db.delete(model)
    db.commit()


def get_model_summary(
    db: Session, model_id: int, current_user_id: int
) -> dict:
    """
    Returns a stats summary for a model:
    total predictions, avg confidence, avg latency,
    unresolved alerts, latest drift score.
    """
    model = get_model_by_id(db, model_id)

    if model.owner_id != current_user_id:
        raise ForbiddenException

    stats = db.query(
        func.count(Prediction.id).label("total_predictions"),
        func.avg(Prediction.confidence_score).label("avg_confidence"),
        func.avg(Prediction.latency_ms).label("avg_latency_ms"),
        func.avg(Prediction.drift_score).label("avg_drift_score"),
    ).filter(Prediction.ml_model_id == model_id).one()

    unresolved_alerts = db.query(func.count(Alert.id)).filter(
        Alert.ml_model_id == model_id,
        Alert.is_resolved == False,  # noqa: E712
    ).scalar()

    latest_prediction = (
        db.query(Prediction)
        .filter(Prediction.ml_model_id == model_id)
        .order_by(Prediction.created_at.desc())
        .first()
    )

    return {
        "model_id": model_id,
        "model_name": model.name,
        "status": model.status,
        "total_predictions": stats.total_predictions or 0,
        "avg_confidence": round(stats.avg_confidence or 0, 4),
        "avg_latency_ms": round(stats.avg_latency_ms or 0, 2),
        "avg_drift_score": round(stats.avg_drift_score or 0, 4),
        "unresolved_alerts": unresolved_alerts or 0,
        "latest_prediction_at": (
            latest_prediction.created_at if latest_prediction else None
        ),
    }
