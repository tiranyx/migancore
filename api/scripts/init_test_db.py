"""Initialize test database from current models + RLS + seed data.

Used by docker-compose.test.yml instead of alembic upgrade head
because the baseline migration has drifted from current models.
"""

import asyncio
import os
import sys
import uuid

sys.path.insert(0, "/app")

from sqlalchemy import text, Table, Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from models.base import Base

# Register the datasets table in Base.metadata so that FK references
# from owner_datasets work during Base.metadata.create_all().
# There is no ORM model for datasets (it is managed via raw SQL).
Table(
    "datasets",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("source_type", String(32), nullable=False),
    Column("size_samples", Integer, nullable=True),
    Column("hf_dataset_uri", String(512), nullable=True),
    Column("local_path", String(512), nullable=True),
    Column("parent_dataset_id", UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True),
    Column("quality_avg", Float, nullable=True),
    Column("language", String(8), nullable=True, default="id"),
    Column("domain", String(64), nullable=True),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    extend_existing=True,
)

# Connect as postgres superuser for setup, then tests run as ado_app
SETUP_DATABASE_URL = (
    "postgresql+asyncpg://postgres:test@postgres_test:5432/ado_test"
)

# RLS policies from baseline migration (PostgreSQL has no IF NOT EXISTS for policies)
RLS_POLICIES = """
CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_agents ON agents
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_conversations ON conversations
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_messages ON messages
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_feedback ON interactions_feedback
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_memory ON memory_blocks
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_archival ON archival_memory
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
"""

SEED_TOOLS = [
    ("web_search", "Web Search", "Search the web for current information", "builtin",
     '{"type":"object","properties":{"query":{"type":"string","description":"Search query"}},"required":["query"]}'),
    ("python_repl", "Python REPL", "Execute Python code in a sandbox", "builtin",
     '{"type":"object","properties":{"code":{"type":"string"},"timeout":{"type":"integer","default":30}},"required":["code"]}'),
    ("read_file", "Read File", "Read contents of a file", "builtin",
     '{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}'),
    ("http_get", "HTTP GET", "Make an HTTP GET request", "builtin",
     '{"type":"object","properties":{"url":{"type":"string"},"headers":{"type":"object"}},"required":["url"]}'),
    ("spawn_agent", "Spawn Agent", "Create a new child agent", "builtin",
     '{"type":"object","properties":{"template_id":{"type":"string"},"name":{"type":"string"},"persona":{"type":"object"}},"required":["name"]}'),
    ("memory_write", "Memory Write", "Write a fact to long-term memory", "builtin",
     '{"type":"object","properties":{"key":{"type":"string"},"value":{"type":"string"},"namespace":{"type":"string","default":"default"}},"required":["key","value"]}'),
    ("memory_search", "Memory Search", "Search long-term memory semantically", "builtin",
     '{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer","default":5}},"required":["query"]}'),
]


async def init() -> None:
    engine = create_async_engine(SETUP_DATABASE_URL)

    async with engine.begin() as conn:
        # Create ado_app as non-superuser (RLS will apply to this user)
        # Use IF NOT EXISTS guard so repeated runs against a persistent DB don't crash.
        try:
            await conn.execute(text("CREATE ROLE ado_app WITH LOGIN PASSWORD 'test'"))
        except Exception:
            pass  # Role already exists — safe to ignore
        await conn.execute(text("GRANT CREATE ON SCHEMA public TO ado_app"))
        await conn.execute(text("GRANT ALL PRIVILEGES ON DATABASE ado_test TO ado_app"))

        # Extensions
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))

        # Tables from current models (including datasets registered above)
        await conn.run_sync(Base.metadata.create_all)

        # Enable RLS on tables that exist in models
        rls_tables = [
            "users", "agents", "conversations", "messages",
            "interactions_feedback",
        ]
        for tbl in rls_tables:
            await conn.execute(text(f"ALTER TABLE IF EXISTS {tbl} ENABLE ROW LEVEL SECURITY"))
            await conn.execute(text(f"ALTER TABLE IF EXISTS {tbl} FORCE ROW LEVEL SECURITY"))

        # RLS policies (only for tables that exist in models)
        for stmt in RLS_POLICIES.strip().split(";"):
            stmt = stmt.strip()
            if stmt and "memory_blocks" not in stmt and "archival_memory" not in stmt:
                await conn.execute(text(stmt + ";"))

        # Grant all privileges to ado_app
        for tbl in Base.metadata.tables:
            await conn.execute(text(f"GRANT ALL PRIVILEGES ON TABLE {tbl} TO ado_app"))
        await conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ado_app"))
        await conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ado_app"))

    # Seed data using ORM so Python-side defaults are applied
    from sqlalchemy import select
    AsyncSeedSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSeedSession() as session:
        from models.tool import Tool
        from models.model_version import ModelVersion

        for name, display_name, description, handler_type, schema in SEED_TOOLS:
            result = await session.execute(select(Tool).where(Tool.name == name))
            if result.scalar_one_or_none() is None:
                tool = Tool(
                    name=name,
                    display_name=display_name,
                    description=description,
                    handler_type=handler_type,
                    schema=schema,
                )
                session.add(tool)

        result = await session.execute(select(ModelVersion).where(ModelVersion.version_tag == "v0.1-seed"))
        if result.scalar_one_or_none() is None:
            mv = ModelVersion(
                base_model="qwen2.5:7b-instruct-q4_K_M",
                version_tag="v0.1-seed",
                is_active=True,
            )
            session.add(mv)

        await session.commit()

    await engine.dispose()
    print("✅ Test database initialized")


if __name__ == "__main__":
    asyncio.run(init())
