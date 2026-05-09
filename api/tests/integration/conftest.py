"""Integration test fixtures — requires PostgreSQL + Redis."""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Override DATABASE_URL for integration tests
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://ado:test@localhost:5432/ado_test",
)

async_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True, poolclass=NullPool)
AsyncTestingSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create engine and tables for integration test session.

    Tables are created by init_test_db.py (superuser) before tests run;
    create_all here is idempotent (checkfirst=True).  We do NOT drop_all
    on teardown because ado_app is not the table owner and would get
    InsufficientPrivilegeError.
    """
    from models.base import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_engine
    await async_engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional DB session that cleans up after each test.

    Sets a dummy tenant context so RLS-enabled tables can be queried without
    raising 'unrecognized configuration parameter app.current_tenant'.
    Uses SET (session-level, false) because NullPool gives each test its own
    dedicated connection that is closed afterwards — no pool leakage risk.

    The fixture wraps the test in a savepoint (begin_nested) inside an outer
    transaction.  Services that call session.commit() will only commit the
    savepoint; the outer transaction is rolled back on teardown so no data
    leaks between tests.
    """
    async with AsyncTestingSessionLocal() as session:
        async with session.begin() as _outer_tx:
            await session.execute(
                text("SELECT set_config('app.current_tenant', '00000000-0000-0000-0000-000000000000', false)")
            )
            async with session.begin_nested():
                yield session

        # If a test or service committed the outer transaction explicitly
        # (rare), the automatic rollback above won't fire.  Run explicit
        # cleanup as a safety net.
        await session.rollback()
        try:
            await session.execute(text("DELETE FROM interactions_feedback"))
            await session.execute(text("DELETE FROM preference_pairs"))
            await session.execute(text("DELETE FROM messages"))
            await session.execute(text("DELETE FROM conversations"))
            await session.execute(text("DELETE FROM agents"))
            await session.execute(text("DELETE FROM tenants WHERE slug LIKE 'test-tenant-%'"))
            await session.commit()
        except Exception:
            await session.rollback()
