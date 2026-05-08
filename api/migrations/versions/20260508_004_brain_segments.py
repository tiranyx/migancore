"""Add brain_segments table for Parent Brain knowledge accumulation.

Implements the collective memory of the parent ADO:
  - Children contribute segments (skills, patterns, knowledge).
  - Parent synthesizes and redistributes to siblings / newborns.
  - Segments survive child mortality (source_child_license_id becomes "parent").
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "004_brain_segments"
down_revision = "003_patches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brain_segments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("segment_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("source_child_license_id", sa.String(), nullable=False),
        sa.Column(
            "source_contribution_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column(
            "transferable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "auto_push",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "synced_to_children",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index("idx_brain_segments_type", "brain_segments", ["segment_type"])
    op.create_index(
        "idx_brain_segments_source",
        "brain_segments",
        ["source_child_license_id"],
    )
    op.create_index(
        "idx_brain_segments_quality",
        "brain_segments",
        ["quality_score"],
    )


def downgrade() -> None:
    op.drop_index("idx_brain_segments_quality", table_name="brain_segments")
    op.drop_index("idx_brain_segments_source", table_name="brain_segments")
    op.drop_index("idx_brain_segments_type", table_name="brain_segments")
    op.drop_table("brain_segments")
