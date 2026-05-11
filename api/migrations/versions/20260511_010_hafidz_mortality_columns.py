"""Add child mortality columns to hafidz_contributions.

Implements SP-009 Extension — tracks when a child ADO instance dies
(license expired, destroyed, revoked) so the parent can extract final
knowledge and capabilities.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "010_hafidz_mortality_columns"
down_revision = "009_feedback_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add child_alive, child_death_reason, child_death_at columns."""
    op.add_column(
        "hafidz_contributions",
        sa.Column("child_alive", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "hafidz_contributions",
        sa.Column("child_death_reason", sa.String(), nullable=True),
    )
    op.add_column(
        "hafidz_contributions",
        sa.Column("child_death_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove child mortality columns."""
    op.drop_column("hafidz_contributions", "child_death_at")
    op.drop_column("hafidz_contributions", "child_death_reason")
    op.drop_column("hafidz_contributions", "child_alive")
