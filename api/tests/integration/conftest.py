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
    """Create engine and tables for integration test session."""
    from models.base import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_engine
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await async_engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional DB session that rolls back after each test.

    Sets a dummy tenant context so RLS-enabled tables can be queried without
    raising 'unrecognized configuration parameter app.current_tenant'.
    Uses SET (session-level, false) because NullPool gives each test its own
    dedicated connection that is closed afterwards — no pool leakage risk.
    """
    async with AsyncTestingSessionLocal() as session:
        await session.execute(
            text("SELECT set_config('app.current_tenant', '00000000-0000-0000-0000-000000000000', false)")
        )
        yield session
        await session.rollback()
