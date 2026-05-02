"""
ModelVersion ORM model for tracking fine-tuned model lineages.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    base_model: Mapped[str] = mapped_column(String(128), nullable=False)
    version_tag: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_versions.id")
    )
    adapter_uri: Mapped[str | None] = mapped_column(String(512))
    gguf_uri: Mapped[str | None] = mapped_column(String(512))
    evaluation_scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_candidate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
