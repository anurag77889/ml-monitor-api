import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.prediction import Prediction
from app.models.alert import Alert

logger = logging.getLogger(__name__)


def _check_low_confidence_alert(
    db: Session,
    model_id: int,
    avg_confidence: float,
    threshold: float = 0.6,
) -> None:
    """
    Fire a low confidence alert if the hourly average
    confidence drops below the threshold.
    Deduplicates — only one alert per hour per model.
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    # Check if we already fired this alert in the last hour
    existing = db.query(Alert).filter(
        Alert.ml_model_id == model_id,
        Alert.alert_type == "low_confidence",
        Alert.created_at >= one_hour_ago,
    ).first()

    if existing:
        return  # Already alerted this hour

    alert = Alert(
        alert_type="low_confidence",
        message=(
            f"Average confidence score dropped to {avg_confidence:.4f} "
            f"over the last hour, below threshold of {threshold:.2f}."
        ),
        severity="high" if avg_confidence < 0.4 else "medium",
        triggered_value=avg_confidence,
        ml_model_id=model_id,
    )
    db.add(alert)
    db.commit()
    logger.warning(
        f"[MetricAggregator] Low confidence alert: "
        f"model_id={model_id} avg_confidence={avg_confidence}"
    )


def _check_high_latency_alert(
    db: Session,
    model_id: int,
    avg_latency_ms: float,
    threshold_ms: float = 500.0,
) -> None:
    """
    Fire a high latency alert if hourly average latency
    exceeds threshold. Deduplicates per hour.
    """
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    existing = db.query(Alert).filter(
        Alert.ml_model_id == model_id,
        Alert.alert_type == "high_latency",
        Alert.created_at >= one_hour_ago,
    ).first()

    if existing:
        return

    alert = Alert(
        alert_type="high_latency",
        message=(
            f"Average latency {avg_latency_ms:.1f}ms exceeds "
            f"threshold of {threshold_ms:.0f}ms over the last hour."
        ),
        severity="critical" if avg_latency_ms > 1000 else "high",
        triggered_value=avg_latency_ms,
        ml_model_id=model_id,
    )
    db.add(alert)
    db.commit()
    logger.warning(
        f"[MetricAggregator] High latency alert: "
        f"model_id={model_id} avg_latency={avg_latency_ms}ms"
    )


def run_metric_aggregation(
    db: Session,
    model_id: int,
) -> dict:
    """
    Aggregate metrics for the last hour for a given model.
    Called as a background task after every prediction.

    Computes:
    - prediction volume
    - avg / min / max confidence
    - avg / max latency
    - drift rate (% of predictions with drift)

    Then checks alert conditions.
    Returns the computed metrics dict for logging.
    """
    try:
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        stats = db.query(
            func.count(Prediction.id).label("total"),
            func.avg(Prediction.confidence_score).label("avg_confidence"),
            func.min(Prediction.confidence_score).label("min_confidence"),
            func.max(Prediction.confidence_score).label("max_confidence"),
            func.avg(Prediction.latency_ms).label("avg_latency"),
            func.max(Prediction.latency_ms).label("max_latency"),
        ).filter(
            Prediction.ml_model_id == model_id,
            Prediction.created_at >= one_hour_ago,
        ).one()

        if not stats.total:
            return {}

        # Count drifted predictions in the window
        drifted: int = db.query(func.count(Prediction.id)).filter(
            Prediction.ml_model_id == model_id,
            Prediction.created_at >= one_hour_ago,
            Prediction.drift_score != None,  # noqa: E711
            Prediction.drift_score > 0.05,
        ).scalar() or 0


        drift_rate = round(drifted / stats.total, 4) if stats.total else 0.0

        metrics = {
            "model_id": model_id,
            "window": "1h",
            "prediction_count": stats.total,
            "avg_confidence": round(stats.avg_confidence or 0, 4),
            "min_confidence": round(stats.min_confidence or 0, 4),
            "max_confidence": round(stats.max_confidence or 0, 4),
            "avg_latency_ms": round(stats.avg_latency or 0, 2),
            "max_latency_ms": round(stats.max_latency or 0, 2),
            "drift_rate": drift_rate,
        }

        logger.info(f"[MetricAggregator] model_id={model_id} metrics={metrics}")

        # Check alert conditions
        if stats.avg_confidence and stats.avg_confidence < 0.6:
            _check_low_confidence_alert(db, model_id, stats.avg_confidence)

        if stats.avg_latency and stats.avg_latency > 500:
            _check_high_latency_alert(db, model_id, stats.avg_latency)

        return metrics

    except Exception as e:
        logger.error(f"[MetricAggregator] Failed for model_id={model_id}: {e}")
        db.rollback()
        return {}