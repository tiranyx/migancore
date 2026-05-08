"""
Agent Cloning Service — SP-008

Wraps spawn logic with automatic license generation.
Child ADO receives a full license ready for Docker deployment.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models import Agent, User
from services.license import (
    LicenseTier,
    mint_license,
)

logger = structlog.get_logger()


async def clone_agent_with_license(
    session: AsyncSession,
    *,
    parent_agent: Agent,
    current_user: User,
    name: str,
    template_id: str | None,
    persona_overrides: dict | None,
    client_name: str,
    tier: str,
    language_pack: list[str],
    months: int | None,
    knowledge_return_enabled: bool,
    knowledge_return_opt_in_types: list[str] | None,
) -> tuple[Agent, dict[str, Any]]:
    """Clone a parent agent and generate a license for the child.

    Steps:
      1. Spawn child agent (inherit from parent)
      2. Generate license with genealogy metadata
      3. Store license reference in child persona_blob
      4. Return (child_agent, license_data)
    """
    from sqlalchemy import select, func, text
    from models import Tenant
    from services.config_loader import load_soul_md, get_personality_template
    from services.letta import ensure_letta_agent

    tenant_id = current_user.tenant_id

    # ── 1. Tenant limits ──────────────────────────────────────────────────
    tenant_result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one()

    agent_count_result = await session.execute(
        select(func.count(Agent.id)).where(
            Agent.tenant_id == tenant_id,
            Agent.status != "archived",
        )
    )
    current_agent_count = agent_count_result.scalar() or 0
    if current_agent_count >= tenant.max_agents:
        raise ValueError(
            f"Agent limit reached: {current_agent_count}/{tenant.max_agents}"
        )

    # ── 2. Generation depth ───────────────────────────────────────────────
    MAX_GENERATION_DEPTH = 5
    if parent_agent.generation + 1 > MAX_GENERATION_DEPTH:
        raise ValueError(f"Maximum generation depth reached ({MAX_GENERATION_DEPTH})")

    # ── 3. Build persona ──────────────────────────────────────────────────
    child_persona = dict(parent_agent.persona_blob or {})

    if template_id:
        tpl = get_personality_template(template_id)
        if tpl:
            for key in ("voice", "tone", "values", "anti_patterns", "additions", "name"):
                if key in tpl:
                    child_persona[key] = tpl[key]
            child_persona["_template_applied"] = template_id

    if persona_overrides:
        child_persona.update(persona_overrides)

    # ── 4. Generate license ───────────────────────────────────────────────
    secret_key = os.environ.get("LICENSE_SECRET_KEY", "")
    if not secret_key:
        raise RuntimeError("LICENSE_SECRET_KEY not configured on cloning server")

    # Build lineage chain
    lineage_chain = child_persona.get("_lineage_chain", []) or []
    if not lineage_chain:
        lineage_chain = [str(parent_agent.id)]
    else:
        lineage_chain = list(lineage_chain) + [str(parent_agent.id)]

    license_tier = LicenseTier(tier)
    license_data = mint_license(
        client_name=client_name,
        ado_display_name=name,
        tier=license_tier,
        language_pack=language_pack,
        secret_key=secret_key,
        months=months,
        parent_version=parent_agent.model_version,
        generation=parent_agent.generation + 1,
        lineage_chain=lineage_chain,
        knowledge_return_enabled=knowledge_return_enabled,
        knowledge_return_opt_in_types=knowledge_return_opt_in_types,
    )

    # Embed license metadata into persona for tracking
    child_persona["_license"] = {
        "license_id": license_data["license_id"],
        "tier": tier,
        "issued_date": license_data["issued_date"],
        "expiry_date": license_data["expiry_date"],
        "parent_version": parent_agent.model_version,
        "generation": parent_agent.generation + 1,
        "knowledge_return_enabled": knowledge_return_enabled,
    }
    child_persona["_lineage_chain"] = lineage_chain

    # ── 5. Create child agent ─────────────────────────────────────────────
    child = Agent(
        tenant_id=tenant_id,
        owner_user_id=current_user.id,
        parent_agent_id=parent_agent.id,
        name=name,
        slug=__import__("secrets").token_urlsafe(8),
        description=parent_agent.description,
        generation=parent_agent.generation + 1,
        model_version=parent_agent.model_version,
        system_prompt=parent_agent.system_prompt,
        persona_blob=child_persona,
        template_id=template_id or parent_agent.template_id or str(parent_agent.id),
        visibility=parent_agent.visibility,
        status="active",
    )
    session.add(child)
    await session.commit()
    await session.refresh(child)

    # ── 6. Copy tool grants ───────────────────────────────────────────────
    await session.execute(
        text(
            """
            INSERT INTO agent_tool_grants (agent_id, tool_id, granted_by_user_id, granted_at)
            SELECT :child_id, tool_id, :user_id, NOW()
            FROM agent_tool_grants
            WHERE agent_id = :parent_id
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "child_id": str(child.id),
            "parent_id": str(parent_agent.id),
            "user_id": str(current_user.id),
        },
    )
    await session.commit()

    # ── 7. Provision Letta ────────────────────────────────────────────────
    soul_text = load_soul_md(None)
    letta_id = await ensure_letta_agent(
        migancore_agent_id=str(child.id),
        agent_name=child.name,
        soul_text=soul_text,
        persona_overrides=child_persona or None,
        existing_letta_id=None,
    )
    if letta_id:
        child.letta_agent_id = letta_id
        await session.commit()
        await session.refresh(child)

    logger.info(
        "agent.cloned",
        parent_id=str(parent_agent.id),
        child_id=str(child.id),
        license_id=license_data["license_id"],
        generation=child.generation,
        tier=tier,
    )

    return child, license_data
