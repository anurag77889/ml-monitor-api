from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.alert import (
    AlertListResponse,
    AlertResponse,
    AlertStats,
    BulkResolveResponse,
)
from app.services.alert_service import (
    get_alerts,
    get_alert_by_id,
    resolve_alert,
    resolve_all_alerts,
    get_alert_stats,
)

router = APIRouter(
    prefix="/models/{model_id}/alerts",
    tags=["Alerts"],
)


@router.get("/", response_model=AlertListResponse)
def list_alerts_route(
    model_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    severity: Optional[str] = Query(
        default=None,
        pattern="^(low|medium|high|critical)$",
        description="Filter by severity level"
    ),
    alert_type: Optional[str] = Query(
        default=None,
        description="Filter by type e.g. drift_detected, low_confidence"
    ),
    is_resolved: Optional[bool] = Query(
        default=None,
        description="true = resolved only, false = unresolved only"
    ),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List alerts for a model.

    - **severity** — filter by low / medium / high / critical
    - **alert_type** — filter by drift_detected / low_confidence / high_latency
    - **is_resolved** — false returns only active unresolved alerts
    - **start_date / end_date** — ISO 8601 datetime range
    """
    alerts, total = get_alerts(
        db,
        model_id=model_id,
        current_user_id=current_user.id,
        skip=skip,
        limit=limit,
        severity=severity,
        alert_type=alert_type,
        is_resolved=is_resolved,
        start_date=start_date,
        end_date=end_date,
    )
    return AlertListResponse(items=alerts, total=total, skip=skip, limit=limit)


@router.get("/stats", response_model=AlertStats)
def alert_stats_route(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get alert counts broken down by severity and type.
    Use this for dashboard summary cards.
    """
    return get_alert_stats(db, model_id, current_user.id)


@router.patch("/resolve-all", response_model=BulkResolveResponse)
def resolve_all_alerts_route(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk resolve all unresolved alerts for a model.
    Frontend 'acknowledge all' button calls this.
    """
    count = resolve_all_alerts(db, model_id, current_user.id)
    return BulkResolveResponse(
        resolved_count=count,
        message=f"Successfully resolved {count} alert(s).",
    )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert_route(
    model_id: int,
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch a single alert by ID."""
    return get_alert_by_id(db, model_id, alert_id, current_user.id)


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert_route(
    model_id: int,
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a single alert as resolved.
    Idempotent — safe to call multiple times.
    """
    return resolve_alert(db, model_id, alert_id, current_user.id)