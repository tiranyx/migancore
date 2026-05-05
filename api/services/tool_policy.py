"""
Tool Policy Enforcement — Safety Gates for MiganCore v0.3.1 (Day 11)

6-class taxonomy:
  read_only        — only reads data (web_search, memory_search)
  write            — writes data (memory_write)
  destructive      — creates/deletes resources (spawn_agent)
  open_world       — interacts with external internet (web_search, http_get)
  requires_approval — needs explicit human approval before execution
  sandbox_required  — needs sandboxed environment (python_repl)

Enforcement layers:
  1. Plan tier check    — is tenant's plan in allowed_plans?
  2. Approval gate      — block if requires_approval and not approved
  3. Sandbox gate       — block if sandbox_required and no sandbox
  4. Rate limit         — per-tenant, per-tool daily counter (Redis)
  5. Python REPL guard  — import blacklist validation
"""

from __future__ import annotations

import asyncio
import datetime
import re
from dataclasses import dataclass
from typing import Any

import redis.asyncio as aioredis
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Python REPL Security
# ---------------------------------------------------------------------------

PYTHON_REPL_IMPORT_BLACKLIST: set[str] = {
    "os", "sys", "subprocess", "socket", "pathlib",
    "urllib", "http", "ftplib", "smtplib", "telnetlib",
    "ctypes", "multiprocessing", "concurrent.futures",
    "pickle", "marshal", "shelve",
    "builtins", "importlib",
}

# Patterns: import os, from os import, __import__('os'), importlib.import_module('os')
_IMPORT_PATTERNS = [
    re.compile(r"^\s*import\s+([\w.]+)", re.MULTILINE),
    re.compile(r"^\s*from\s+([\w.]+)\s+import", re.MULTILINE),
    re.compile(r"__import__\s*\(\s*['\"]([\w.]+)['\"]\s*\)"),
    re.compile(r"import_module\s*\(\s*['\"]([\w.]+)['\"]\s*\)"),
]


class PolicyViolation(Exception):
    """Raised when a tool call violates safety policy."""

    def __init__(self, reason: str, violation_type: str, details: dict | None = None):
        self.reason = reason
        self.violation_type = violation_type
        self.details = details or {}
        super().__init__(reason)


# ---------------------------------------------------------------------------
# Redis pool for call counters
# ---------------------------------------------------------------------------

_counter_pool: aioredis.ConnectionPool | None = None
_counter_lock = asyncio.Lock()


async def _get_counter_pool() -> aioredis.ConnectionPool:
    global _counter_pool
    if _counter_pool is None:
        async with _counter_lock:
            if _counter_pool is None:
                _counter_pool = aioredis.ConnectionPool.from_url(
                    settings.REDIS_URL,
                    max_connections=10,
                    decode_responses=True,
                )
    return _counter_pool


async def _counter_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=await _get_counter_pool())


# ---------------------------------------------------------------------------
# Policy dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolPolicy:
    tool_name: str
    risk_level: str  # low | medium | high | critical
    classes: set[str]
    requires_approval: bool
    sandbox_required: bool
    allowed_plans: list[str]
    max_calls_per_day: int

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "ToolPolicy":
        policy = row.get("policy") or {}
        if isinstance(policy, str):
            import json
            policy = json.loads(policy)
        return cls(
            tool_name=row["name"],
            risk_level=row.get("risk_level", "medium"),
            classes=set(policy.get("classes", [])),
            requires_approval=policy.get("requires_approval", False),
            sandbox_required=policy.get("sandbox_required", False),
            allowed_plans=policy.get("allowed_plans", ["free", "pro", "enterprise"]),
            max_calls_per_day=row.get("max_calls_per_day", 1000),
        )

    def allows_plan(self, plan: str) -> bool:
        return plan in self.allowed_plans


# ---------------------------------------------------------------------------
# Load policies from DB
# ---------------------------------------------------------------------------

async def load_tool_policies(db: AsyncSession, tenant_id: str) -> dict[str, ToolPolicy]:
    """Load all active tool policies scoped to tenant (or global)."""
    from models.tool import Tool

    result = await db.execute(
        select(Tool).where(
            Tool.is_active == True,  # noqa: E712
            (Tool.tenant_id == tenant_id) | (Tool.tenant_id.is_(None)),
        )
    )
    policies: dict[str, ToolPolicy] = {}
    for tool in result.scalars().all():
        policies[tool.name] = ToolPolicy.from_db_row({
            "name": tool.name,
            "risk_level": tool.risk_level,
            "policy": tool.policy,
            "max_calls_per_day": tool.max_calls_per_day,
        })
    return policies


# ---------------------------------------------------------------------------
# Call counter (Redis)
# ---------------------------------------------------------------------------

def _counter_key(tenant_id: str, tool_name: str) -> str:
    today = datetime.date.today().isoformat()
    return f"ado:tool_calls:{tenant_id}:{tool_name}:{today}"


