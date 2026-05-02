"""
Database dependency with tenant context injection.
"""

from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models import AsyncSessionLocal


@asynccontextmanager
async def tenant_session(tenant_id: str | None, user_id: str | None = None):
    """Yield a DB session with SET LOCAL tenant context for RLS."""
    async with AsyncSessionLocal() as session:
        if tenant_id:
            await session.execute(
                text("SET LOCAL app.current_tenant = :tid"),
                {"tid": tenant_id},
            )
        if user_id:
            await session.execute(
                text("SET LOCAL app.current_user = :uid"),
                {"uid": user_id},
            )
        yield session
