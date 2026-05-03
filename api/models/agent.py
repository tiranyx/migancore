"""
Agent ORM model.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    parent_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="qwen2.5:7b-instruct-q4_K_M")
    system_prompt: Mapped[str | None] = mapped_column(String(8192), nullable=True)
    persona_blob: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    persona_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    template_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    letta_agent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), nullable=False, default="private")
    webhook_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    interaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
