"""Enhance interactions_feedback table for proper audit trail.

Adds:
  - comment (free-text user note)
  - preference_pair_id (FK to preference_pairs, nullable)

These columns support the refactored feedback service which links every
user signal to a derived preference pair.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "005_feedback_enhance"
down_revision = "004_brain_segments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interactions_feedback",
        sa.Column("comment", sa.Text(), nullable=True),
    )
    op.add_column(
        "interactions_feedback",
        sa.Column(
            "preference_pair_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("preference_pairs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_feedback_pair",
        "interactions_feedback",
        ["preference_pair_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_feedback_pair", table_name="interactions_feedback")
    op.drop_column("interactions_feedback", "preference_pair_id")
    op.drop_column("interactions_feedback", "comment")
