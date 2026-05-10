"""Day 72d — Feedback hardening: add processing_attempts to preference_pairs.

Enables retry tracking for pairs with AWAITING_* placeholders.
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "009_feedback_hardening"
down_revision = "008_audit_events_rls_fix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(text("""
        ALTER TABLE preference_pairs
            ADD COLUMN IF NOT EXISTS processing_attempts INT NOT NULL DEFAULT 0;
    """))
    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_preference_pairs_awaiting
            ON preference_pairs(processing_attempts)
            WHERE chosen LIKE '__AWAITING_CHOSEN__%'
               OR rejected LIKE '__AWAITING_REJECTED__%';
    """))


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(text("""
        DROP INDEX IF EXISTS idx_preference_pairs_awaiting;
    """))
    connection.execute(text("""
        ALTER TABLE preference_pairs
            DROP COLUMN IF EXISTS processing_attempts;
    """))
