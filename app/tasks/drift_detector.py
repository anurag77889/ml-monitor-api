import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.ml_model import MLModel
from app.models.prediction import Prediction

logger = logging.getLogger(__name__)


def _compute_drift_score(
    current_value: float,
    baseline_mean: float,
    baseline_std: float,
) -> float:
    """
    Compute a normalised drift score using Z-score method.

    Z-score = |current - baseline_mean| / baseline_std

    We normalise it to a 0–1 range using a sigmoid-like compression.
    Score close to 0 = stable. Score close to 1 = high drift.
    """
    if baseline_std == 0:
        return 0.0
    z_score = abs(current_value - baseline_mean) / baseline_std
    # Compress z_score to 0–1 range (z=3 maps to ~0.75, z=5 maps to ~0.91)
    drift = z_score / (z_score + 2)
    return round(min(drift, 1.0), 4)


def _get_baseline_stats(
    db: Session,
    model_id: int,
    exclude_prediction_id: int,
    window: int = 100,
) -> tuple[float, float]:
    """
    Compute baseline mean and std of confidence scores
    from the last `window` predictions (excluding the current one).

    This is our reference distribution for drift comparison.
    """
    result = db.query(
        func.avg(Prediction.confidence_score).label("mean"),
        func.avg(
            Prediction.confidence_score * Prediction.confidence_score
        ).label("mean_sq"),
    ).filter(
        Prediction.ml_model_id == model_id,
        Prediction.id != exclude_prediction_id,
        Prediction.confidence_score != None,  # noqa: E711
    ).order_by(
        Prediction.created_at.desc()
    ).limit(window).one()

    mean = result.mean or 0.0
    mean_sq = result.mean_sq or 0.0

    # std = sqrt(E[X²] - E[X]²)
    variance = max(mean_sq - (mean ** 2), 0)
    std = variance ** 0.5

    return mean, std


def _create_drift_alert(
    db: Session,
    model: MLModel,
    prediction_id: int,
    drift_score: float,
) -> None:
    """Create an alert when drift exceeds the model's threshold."""
    severity = "medium"
    if drift_score >= 0.75:
        severity = "critical"
    elif drift_score >= 0.5:
        severity = "high"
    elif drift_score >= 0.25:
        severity = "medium"
    else:
        severity = "low"

    alert = Alert(
        alert_type="drift_detected",
        message=(
            f"Drift detected on model '{model.name}' v{model.version}. "
            f"Drift score {drift_score:.4f} exceeds threshold "
            f"{model.drift_threshold:.4f}. "
            f"Prediction ID: {prediction_id}."
        ),
        severity=severity,
        triggered_value=drift_score,
        ml_model_id=model.id,
    )
    db.add(alert)
    db.commit()
    logger.warning(
        f"[DriftAlert] model_id={model.id} prediction_id={prediction_id} "
        f"drift={drift_score} severity={severity}"
    )


def run_drift_detection(
    db: Session,
    prediction_id: int,
    model_id: int,
) -> None:
    """
    Main drift detection task.
    Called as a background task after every prediction is logged.

    Steps:
    1. Load the prediction
    2. Check we have enough history (min 10 predictions for baseline)
    3. Compute baseline stats from recent predictions
    4. Compute drift score for this prediction
    5. Update prediction.drift_score in DB
    6. Fire alert if drift > threshold
    """
    try:
        prediction = db.query(Prediction).filter(
            Prediction.id == prediction_id
        ).first()

        if not prediction or prediction.confidence_score is None:
            logger.info(
                f"[DriftDetector] Skipping prediction {prediction_id} "
                f"— no confidence score."
            )
            return

        model = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            return

        # Need at least 10 prior predictions to establish a baseline
        prior_count = db.query(func.count(Prediction.id)).filter(
            Prediction.ml_model_id == model_id,
            Prediction.id != prediction_id,
            Prediction.confidence_score != None,  # noqa: E711
        ).scalar()

        if prior_count < 10:
            logger.info(
                f"[DriftDetector] model_id={model_id} — only {prior_count} "
                f"prior predictions, need 10 to establish baseline. Skipping."
            )
            return

        # Compute baseline from last 100 predictions
        baseline_mean, baseline_std = _get_baseline_stats(
            db, model_id, exclude_prediction_id=prediction_id
        )

        drift_score = _compute_drift_score(
            current_value=prediction.confidence_score,
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
        )

        # Persist the drift score on the prediction
        prediction.drift_score = drift_score
        db.commit()

        logger.info(
            f"[DriftDetector] pred_id={prediction_id} "
            f"drift_score={drift_score} threshold={model.drift_threshold}"
        )

        # Fire alert if drift exceeds model's configured threshold
        if drift_score > model.drift_threshold:
            _create_drift_alert(db, model, prediction_id, drift_score)

    except Exception as e:
        logger.error(
            f"[DriftDetector] Failed for prediction {prediction_id}: {e}"
        )
        db.rollback()
