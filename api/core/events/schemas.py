"""
Event schemas — Pydantic models for type-safe event payloads.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ConversationNew(BaseModel):
    conversation_id: str
    tenant_id: str
    user_message: str
    agent_id: Optional[str] = None
    session_id: Optional[str] = None


class FeedbackReceived(BaseModel):
    feedback_id: str
    tenant_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    message_id: Optional[str] = None


class CodeExecuted(BaseModel):
    execution_id: str
    tenant_id: str
    success: bool
    score: float = Field(..., ge=-1.0, le=1.0)
    feeling: str = ""
    error_type: Optional[str] = None
    elapsed_ms: int = 0
    code_length: int = 0
    lesson_saved: bool = False
    lesson_bucket: Optional[str] = None


class ReflectionCreated(BaseModel):
    reflection_key: str
    content: str
    category: str = "general"  # learn, fail, need, propose


class ProposalSubmitted(BaseModel):
    proposal_id: str
    title: str
    risk_level: str = "low"
    source: str = "dev_organ"
    component: Optional[str] = None


class EvalGateFailed(BaseModel):
    test_name: str
    score: float
    threshold: float
    violations: list[str] = Field(default_factory=list)


class MemoryUpdated(BaseModel):
    tenant_id: str
    agent_id: str
    namespace: str
    key: str
    operation: str  # write, delete


class KGEntityExtracted(BaseModel):
    tenant_id: str
    conversation_id: str
    entity_name: str
    entity_type: str
    mention_count: int = 1


class AgentSpawned(BaseModel):
    agent_id: str
    tenant_id: str
    parent_agent_id: Optional[str] = None
    generation: int = 0
    name: str = ""


class AgentTerminated(BaseModel):
    agent_id: str
    tenant_id: str
    reason: str = ""
    final_knowledge_extracted: bool = False
