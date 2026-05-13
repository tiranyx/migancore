"""
Database dependency with tenant context injection for RLS.
"""

from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models import base as _base


async def get_db() -> AsyncSession:
    """Dependency: yield an async DB session without tenant context.
    
    Use this for system-level queries (health checks, startup) where
    RLS is not needed. For tenant-scoped endpoints, use get_db_tenant
    or call set_tenant_context() explicitly.
    """
    if _base.AsyncSessionLocal is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    async with _base.AsyncSessionLocal() as session:
        yield session


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """Set PostgreSQL RLS context for the current transaction.
    
    Must be called before any query on tenant-scoped tables.
    Uses SET LOCAL so the setting is automatically cleared on transaction end.
    """
    await session.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": tenant_id},
    )


@asynccontextmanager
async def get_admin_db():
    """Context manager: yield a session without RLS (superuser cross-tenant queries).

    Uses the same DATABASE_URL (ado superuser) but skips tenant context so
    background workers can query across all tenants — distillation, watchdog, etc.
    """
    if _base.AsyncSessionLocal is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    async with _base.AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def tenant_session(tenant_id: str | None):
    """Context manager: yield a DB session with RLS tenant context set.
    
    Usage:
        async with tenant_session(str(user.tenant_id)) as session:
            result = await session.execute(select(Agent))
    """
    if _base.AsyncSessionLocal is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    async with _base.AsyncSessionLocal() as session:
        if tenant_id:
            await set_tenant_context(session, tenant_id)
        yield session
