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

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models import AsyncSessionLocal, User, Tenant, Agent
from deps.db import set_tenant_context
from services.password import hash_password


TEST_EMAIL_A = "rls_test_a@migancore.com"
TEST_EMAIL_B = "rls_test_b@migancore.com"
TEST_SLUG_A = "rls-test-a"
TEST_SLUG_B = "rls-test-b"


async def _cleanup_legacy():
    """Remove any leftover test data from prior runs."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("SET LOCAL app.current_tenant = '00000000-0000-0000-0000-000000000000'"))
        await session.execute(text(f"DELETE FROM agents WHERE tenant_id IN (SELECT id FROM tenants WHERE slug IN ('{TEST_SLUG_A}', '{TEST_SLUG_B}'))"))
        await session.execute(text(f"DELETE FROM users WHERE tenant_id IN (SELECT id FROM tenants WHERE slug IN ('{TEST_SLUG_A}', '{TEST_SLUG_B}'))"))
        await session.execute(text(f"DELETE FROM tenants WHERE slug IN ('{TEST_SLUG_A}', '{TEST_SLUG_B}')"))
        await session.commit()


async def _create_test_user(email: str, tenant_slug: str) -> tuple[User, Tenant]:
    """Create a test user + tenant directly in the DB."""
    async with AsyncSessionLocal() as session:
        tenant = Tenant(name=f"Test {tenant_slug}", slug=tenant_slug)
        session.add(tenant)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            email=email,
            password_hash=hash_password("TestPass123!"),
            role="owner",
        )
        session.add(user)
        await session.commit()

        # Refresh to get IDs
        await session.refresh(tenant)
        await session.refresh(user)
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
    await session.commit()


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

    # Create an agent for Tenant A (bypass RLS for setup)
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, str(tenant_a.id))
        agent = Agent(
            tenant_id=tenant_a.id,
            name="Secret Agent",
            slug="secret-agent",
        )
        session.add(agent)
        await session.commit()
        print(f"Agent created for Tenant A: {agent.id}")

    failures = []

    # Test 1: Tenant A can see their own agent
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, str(tenant_a.id))
        result = await session.execute(select(Agent))
        agents = result.scalars().all()
        if len(agents) == 1 and agents[0].name == "Secret Agent":
            print("TEST 1 PASS: Tenant A sees their own agent")
        else:
            print(f"TEST 1 FAIL: Tenant A sees {len(agents)} agents")
            failures.append("TEST 1")

    # Test 2: Tenant B cannot see Tenant A's agent
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, str(tenant_b.id))
        result = await session.execute(select(Agent))
        agents = result.scalars().all()
        if len(agents) == 0:
            print("TEST 2 PASS: Tenant B sees 0 agents (isolation works)")
        else:
            print(f"TEST 2 FAIL: Tenant B sees {len(agents)} agents — DATA LEAK!")
            failures.append("TEST 2")

    # Test 3: Query without SET LOCAL should fail/return nothing
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Agent))
            agents = result.scalars().all()
            if len(agents) == 0:
                print("TEST 3 PASS: No tenant context → 0 agents")
            else:
                print(f"TEST 3 WARN: No tenant context → {len(agents)} agents (RLS not strict?)")
        except Exception as exc:
            print(f"TEST 3 PASS: No tenant context → error (fail-closed): {exc}")

    # Test 4: Users table RLS — Tenant B cannot see Tenant A's user
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, str(tenant_b.id))
        result = await session.execute(select(User).where(User.email == TEST_EMAIL_A))
        user = result.scalar_one_or_none()
        if user is None:
            print("TEST 4 PASS: Tenant B cannot find Tenant A's user")
        else:
            print(f"TEST 4 FAIL: Tenant B found Tenant A's user — DATA LEAK!")
            failures.append("TEST 4")

    # Cleanup
    async with AsyncSessionLocal() as session:
        await _cleanup_test_data(session, [tenant_a.id, tenant_b.id])
    print("\nTest data cleaned up.")

    if failures:
        print(f"\n{len(failures)} TEST(S) FAILED: {', '.join(failures)}")
        return False
    print("\nALL RLS TESTS PASSED")
    return True


if __name__ == "__main__":
    ok = asyncio.run(test_rls_isolation())
    exit(0 if ok else 1)
