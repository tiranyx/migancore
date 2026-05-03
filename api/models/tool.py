"""
Tool ORM model.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, Integer, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    handler_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="builtin"
    )
    handler_config: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    scopes_required: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )
    risk_level: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium"
    )
    policy: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    max_calls_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1000
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
