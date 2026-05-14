"""Pytest fixtures and configuration for MiganCore API tests."""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient

# Ensure test environment
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://ado_app:changeme@localhost:5432/ado_test")
os.environ.setdefault("REDIS_URL", "redis://:changeme@localhost:6379/1")
os.environ.setdefault("ADMIN_SECRET_KEY", "")
os.environ.setdefault("LICENSE_DEMO_MODE", "true")

from config import settings
from main import app, lifespan
from models.base import init_engine, engine, AsyncSessionLocal


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_engine():
    """Initialize database engine for tests."""
    init_engine()
    yield engine


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Create a fresh database session for each test."""
    if AsyncSessionLocal is None:
        raise RuntimeError("AsyncSessionLocal not initialized")
    async with AsyncSessionLocal() as session:
        yield session
        # Rollback after each test to keep DB clean
        await session.rollback()


@pytest.fixture(scope="session")
async def test_app():
    """Yield the FastAPI app with lifespan manager started."""
    async with lifespan(app):
        yield app


@pytest.fixture(scope="function")
async def async_client(test_app):
    """Async HTTP client for testing."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def sync_client(test_app):
    """Sync HTTP client using TestClient (for routes that need sync)."""
    from fastapi.testclient import TestClient
    with TestClient(test_app) as client:
        yield client


@pytest.fixture(scope="session")
def secret_key():
    """Test secret key for license validation."""
    return "test-secret-key-32-chars-long!!!"


@pytest.fixture(scope="function")
async def test_tenant(db_session):
    """Create a test tenant."""
    from models.tenant import Tenant
    tenant = Tenant(
        name="Test Tenant",
        slug=f"test-{uuid.uuid4().hex[:8]}",
        plan="free",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
async def test_user(db_session, test_tenant):
    """Create a test user with auth token."""
    from services.password import hash_password
    from models.user import User
    user = User(
        tenant_id=test_tenant.id,
        email=f"test-{uuid.uuid4().hex[:8]}@migancore.com",
        password_hash=hash_password("TestPass123!"),
        display_name="Test User",
        role="member",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
