"""
Owner Dataset model — curated training data uploaded by platform owners.

Supports CSV/JSON/JSONL uploads with annotation and conversion to
preference pairs for training flywheel.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, ForeignKey, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class OwnerDataset(Base):
    """A dataset uploaded by an owner for training or evaluation."""

    __tablename__ = "owner_datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # csv, json, jsonl
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    schema_preview: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # {"columns": [...], "sample": [...]}

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="uploaded"
    )  # uploaded, processing, ready, converted, error

    annotation_config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # {"labels": [{"name": "quality", "type": "score"}]}

    converted_dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
