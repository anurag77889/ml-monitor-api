import logging
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.alert import Alert
from app.models.ml_model import MLModel

logger = logging.getLogger(__name__)


def _assert_model_ownership(db: Session,
                            model_id: int,
                            user_id: int) -> MLModel:
    """
    Verify the model exists and belongs to the user.
    Returns the model if valid, raises otherwise.
    """
    model = db.query(MLModel).filter(MLModel.id == model_id).first()
    if not model:
        raise NotFoundException
    if model.owner_id != user_id:
        raise ForbiddenException
    return model


def get_alerts(
    db: Session,
    model_id: int,
    current_user_id: int,
    skip: int = 0,
    limit: int = 50,
    severity: str | None = None,
    alert_type: str | None = None,
    is_resolved: bool | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> tuple[list[Alert], int]:
    """
    Fetch paginated alerts for a model with optional filters.
    """
    _assert_model_ownership(db, model_id, current_user_id)

    query = db.query(Alert).filter(Alert.ml_model_id == model_id)

    if severity:
        query = query.filter(Alert.severity == severity)

    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)

    if is_resolved is True:
        query = query.filter(Alert.is_resolved == True)   # noqa: E712

    if is_resolved is False:
        query = query.filter(Alert.is_resolved == False)  # noqa: E712

    if start_date:
        query = query.filter(Alert.created_at >= start_date)

    if end_date:
        query = query.filter(Alert.created_at <= end_date)

    total = query.count()
    alerts = (
        query
        .order_by(Alert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return alerts, total


def get_alert_by_id(
    db: Session,
    model_id: int,
    alert_id: int,
    current_user_id: int,
) -> Alert:
    """Fetch a single alert by ID. Verifies ownership."""
    _assert_model_ownership(db, model_id, current_user_id)

    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.ml_model_id == model_id,
    ).first()

    if not alert:
        raise NotFoundException

    return alert


def resolve_alert(
    db: Session,
    model_id: int,
    alert_id: int,
    current_user_id: int,
) -> Alert:
    """
    Mark an alert as resolved.
    Sets is_resolved=True and records resolved_at timestamp.
    Idempotent — resolving an already-resolved alert is a no-op.
    """
    alert = get_alert_by_id(db, model_id, alert_id, current_user_id)

    if alert.is_resolved:
        # Already resolved — return as-is, don't error
        return alert

    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)

    logger.info(
        f"[AlertService] Resolved alert_id={alert_id} "
        f"model_id={model_id} type={alert.alert_type}"
    )
    return alert


def resolve_all_alerts(
    db: Session,
    model_id: int,
    current_user_id: int,
) -> int:
    """
    Bulk resolve all unresolved alerts for a model.
    Returns count of alerts resolved.
    Useful for 'acknowledge all' button on the frontend.
    """
    _assert_model_ownership(db, model_id, current_user_id)

    now = datetime.utcnow()
    updated = db.query(Alert).filter(
        Alert.ml_model_id == model_id,
        Alert.is_resolved == False,  # noqa: E712
    ).all()

    count = len(updated)
    for alert in updated:
        alert.is_resolved = True
        alert.resolved_at = now

    db.commit()

    logger.info(
        f"[AlertService] Bulk resolved {count} alerts for model_id={model_id}"
    )
    return count


def get_alert_stats(
    db: Session,
    model_id: int,
    current_user_id: int,
) -> dict:
    """
    Aggregate alert counts broken down by:
    - severity (low / medium / high / critical)
    - alert type (drift_detected / low_confidence / high_latency)
    - resolved vs unresolved

    Used for dashboard summary cards.
    """
    _assert_model_ownership(db, model_id, current_user_id)

    # Total and resolved counts
    total_alerts: int = int(
        db.query(func.count(Alert.id))
        .filter(Alert.ml_model_id == model_id)
        .scalar() or 0
    )
    unresolved_alerts: int = int(
        db.query(func.count(Alert.id))
        .filter(
            Alert.ml_model_id == model_id,
            Alert.is_resolved == False,  # noqa: E712
        )
        .scalar()
        or 0
    )

    # Breakdown by severity
    severity_rows = (
        db.query(Alert.severity, func.count(Alert.id).label("total"))
        .filter(Alert.ml_model_id == model_id)
        .group_by(Alert.severity)
        .all()
    )
    by_severity = {row.severity: int(row.total) for row in severity_rows}

    # Breakdown by type
    type_rows = (
        db.query(Alert.alert_type, func.count(Alert.id).label("total"))
        .filter(Alert.ml_model_id == model_id)
        .group_by(Alert.alert_type)
        .all()
    )
    by_type = {row.alert_type: int(row.total) for row in type_rows}

    return {
        "model_id": model_id,
        "total_alerts": total_alerts,
        "unresolved_alerts": unresolved_alerts,
        "resolved_alerts": total_alerts - unresolved_alerts,
        "by_severity": {
            "low": by_severity.get("low", 0),
            "medium": by_severity.get("medium", 0),
            "high": by_severity.get("high", 0),
            "critical": by_severity.get("critical", 0),
        },
        "by_type": {
            "drift_detected": by_type.get("drift_detected", 0),
            "low_confidence": by_type.get("low_confidence", 0),
            "high_latency": by_type.get("high_latency", 0),
        },
    }
