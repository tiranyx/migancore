"""Day 72a — Add service_bypass_audit_events RLS policy.

Fixes hourly RLS violation on audit_events by adding service-role bypass
policy for the ado_app role.

This patch was applied manually on Day 72a; this migration makes it
repeatable for new databases.
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "008_audit_events_rls_fix"
down_revision = "007_schema_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    # Drop existing policy if present (idempotent)
    connection.execute(text("""
        DROP POLICY IF EXISTS service_bypass_audit_events ON audit_events;
    """))

    # Create service-role bypass policy
    connection.execute(text("""
        CREATE POLICY service_bypass_audit_events
            ON audit_events
            FOR ALL
            TO ado_app
            WITH CHECK (true);
    """))


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(text("""
        DROP POLICY IF EXISTS service_bypass_audit_events ON audit_events;
    """))
