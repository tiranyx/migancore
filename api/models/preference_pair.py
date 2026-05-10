"""
PreferencePair ORM model — DPO training data flywheel (Day 17).

preference_pairs is a GLOBAL table (no tenant_id, no RLS).
Every CAI pipeline run that detects a low-quality response stores
one (chosen=revised, rejected=original) pair here for training.

Schema mirrors init.sql: prompt, chosen, rejected, judge_score,
judge_model, source_method, source_message_id, created_at,
used_in_training_run_id (NULL = not yet used in any training run).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class PreferencePair(Base):
    __tablename__ = "preference_pairs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    chosen: Mapped[str] = mapped_column(Text, nullable=False)
    rejected: Mapped[str] = mapped_column(Text, nullable=False)
    judge_score: Mapped[float] = mapped_column(Float, nullable=False)
    judge_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_method: Mapped[str] = mapped_column(String(64), nullable=False)
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    used_in_training_run_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True, default=None
    )
    processing_attempts: Mapped[int] = mapped_column(
        nullable=False, default=0
    )