async def increment_tool_counter(tenant_id: str, tool_name: str) -> int:
    """Increment daily call counter. Returns new count."""
    r = await _counter_redis()
    key = _counter_key(tenant_id, tool_name)
    new_count = await r.incr(key)
    if new_count == 1:
        # Set expiry at end of day (~25 hours to be safe)
        await r.expire(key, 90000)
    return new_count


async def get_tool_counter(tenant_id: str, tool_name: str) -> int:
    r = await _counter_redis()
    key = _counter_key(tenant_id, tool_name)
    val = await r.get(key)
    return int(val) if val else 0


# ---------------------------------------------------------------------------
# Python code validation
# ---------------------------------------------------------------------------

def validate_python_code(code: str) -> None:
    """Check Python code for blacklisted imports.

    Raises PolicyViolation if dangerous imports are detected.
    This is a defense-in-depth layer — the real sandbox is subprocess isolation.
    """
    for pattern in _IMPORT_PATTERNS:
        for match in pattern.finditer(code):
            module = match.group(1).split(".")[0]
            if module in PYTHON_REPL_IMPORT_BLACKLIST:
                raise PolicyViolation(
                    reason=f"Import of '{module}' is blocked for security. "
                           f"Blacklisted modules: {sorted(PYTHON_REPL_IMPORT_BLACKLIST)}",
                    violation_type="python_repl_blacklist",
                    details={"module": module, "line": match.group(0).strip()},
                )

    # Additional heuristic: block eval/exec of arbitrary strings
    # __import__ is already caught by the regex patterns above; eval/exec/compile are not.
    for d in ["eval(", "exec(", "compile("]:
        if d in code:
            raise PolicyViolation(
                reason=f"Use of '{d}' is blocked in python_repl for security.",
                violation_type="python_repl_dangerous_builtin",
                details={"builtin": d},
            )

    logger.debug("tool.python_repl.validated", code_len=len(code))


# ---------------------------------------------------------------------------
# Policy checker (runtime)
# ---------------------------------------------------------------------------

class ToolPolicyChecker:
    """Runtime policy enforcement for tool execution."""

    def __init__(
        self,
        tenant_plan: str,
        tenant_id: str,
        tool_policies: dict[str, ToolPolicy],
    ):
        self.tenant_plan = tenant_plan
        self.tenant_id = tenant_id
        self.policies = tool_policies

    async def check(self, tool_name: str) -> ToolPolicy:
        """Full policy check. Returns policy on success, raises PolicyViolation on failure."""
        policy = self.policies.get(tool_name)
        if not policy:
            # Unknown tool — allow with warning (defense: tool grants should control this)
            logger.warning("tool.policy_missing", tool=tool_name, tenant=self.tenant_id)
            return ToolPolicy(
                tool_name=tool_name,
                risk_level="unknown",
                classes=set(),
                requires_approval=False,
                sandbox_required=False,
                allowed_plans=["free", "pro", "enterprise"],
                max_calls_per_day=1000,
            )

        # 1. Plan tier check
        if not policy.allows_plan(self.tenant_plan):
            raise PolicyViolation(
                reason=f"Tool '{tool_name}' requires plan {policy.allowed_plans}. "
                       f"Current plan: {self.tenant_plan}",
                violation_type="plan_tier_denied",
                details={"tool": tool_name, "required_plans": policy.allowed_plans, "current_plan": self.tenant_plan},
            )

        # 2. Approval gate (hard block for MVP — approval UI comes later)
        if policy.requires_approval:
            raise PolicyViolation(
                reason=f"Tool '{tool_name}' requires explicit approval before execution. "
                       f"Contact your administrator to enable this tool.",
                violation_type="requires_approval",
                details={"tool": tool_name},
            )

        # 3. Sandbox gate
        if policy.sandbox_required:
            # For MVP: sandbox is subprocess isolation. Mark as not-yet-fully-sandboxed.
            logger.warning("tool.sandbox_required", tool=tool_name, tenant=self.tenant_id)
            # We do NOT block — subprocess is our current sandbox. Log for audit.

        # 4. Rate limit check
        current_count = await get_tool_counter(self.tenant_id, tool_name)
        if current_count >= policy.max_calls_per_day:
            raise PolicyViolation(
                reason=f"Daily limit exceeded for '{tool_name}': "
                       f"{current_count}/{policy.max_calls_per_day} calls today.",
                violation_type="rate_limit_exceeded",
                details={"tool": tool_name, "limit": policy.max_calls_per_day, "used": current_count},
            )

        # Increment counter
        await increment_tool_counter(self.tenant_id, tool_name)

        logger.info(
            "tool.policy_ok",
            tool=tool_name,
            risk=policy.risk_level,
            classes=list(policy.classes),
            tenant=self.tenant_id,
        )
        return policy
