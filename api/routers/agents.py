"""
Agent router — CRUD for autonomous agents.

Day 6 MVP: POST /v1/agents (create agent)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deps.auth import get_current_user
from deps.db import get_db, set_tenant_context
from models import Agent, User

router = APIRouter(prefix="/v1/agents", tags=["agents"])


class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1024)
    model_version: str = Field(default="qwen2.5:7b-instruct-q4_K_M")
    system_prompt: str | None = Field(None, max_length=8192)


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    model_version: str
    status: str
    created_at: str


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
        name=data.name,
        description=data.description,
        model_version=data.model_version,
        system_prompt=data.system_prompt,
        status="active",
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        model_version=agent.model_version,
        status=agent.status,
        created_at=agent.created_at.isoformat(),
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get an agent by ID."""
    await set_tenant_context(db, str(current_user.tenant_id))

    result = await db.execute(
        select(Agent).where(
            Agent.id == uuid.UUID(agent_id),
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        model_version=agent.model_version,
        status=agent.status,
        created_at=agent.created_at.isoformat(),
    )
