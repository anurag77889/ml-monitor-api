from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .ml_model import MLModel


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # The input features sent to the model (stored as JSON)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # What the model predicted
    prediction_output: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Ground truth label (filled in later when available)
    actual_output: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Confidence score of the prediction (0.0 to 1.0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Drift score computed by background task
    drift_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Latency in milliseconds
    latency_ms: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    # Foreign key
    ml_model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ml_models.id"), nullable=False, index=True
    )

    # Relationships
    ml_model: Mapped["MLModel"] = relationship(
        "MLModel", back_populates="predictions"
    )
