"""
Audit logging service for security and compliance events.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models import AuditEvent


async def log_audit_event(
    db: AsyncSession,
    event_type: str,
    tenant_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Record an audit event.
    
    Does NOT commit — the caller's transaction should commit.
    If the caller rolls back, the audit event is also rolled back.
    For critical security events, consider a separate background task.
    """
    event = AuditEvent(
        tenant_id=uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id,
        user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=uuid.UUID(resource_id) if isinstance(resource_id, str) else resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(event)
