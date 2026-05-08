"""Add Hafidz Ledger table for knowledge return from child ADO instances.

Implements "Anak Kembali ke Induk" — anonymized domain knowledge flows
back to the parent Migancore when a licensed child instance expires or
opts into contribution.

Related: docs/MIGANCORE_AMOEBA_ARCHITECTURE_LOCKED.md (Section IV)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002_hafidz_ledger"
down_revision = "001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create hafidz_contributions table and indexes."""
    op.create_table(
        "hafidz_contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("child_license_id", sa.String(), nullable=False),
        sa.Column("child_display_name", sa.String(), nullable=False),
        sa.Column("child_tier", sa.String(), nullable=False),
        sa.Column("parent_version", sa.String(), nullable=False),
        sa.Column("contribution_type", sa.String(), nullable=False),
        sa.Column("contribution_hash", sa.String(), nullable=False, unique=True),
        sa.Column("anonymized_payload", postgresql.JSONB(), nullable=False, default={}),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("incorporated_cycle", sa.Integer(), nullable=True),
        sa.Column("incorporated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reject_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index("hafidz_parent_version_idx", "hafidz_contributions", ["parent_version"])
    op.create_index("hafidz_status_idx", "hafidz_contributions", ["status"])
    op.create_index("hafidz_type_idx", "hafidz_contributions", ["contribution_type"])
    op.create_index("hafidz_cycle_idx", "hafidz_contributions", ["incorporated_cycle"])
    op.create_index("hafidz_license_idx", "hafidz_contributions", ["child_license_id"])

    # Create summary view
    op.execute("""
        CREATE VIEW hafidz_child_summary AS
        SELECT
            child_license_id,
            child_display_name,
            child_tier,
            parent_version,
            COUNT(*) as total_contributions,
            COUNT(CASE WHEN status = 'incorporated' THEN 1 END) as incorporated_count,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
            MIN(received_at) as first_contribution,
            MAX(received_at) as last_contribution
        FROM hafidz_contributions
        GROUP BY child_license_id, child_display_name, child_tier, parent_version;
    """)


def downgrade() -> None:
    """Drop Hafidz Ledger table, indexes, and view."""
    op.execute("DROP VIEW IF EXISTS hafidz_child_summary")
    op.drop_index("hafidz_license_idx", table_name="hafidz_contributions")
    op.drop_index("hafidz_cycle_idx", table_name="hafidz_contributions")
    op.drop_index("hafidz_type_idx", table_name="hafidz_contributions")
    op.drop_index("hafidz_status_idx", table_name="hafidz_contributions")
    op.drop_index("hafidz_parent_version_idx", table_name="hafidz_contributions")
    op.drop_table("hafidz_contributions")
