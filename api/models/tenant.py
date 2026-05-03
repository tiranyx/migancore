"""
Tenant ORM model.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    max_agents: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_messages_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    messages_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    messages_day_reset: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    api_key_hash: Mapped[str | None] = mapped_column(String(255))
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    users = relationship("User", back_populates="tenant", lazy="raise")
