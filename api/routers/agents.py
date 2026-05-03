"""
Agent router — CRUD for autonomous agents + Spawning (Day 10).

Day 6 MVP: POST /v1/agents (create agent)
Day 10:    POST /v1/agents/{id}/spawn (spawn child agent)
           GET  /v1/agents/{id}/children (list direct children)
"""

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from deps.auth import get_current_user
from deps.db import get_db, set_tenant_context
from models import Agent, User

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
    await set_tenant_context(db, str(current_user.tenant_id))

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
    # Re-set tenant context before refresh since SET LOCAL is cleared on commit
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
    """
    tenant_id = current_user.tenant_id
    await set_tenant_context(db, str(tenant_id))

    # 1. Resolve parent
    parent = await _get_agent_or_404(db, agent_id, tenant_id)

    # 2. Build persona blob: parent base + overrides
    child_persona = dict(parent.persona_blob or {})
    if data.persona_overrides:
        child_persona.update(data.persona_overrides)

    # 3. Determine template_id: explicit > parent's template > parent's id as fallback
    child_template_id = data.template_id or parent.template_id or str(parent.id)

    # 4. Create child agent
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

    # 5. Re-set tenant context after commit
    await set_tenant_context(db, str(tenant_id))
    await db.refresh(child)

    # 6. Copy parent's tool grants to child (raw SQL, no ORM for junction table yet)
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
