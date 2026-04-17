from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
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
    from .alert import Alert
    from .prediction import Prediction
    from .user import User


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # e.g. "classification", "regression", "nlp"
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # e.g. "production", "staging", "retired"
    status: Mapped[str] = mapped_column(String(50), default="staging")

    # Drift threshold — alert when drift score exceeds this
    drift_threshold: Mapped[float] = mapped_column(Float, default=0.05)

    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Foreign key to owner
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="ml_models")
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction", back_populates="ml_model", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="ml_model", cascade="all, delete-orphan"
    )
