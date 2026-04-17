from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .ml_model import MLModel


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # e.g. "drift_detected", "low_confidence", "high_latency"
    alert_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    # Human-readable message
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Severity: "low", "medium", "high", "critical"
    severity: Mapped[str] = mapped_column(String(50), default="medium")

    # The metric value that triggered this alert
    triggered_value: Mapped[float] = mapped_column(Float, nullable=True)

    # Whether the alert has been acknowledged
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Foreign key
    ml_model_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ml_models.id"), nullable=False, index=True
    )

    # Relationships
    ml_model: Mapped["MLModel"] = relationship(
        "MLModel", back_populates="alerts"
    )
