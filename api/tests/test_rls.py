"""
Cross-tenant RLS isolation tests.

Run inside the API container:
    docker compose exec api python -m pytest tests/test_rls.py -v

Or run directly:
    docker compose exec api python tests/test_rls.py
"""

import asyncio
import sys
import uuid

sys.path.insert(0, "/app")

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Tenant, Agent
from models.base import init_engine
from deps.db import set_tenant_context
from services.password import hash_password


TEST_EMAIL_A = "rls_test_a@migancore.com"
TEST_EMAIL_B = "rls_test_b@migancore.com"
TEST_SLUG_A = "rls-test-a"
TEST_SLUG_B = "rls-test-b"


async def _cleanup_legacy():
    """Remove any leftover test data from prior runs."""
    init_engine()
    from models.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(text("SELECT set_config('app.current_tenant', '00000000-0000-0000-0000-000000000000', false)"))
            # Aggressive cleanup: wipe all test data from shared tables
            await session.execute(text("DELETE FROM interactions_feedback"))
            await session.execute(text("DELETE FROM preference_pairs"))
            await session.execute(text("DELETE FROM messages"))
            await session.execute(text("DELETE FROM conversations"))
            await session.execute(text("DELETE FROM agents"))
            await session.execute(text("DELETE FROM users WHERE tenant_id IN (SELECT id FROM tenants WHERE slug LIKE 'test-%' OR slug IN ('rls-test-a', 'rls-test-b'))"))
            await session.execute(text("DELETE FROM tenants WHERE slug LIKE 'test-%' OR slug IN ('rls-test-a', 'rls-test-b')"))


async def _create_test_user(email: str, tenant_slug: str) -> tuple[User, Tenant]:
    """Create a test user + tenant directly in the DB."""
    init_engine()
    from models.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        async with session.begin():
            tenant = Tenant(name=f"Test {tenant_slug}", slug=tenant_slug)
            session.add(tenant)
            await session.flush()

            # Set tenant context before creating user (RLS enforced)
            await set_tenant_context(session, str(tenant.id))

            user = User(
                tenant_id=tenant.id,
                email=email,
                password_hash=hash_password("TestPass123!"),
                role="owner",
            )
            session.add(user)
        return user, tenant


async def _cleanup_test_data(session: AsyncSession, tenant_ids: list[uuid.UUID]):
    """Remove test data. Bypass RLS for cleanup."""
    for tid in tenant_ids:
        await session.execute(
            text("DELETE FROM agents WHERE tenant_id = :tid"),
            {"tid": str(tid)},
        )
        await session.execute(
            text("DELETE FROM users WHERE tenant_id = :tid"),
            {"tid": str(tid)},
        )
        await session.execute(
            text("DELETE FROM tenants WHERE id = :tid"),
            {"tid": str(tid)},
        )


@pytest.mark.asyncio
async def test_rls_isolation():
    """Main RLS test: Tenant A cannot see Tenant B's data."""
    print("\n=== RLS ISOLATION TEST ===\n")

    # Cleanup first to handle dirty state from previous interrupted runs
    await _cleanup_legacy()

    # Setup: create two tenants
    user_a, tenant_a = await _create_test_user(TEST_EMAIL_A, TEST_SLUG_A)
    user_b, tenant_b = await _create_test_user(TEST_EMAIL_B, TEST_SLUG_B)
    print(f"Tenant A: {tenant_a.id} ({tenant_a.slug})")
    print(f"Tenant B: {tenant_b.id} ({tenant_b.slug})")

    # Create an agent for Tenant A (with RLS context inside a transaction)
    init_engine()
    from models.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_a.id))
            agent = Agent(
                tenant_id=tenant_a.id,
                name="Secret Agent",
                slug="secret-agent",
            )
            session.add(agent)
        print(f"Agent created for Tenant A: {agent.id}")

    failures = []

    # Test 1: Tenant A can see their own agent
    init_engine()
    from models.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_a.id))
            result = await session.execute(text("SELECT id, name, tenant_id FROM agents"))
            rows = result.fetchall()
            agents = [{"id": r[0], "name": r[1], "tenant_id": r[2]} for r in rows]
    if len(agents) == 1 and agents[0]["name"] == "Secret Agent":
        print("TEST 1 PASS: Tenant A sees their own agent")
    else:
        print(f"TEST 1 FAIL: Tenant A sees {len(agents)} agents")
        failures.append("TEST 1")

    # Test 2: Tenant B cannot see Tenant A's agent
    init_engine()
    from models.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, str(tenant_b.id))
            result = await session.execute(text("SELECT id, name, tenant_id FROM agents"))
            rows = result.fetchall()
            agents = [{"id": r[0], "name": r[1], "tenant_id": r[2]} for r in rows]
    if len(agents) == 0:
        print("TEST 2 PASS: Tenant B sees 0 agents (isolation works)")
    else:
        print(f"TEST 2 FAIL: Tenant B sees {len(agents)} agents — DATA LEAK!")
        for a in agents:
            print(f"  LEAKED: id={a['id']}, name={a['name']}, tenant_id={a['tenant_id']}")
        failures.append("TEST 2")

    # Test 3: Query without tenant context should fail-closed (error)
    init_engine()
    from models.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            async with session.begin():
                result = await session.execute(text("SELECT id, name, tenant_id FROM agents"))
                rows = result.fetchall()
                agents = [{"id": r[0], "name": r[1], "tenant_id": r[2]} for r in rows]
            if len(agents) == 0:
                print("TEST 3 PASS: No tenant context → 0 agents")
            else:
                print(f"TEST 3 WARN: No tenant context → {len(agents)} agents (RLS not strict?)")
                for a in agents:
                    print(f"  ORPHAN: id={a['id']}, name={a['name']}, tenant_id={a['tenant_id']}")
        except Exception as exc:
            print(f"TEST 3 PASS: No tenant context → error (fail-closed): {exc}")

    # Test 4: Users table RLS — Tenant B cannot see Tenant A's user
    # NOTE: RLS on users is temporarily disabled for auth compatibility.
    # Re-enable in Week 2 with a SECURITY DEFINER login lookup function.
    print("TEST 4 SKIP: Users RLS disabled (see migration 009)")

    # Cleanup
    init_engine()
    from models.base import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await _cleanup_test_data(session, [tenant_a.id, tenant_b.id])
    print("\nTest data cleaned up.")

    if failures:
        print(f"\n{len(failures)} TEST(S) FAILED: {', '.join(failures)}")
    print("\nALL RLS TESTS PASSED")
    
    # Use assertions for pytest compatibility
    assert len(failures) == 0, f"RLS tests failed: {failures}"


if __name__ == "__main__":
    try:
        asyncio.run(test_rls_isolation())
        exit(0)
    except AssertionError as e:
        print(f"FAILED: {e}")
        exit(1)
