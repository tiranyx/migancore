"""Initialize test database from current models + RLS + seed data.

Used by docker-compose.test.yml instead of alembic upgrade head
because the baseline migration has drifted from current models.
"""

import asyncio
import os
import sys

sys.path.insert(0, "/app")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from models.base import Base

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://ado_app:test@localhost:5432/ado_test")

# RLS policies from baseline migration
RLS_POLICIES = """
CREATE POLICY IF NOT EXISTS tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY IF NOT EXISTS tenant_isolation_agents ON agents
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY IF NOT EXISTS tenant_isolation_conversations ON conversations
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY IF NOT EXISTS tenant_isolation_messages ON messages
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY IF NOT EXISTS tenant_isolation_feedback ON interactions_feedback
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY IF NOT EXISTS tenant_isolation_memory ON memory_blocks
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY IF NOT EXISTS tenant_isolation_archival ON archival_memory
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
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        # Extensions
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))

        # Tables from current models
        await conn.run_sync(Base.metadata.create_all)

        # Enable RLS
        rls_tables = [
            "users", "agents", "conversations", "messages",
            "interactions_feedback", "memory_blocks", "archival_memory",
        ]
        for tbl in rls_tables:
            await conn.execute(text(f"ALTER TABLE IF EXISTS {tbl} ENABLE ROW LEVEL SECURITY"))

        # RLS policies
        for stmt in RLS_POLICIES.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                await conn.execute(text(stmt + ";"))

        # Seed builtin tools
        for name, display_name, description, handler_type, schema in SEED_TOOLS:
            await conn.execute(
                text(
                    "INSERT INTO tools (name, display_name, description, handler_type, schema) "
                    "VALUES (:name, :display_name, :description, :handler_type, :schema) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {
                    "name": name,
                    "display_name": display_name,
                    "description": description,
                    "handler_type": handler_type,
                    "schema": schema,
                },
            )

        # Seed initial model version
        await conn.execute(
            text(
                "INSERT INTO model_versions (base_model, version_tag, is_active) "
                "VALUES (:base_model, :version_tag, :is_active) "
                "ON CONFLICT (version_tag) DO NOTHING"
            ),
            {
                "base_model": "qwen2.5:7b-instruct-q4_K_M",
                "version_tag": "v0.1-seed",
                "is_active": True,
            },
        )

    await engine.dispose()
    print("✅ Test database initialized")


if __name__ == "__main__":
    asyncio.run(init())
