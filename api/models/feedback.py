"""
User Feedback ORM model.

Tracks every thumbs up/down, followup, and correction signal.
This is the audit trail. Preference pairs are derived from these signals
by background workers (teacher distillation, synthetic generation).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class FeedbackEvent(Base):
    """A single user interaction signal (thumb, followup, correction)."""

    __tablename__ = "interactions_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)

    signal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # thumb_up, thumb_down, followup, retry, length_ok, length_bad, correction

    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Optional numeric score (e.g. 0.0–1.0)

    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free-text user comment

    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="user"
    )
    # user, llm_judge, implicit

    judge_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # If source == llm_judge, which model judged it

    # Derived data — populated by background worker
    preference_pair_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("preference_pairs.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
