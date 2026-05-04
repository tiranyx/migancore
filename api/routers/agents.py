"""
Agent router — CRUD for autonomous agents + Spawning (Day 10).

Day 6 MVP: POST /v1/agents (create agent)
Day 10:    POST /v1/agents/{id}/spawn (spawn child agent)
           GET  /v1/agents/{id}/children (list direct children)
Day 13:    Letta Tier 3 wiring — create/spawn auto-provisions Letta persona agent
"""

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from deps.auth import get_current_user
from deps.db import get_db, set_tenant_context
from models import Agent, User, Tenant
from services.config_loader import load_soul_md
from services.letta import ensure_letta_agent

MAX_GENERATION_DEPTH = 5

router = APIRouter(prefix="/v1/agents", tags=["agents"])


class CreateAgentRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1024)
    model_version: str = Field(default="qwen2.5:7b-instruct-q4_K_M")
    system_prompt: str | None = Field(None, max_length=8192)
    visibility: str = Field(default="private")


class SpawnRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(..., min_length=1, max_length=255)
    template_id: str | None = Field(None, max_length=64)
    persona_overrides: dict | None = Field(None)


class AgentResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    name: str
    description: str | None
    model_version: str
    status: str
    created_at: str
    parent_agent_id: str | None = None
    generation: int = 0
    template_id: str | None = None
    persona_locked: bool = False


class AgentChildResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    name: str
    generation: int
    status: str
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_agent_or_404(
    db: AsyncSession,
    agent_id: str,
    tenant_id: uuid.UUID,
) -> Agent:
    """Fetch an agent by ID, scoped to tenant."""
    result = await db.execute(
        select(Agent).where(
            Agent.id == uuid.UUID(agent_id),
            Agent.tenant_id == tenant_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: CreateAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new agent for the current tenant."""
    tenant_id = current_user.tenant_id
    await set_tenant_context(db, str(tenant_id))

    # Day 11: Enforce max_agents per tenant
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one()

    agent_count_result = await db.execute(
        select(func.count(Agent.id)).where(
            Agent.tenant_id == tenant_id,
            Agent.status != "archived",
        )
    )
    current_agent_count = agent_count_result.scalar() or 0

    if current_agent_count >= tenant.max_agents:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent limit reached: {current_agent_count}/{tenant.max_agents} agents. "
                   f"Upgrade your plan to create more agents.",
        )

    agent = Agent(
        tenant_id=current_user.tenant_id,
        owner_user_id=current_user.id,
        name=data.name,
        slug=secrets.token_urlsafe(8),
        description=data.description,
        model_version=data.model_version,
        system_prompt=data.system_prompt,
        visibility=data.visibility,
        status="active",
    )
    db.add(agent)
    await db.commit()
    await set_tenant_context(db, str(current_user.tenant_id))
    await db.refresh(agent)

    # Day 13: Provision Letta Tier 3 persona agent (never blocks response on failure)
    soul_text = load_soul_md(None)
    letta_id = await ensure_letta_agent(
        migancore_agent_id=str(agent.id),
        agent_name=agent.name,
        soul_text=soul_text,
        persona_overrides=None,
        existing_letta_id=None,
    )
    if letta_id:
        agent.letta_agent_id = letta_id
        await db.commit()
        await set_tenant_context(db, str(current_user.tenant_id))
        await db.refresh(agent)

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        model_version=agent.model_version,
        status=agent.status,
        created_at=agent.created_at.isoformat(),
        generation=agent.generation,
    )


# IMPORTANT: List + genealogy + templates endpoints MUST come BEFORE /{agent_id} routes
# otherwise FastAPI matches "/genealogy" or "/templates" as agent_id and 500s on UUID parse.
# (Day 29 lesson — route declaration order matters in FastAPI.)

@router.get("/templates", response_model=list[dict])
async def list_personality_templates(
    current_user: User = Depends(get_current_user),
):
    """List available personality mode templates (Day 31).

    Used by chat.html spawn modal to populate "Choose Template" dropdown.
    Templates are merged into spawned child's persona_blob.
    """
    from services.config_loader import load_personality_templates
    cfg = load_personality_templates()
    templates = cfg.get("templates", {})
    return [
        {
            "id": tid,
            "name": t.get("name", tid),
            "description": t.get("description", ""),
            "voice": t.get("voice", ""),
            "tone": t.get("tone", ""),
            "values": t.get("values", []),
            "anti_patterns": t.get("anti_patterns", []),
            "additions": t.get("additions", ""),
        }
        for tid, t in templates.items()
    ]


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    include_archived: bool = False,
):
    """List all agents for the current tenant (Week 4 Day 29 — Spawn UI support).

    Returns agents ordered by generation (oldest core_brain first), then created_at.
    Used by chat.html sidebar agent switcher and dashboard genealogy view.
    """
    await set_tenant_context(db, str(current_user.tenant_id))

    stmt = select(Agent).where(Agent.tenant_id == current_user.tenant_id)
    if not include_archived:
        stmt = stmt.where(Agent.status != "archived")
    stmt = stmt.order_by(Agent.generation.asc(), Agent.created_at.asc())

    result = await db.execute(stmt)
    agents = result.scalars().all()

    return [
        AgentResponse(
            id=str(a.id),
            name=a.name,
            description=a.description,
            model_version=a.model_version,
            status=a.status,
            created_at=a.created_at.isoformat(),
            parent_agent_id=str(a.parent_agent_id) if a.parent_agent_id else None,
            generation=a.generation,
            template_id=a.template_id,
            persona_locked=a.persona_locked,
        )
        for a in agents
    ]


@router.get("/genealogy", response_model=list[dict])
async def get_genealogy(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full genealogy tree for current tenant (Day 30 — D3.js force-directed).

    Returns flat list of {id, name, parent_id, generation, template_id, status, created_at}.
    Frontend builds the tree from parent_id links.
    """
    await set_tenant_context(db, str(current_user.tenant_id))
    result = await db.execute(
        select(Agent).where(
            Agent.tenant_id == current_user.tenant_id,
            Agent.status != "archived",
        ).order_by(Agent.generation.asc(), Agent.created_at.asc())
    )
    agents = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "parent_id": str(a.parent_agent_id) if a.parent_agent_id else None,
            "generation": a.generation,
            "template_id": a.template_id,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
            "model_version": a.model_version,
        }
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get an agent by ID."""
    await set_tenant_context(db, str(current_user.tenant_id))

    agent = await _get_agent_or_404(db, agent_id, current_user.tenant_id)

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        model_version=agent.model_version,
        status=agent.status,
        created_at=agent.created_at.isoformat(),
        parent_agent_id=str(agent.parent_agent_id) if agent.parent_agent_id else None,
        generation=agent.generation,
        template_id=agent.template_id,
        persona_locked=agent.persona_locked,
    )


@router.post("/{agent_id}/spawn", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def spawn_agent(
    agent_id: str,
    data: SpawnRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Spawn a child agent from a parent agent.

    Inherits model_version, visibility, and system_prompt from parent.
    Merges parent's persona_blob with optional persona_overrides.
    Copies parent's tool grants to child.

    Day 11: Enforces max_agents, generation depth limit, and persona_lock.
    """
    tenant_id = current_user.tenant_id
    await set_tenant_context(db, str(tenant_id))

    # 1. Resolve parent
    parent = await _get_agent_or_404(db, agent_id, tenant_id)

    # 2. Check tenant limits
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one()

    agent_count_result = await db.execute(
        select(func.count(Agent.id)).where(
            Agent.tenant_id == tenant_id,
            Agent.status != "archived",
        )
    )
    current_agent_count = agent_count_result.scalar() or 0

    if current_agent_count >= tenant.max_agents:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agent limit reached: {current_agent_count}/{tenant.max_agents} agents. "
                   f"Upgrade your plan to spawn more agents.",
        )

    # 3. Check generation depth
    if parent.generation + 1 > MAX_GENERATION_DEPTH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Maximum generation depth reached ({MAX_GENERATION_DEPTH}). "
                   f"Cannot spawn beyond generation {MAX_GENERATION_DEPTH}.",
        )

    # 4. Check persona_lock
    if parent.persona_locked and data.persona_overrides:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Parent agent's persona is locked. Cannot apply persona overrides.",
        )

    # 5. Build persona blob: parent base + template (if any) + explicit overrides
    # Day 31: If template_id matches a personality template, apply it as middle layer
    child_persona = dict(parent.persona_blob or {})

    if data.template_id:
        from services.config_loader import get_personality_template
        tpl = get_personality_template(data.template_id)
        if tpl:
            # Merge template fields — these become the agent's default voice/tone/values
            for key in ("voice", "tone", "values", "anti_patterns", "additions", "name"):
                if key in tpl:
                    child_persona[key] = tpl[key]
            child_persona["_template_applied"] = data.template_id

    if data.persona_overrides:
        child_persona.update(data.persona_overrides)

    # 6. Determine template_id: explicit > parent's template > parent's id as fallback
    child_template_id = data.template_id or parent.template_id or str(parent.id)

    # 7. Create child agent
    child = Agent(
        tenant_id=tenant_id,
        owner_user_id=current_user.id,
        parent_agent_id=parent.id,
        name=data.name,
        slug=secrets.token_urlsafe(8),
        description=parent.description,
        generation=parent.generation + 1,
        model_version=parent.model_version,
        system_prompt=parent.system_prompt,
        persona_blob=child_persona,
        template_id=child_template_id,
        visibility=parent.visibility,
        status="active",
    )
    db.add(child)
    await db.commit()

    await set_tenant_context(db, str(tenant_id))
    await db.refresh(child)

    # Copy parent's tool grants to child (raw SQL, no ORM for junction table yet)
    await db.execute(
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
            "parent_id": str(parent.id),
            "user_id": str(current_user.id),
        },
    )
    await db.commit()

    # Day 13: Provision Letta persona for child, inheriting parent's merged persona_blob
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
        await db.commit()
        await set_tenant_context(db, str(tenant_id))
        await db.refresh(child)

    return AgentResponse(
        id=str(child.id),
        name=child.name,
        description=child.description,
        model_version=child.model_version,
        status=child.status,
        created_at=child.created_at.isoformat(),
        parent_agent_id=str(child.parent_agent_id),
        generation=child.generation,
        template_id=child.template_id,
        persona_locked=child.persona_locked,
    )


@router.get("/{agent_id}/children", response_model=list[AgentChildResponse])
async def list_agent_children(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List direct children of an agent."""
    await set_tenant_context(db, str(current_user.tenant_id))

    # Verify parent exists and belongs to tenant
    await _get_agent_or_404(db, agent_id, current_user.tenant_id)

    result = await db.execute(
        select(Agent).where(
            Agent.parent_agent_id == uuid.UUID(agent_id),
            Agent.tenant_id == current_user.tenant_id,
            Agent.status != "archived",
        ).order_by(Agent.created_at.desc())
    )
    children = result.scalars().all()

    return [
        AgentChildResponse(
            id=str(child.id),
            name=child.name,
            generation=child.generation,
            status=child.status,
            created_at=child.created_at.isoformat(),
        )
        for child in children
    ]
