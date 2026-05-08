"""Add owner_datasets table for curated training data uploads.

Supports CSV/JSON/JSONL with annotation and conversion to preference pairs.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "006_owner_datasets"
down_revision = "005_feedback_enhance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "owner_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("file_type", sa.String(16), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("schema_preview", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.Column("annotation_config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("converted_dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index("idx_owner_datasets_tenant", "owner_datasets", ["tenant_id"])
    op.create_index("idx_owner_datasets_status", "owner_datasets", ["status"])


def downgrade() -> None:
    op.drop_index("idx_owner_datasets_status", table_name="owner_datasets")
    op.drop_index("idx_owner_datasets_tenant", table_name="owner_datasets")
    op.drop_table("owner_datasets")
