"""
SQLAlchemy async base configuration for MiganCore.

Engine is created lazily via init_engine() to avoid module-level side effects
and connection pool corruption on process fork (e.g. Celery workers).
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# Engine and session factory are initialized lazily via init_engine()
engine = None
AsyncSessionLocal = None


def init_engine():
    """Create the async engine and session factory.

    Must be called once during application startup (lifespan).
    """
    global engine, AsyncSessionLocal
    if engine is not None:
        return
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        echo=settings.ENVIRONMENT == "development",
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )



