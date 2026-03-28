from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.ml_model import (
    MLModelCreate,
    MLModelUpdate,
    MLModelResponse,
    MLModelListResponse,
    MLModelSummary,
)
from app.services.model_service import (
    create_model,
    get_model_by_id,
    get_models_by_owner,
    update_model,
    delete_model,
    get_model_summary,
)

router = APIRouter(prefix="/models", tags=["ML Models"])


@router.post("/", response_model=MLModelResponse, status_code=201)
def register_model(
    payload: MLModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new ML model. Authenticated users only."""
    return create_model(db, payload, owner_id=current_user.id)


@router.get("/", response_model=MLModelListResponse)
def list_models(
    skip: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    status: str | None = Query(default=None, description="Filter by status"),
    model_type: str | None = Query(default=None, description="Filter by type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all models owned by the current user. Supports filtering & pagination."""
    models, total = get_models_by_owner(
        db,
        owner_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status,
        model_type=model_type,
    )
    return MLModelListResponse(items=models, total=total, skip=skip, limit=limit)


@router.get("/{model_id}", response_model=MLModelResponse)
def get_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single model by ID."""
    model = get_model_by_id(db, model_id)
    return model


@router.patch("/{model_id}", response_model=MLModelResponse)
def update_model_route(
    model_id: int,
    payload: MLModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Partially update a model.
    PATCH — only send the fields you want to change.
    Only the owner can update.
    """
    return update_model(db, model_id, payload, current_user_id=current_user.id)


@router.delete("/{model_id}", status_code=204)
def delete_model_route(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a model and all associated predictions and alerts.
    Only the owner can delete. Returns 204 No Content on success.
    """
    delete_model(db, model_id, current_user_id=current_user.id)


@router.get("/{model_id}/summary", response_model=MLModelSummary)
def model_summary(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get aggregated stats for a model:
    prediction count, avg confidence, avg latency, drift, alerts.
    """
    return get_model_summary(db, model_id, current_user_id=current_user.id)