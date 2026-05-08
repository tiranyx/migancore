"""
SQLAlchemy ORM model for Hafidz Ledger contributions.

Note: This table is created via Alembic migration (20260508_002_hafidz_ledger.py),
not via Base.metadata.create_all(). The model is used for typed ORM operations.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Float, DateTime, Integer, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class HafidzContribution(Base):
    """A single knowledge contribution from a child ADO back to its parent."""

    __tablename__ = "hafidz_contributions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    child_license_id: Mapped[str] = mapped_column(String, nullable=False)
    child_display_name: Mapped[str] = mapped_column(String, nullable=False)
    child_tier: Mapped[str] = mapped_column(String, nullable=False)
    parent_version: Mapped[str] = mapped_column(String, nullable=False)
    contribution_type: Mapped[str] = mapped_column(String, nullable=False)
    contribution_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    anonymized_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default="pending"
    )
    incorporated_cycle: Mapped[int | None] = mapped_column(Integer, nullable=True)
    incorporated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reject_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
