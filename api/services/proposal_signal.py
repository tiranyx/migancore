"""
M1.7 — Proposal Signal Collector.

Converts system events into Dev Organ improvement proposals automatically.
MiganCore observes its own failures and patterns, then generates proposals
for the Playground queue without Fahmi having to notice them manually.

Signal sources:
  - tool_failure(tool_id, error)    → propose fix for broken tool
  - low_quality_response(msg_id)    → propose training data improvement
  - missing_skill(capability_name)  → propose new tool/skill
  - owner_command(text)             → convert explicit request into proposal
  - eval_failure(eval_name, score)  → propose training cycle improvement

Proposals are stored via the sandbox router's DB layer (direct DB write,
no HTTP round-trip needed since we share the same process).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.proposal import DevOrganProposal
from services.dev_organ import classify_risk

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Public signal entry points — call these from tool executor, chat router, etc.
# ---------------------------------------------------------------------------


async def signal_tool_failure(
    db: AsyncSession,
    tool_id: str,
    error: str,
    context: dict[str, Any] | None = None,
) -> DevOrganProposal:
    """Generate a proposal when a tool fails."""

    title = f"Fix broken tool: {tool_id}"
    problem = (
        f"Tool `{tool_id}` raised an error during execution: {error[:300]}"
    )
    hypothesis = (
        f"The tool handler for `{tool_id}` has a bug or dependency issue. "
        "Inspect the handler, add defensive error handling, write a focused test, "
        "and verify the fix in sandbox before promoting."
    )
    touched_paths = [f"api/services/tool_executor.py", f"api/tools/{tool_id}.py"]
    tests = [f"api/tests/test_tool_{tool_id}.py"]
    rollback_plan = f"Revert to previous tool_executor.py — git revert HEAD on tool_executor."

    return await _create_proposal(
        db=db,
        title=title,
        problem=problem,
        hypothesis=hypothesis,
        touched_paths=touched_paths,
        tests=tests,
        rollback_plan=rollback_plan,
        source="tool_failure",
        metadata={"tool_id": tool_id, "error": error[:500], **(context or {})},
    )


async def signal_missing_skill(
    db: AsyncSession,
    capability_name: str,
    user_request: str = "",
) -> DevOrganProposal:
    """Generate a proposal when the brain can't do something the user asked for."""

    title = f"Add new skill: {capability_name}"
    problem = (
        f"User requested a capability that does not exist: '{capability_name}'. "
        f"Original request fragment: {user_request[:200]}"
    )
    hypothesis = (
        f"Build a new tool `{capability_name.lower().replace(' ', '_')}` that satisfies "
        "this class of user requests. Define schema in skills.json, implement handler in "
        "tool_executor.py, write tests, and run contract validation."
    )
    touched_paths = ["config/skills.json", "api/services/tool_executor.py"]
    tests = ["api/tests/test_new_skill.py"]
    rollback_plan = "Remove the new skill entry from skills.json and redeploy — no DB change needed."

    return await _create_proposal(
        db=db,
        title=title,
        problem=problem,
        hypothesis=hypothesis,
        touched_paths=touched_paths,
        tests=tests,
        rollback_plan=rollback_plan,
        source="auto",
        metadata={"capability": capability_name, "user_request": user_request[:500]},
    )


async def signal_owner_command(
    db: AsyncSession,
    command_text: str,
    agent_id: str = "core_brain",
) -> DevOrganProposal:
    """Convert an explicit improvement directive from Fahmi into a proposal."""

    title = f"Owner directive: {command_text[:80]}"
    problem = f"Creator issued an explicit improvement command: '{command_text}'"
    hypothesis = (
        "Translate this owner directive into a concrete system change. "
        "Identify affected files, write tests, validate, and prepare for review."
    )

    return await _create_proposal(
        db=db,
        title=title,
        problem=problem,
        hypothesis=hypothesis,
        touched_paths=[],
        tests=[],
        rollback_plan="To be determined after analysis.",
        source="owner_command",
        metadata={"command": command_text, "agent_id": agent_id},
    )


async def signal_eval_failure(
    db: AsyncSession,
    eval_name: str,
    score: float,
    gate_value: float,
    cycle_id: str = "",
) -> DevOrganProposal:
    """Generate a proposal when a model eval fails a promotion gate."""

    title = f"Improve eval: {eval_name} ({score:.3f} < {gate_value:.3f})"
    problem = (
        f"Eval `{eval_name}` scored {score:.3f}, below the gate of {gate_value:.3f}. "
        f"Training cycle: {cycle_id or 'unknown'}."
    )
    hypothesis = (
        f"Generate targeted training pairs for `{eval_name}` category. "
        "A minimum of 50 high-quality pairs typically improves a category score by +0.05 to +0.13 "
        "(empirical from Cycles 3–5). Export dataset, retrain, re-evaluate."
    )
    touched_paths = [
        f"training/generate_{eval_name}_pairs.py",
        "training/export_cycle_dataset.py",
    ]
    tests = ["training/run_identity_eval.py"]
    rollback_plan = f"Keep current brain tag. Do not hot-swap until gate passes."

    return await _create_proposal(
        db=db,
        title=title,
        problem=problem,
        hypothesis=hypothesis,
        touched_paths=touched_paths,
        tests=tests,
        rollback_plan=rollback_plan,
        source="eval_failure",
        metadata={
            "eval_name": eval_name,
            "score": score,
            "gate": gate_value,
            "cycle_id": cycle_id,
        },
    )


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


async def _create_proposal(
    db: AsyncSession,
    title: str,
    problem: str,
    hypothesis: str,
    touched_paths: list[str],
    tests: list[str],
    rollback_plan: str,
    source: str,
    metadata: dict[str, Any],
    created_by: str = "core_brain",
) -> DevOrganProposal:
    risk = classify_risk(touched_paths).value

    row = DevOrganProposal(
        title=title,
        problem=problem,
        hypothesis=hypothesis,
        touched_paths=touched_paths,
        tests=tests,
        rollback_plan=rollback_plan,
        source=source,
        risk_level=risk,
        stage="proposed",
        gate_results=[],
        metadata_=metadata,
        created_by=created_by,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    logger.info(
        "dev_organ.proposal.auto_created",
        proposal_id=str(row.id),
        source=source,
        title=title[:60],
        risk=risk,
    )
    return row
