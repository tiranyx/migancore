"""
Parent Brain — Brain Segment Model

A Brain Segment is a modular unit of knowledge that the parent accumulates
from children and distributes back to the family.

Philosophy:
  - The parent is the family's collective memory.
  - Each child contributes segments (skills, patterns, knowledge).
  - The parent synthesizes and redistributes segments to all children.
  - When a child dies, its segments live on in the parent's brain.

Segment types:
  skill          → A learned capability (e.g. "draft legal contract")
  domain_knowledge → Factual knowledge about a domain
  tool_pattern   → A pattern of tool usage
  voice_pattern  → A communication style / tone
  dpo_pair       → A training example (prompt, chosen, rejected)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, Integer, text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class BrainSegment(Base):
    """A modular knowledge unit in the parent's collective brain."""

    __tablename__ = "brain_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    # Classification
    segment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # e.g. "skill", "domain_knowledge", "tool_pattern", "voice_pattern", "dpo_pair"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Human-readable name, e.g. "Contract Drafting Skill v3"

    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Source tracking
    source_child_license_id: Mapped[str] = mapped_column(String, nullable=False)
    # "parent" if native to the parent, or the child's license_id

    source_contribution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # Link to hafidz_contributions.id (optional)

    # Content
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # The actual knowledge content — schema depends on segment_type

    # Quality & versioning
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Distribution flags
    transferable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    # Can this segment be shared with other children?

    auto_push: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    # Auto-push to new/live children on sync?

    # Tracking which children have received this segment
    synced_to_children: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    # List of child_license_ids that have synced this segment

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
