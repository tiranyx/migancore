"""
Reflection Daemon — Sprint 2 Day 75

Migan refleksi diri akhir hari (atau periodik) — "synaptic pruning" primitive.
Query last N hours: conversation count, tool calls, code_lab scores, error patterns.
Generate reflection via local LLM → write to `nafs` bucket (self-awareness).

Vision tags:
- Nafs (self-awareness, recursive feedback loop)
- Pruning (biomimetic — review boros vs efisien)
- Adaptive Design (not every hour reflect — only when meaningful activity)

API:
  POST /v1/admin/reflection/trigger   — manual trigger reflection now
  GET  /v1/admin/reflection/latest    — read most recent reflection

Future: wire to cron / lifespan background task (after MVP validated).
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/admin/reflection", tags=["admin-reflection"])


def _require_admin(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")) -> None:
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Admin endpoints not configured")
    if not x_admin_key or x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")


# ---------------------------------------------------------------------------
# Activity gathering — query last N hours of brain activity
# ---------------------------------------------------------------------------
async def gather_recent_activity(
    tenant_id: str,
    agent_id: str,
    hours_back: int = 24,
) -> dict:
    """Pull last N hours of brain activity for reflection input.

    Sources (read-only):
      - nafs bucket recent entries (from Code Lab failures)
      - hikmah bucket recent entries (from Code Lab successes)
      - conversation count via DB (if accessible)

    Returns compact summary dict for LLM prompt.
    """
    from services.memory import memory_list

    cutoff_ts = time.time() - (hours_back * 3600)

    summary = {
        "hours_back": hours_back,
        "nafs_lessons": [],  # failures / self-awareness
        "hikmah_lessons": [],  # successes / wisdom
        "stats": {
            "code_lab_failures": 0,
            "code_lab_successes": 0,
            "buckets_active": [],
        },
    }

    # Gather from nafs + hikmah buckets via Redis KV memory_list
    for bucket in ("nafs", "hikmah"):
        try:
            entries = await memory_list(
                tenant_id=tenant_id,
                agent_id=agent_id,
                namespace=bucket,
                limit=50,
            )
            recent = []
            for key, value in entries.items():
                # Code Lab entries have timestamp in key: codelab_<unix_ts>_<hash>
                if key.startswith("codelab_"):
                    try:
                        ts = int(key.split("_")[1])
                        if ts >= cutoff_ts:
                            recent.append({"key": key, "summary": value[:400]})
                    except (IndexError, ValueError):
                        continue
            target_list = "hikmah_lessons" if bucket == "hikmah" else "nafs_lessons"
            summary[target_list] = recent
            if bucket == "nafs":
                summary["stats"]["code_lab_failures"] = len(recent)
            elif bucket == "hikmah":
                summary["stats"]["code_lab_successes"] = len(recent)
            if recent:
                summary["stats"]["buckets_active"].append(bucket)
        except Exception as exc:
            logger.warning("reflection.bucket_read_fail", bucket=bucket, error=str(exc))

    return summary


# ---------------------------------------------------------------------------
# Reflection generation via local Ollama (zero cost)
# ---------------------------------------------------------------------------
async def generate_reflection(activity: dict, agent_id: str) -> str:
    """Generate human-readable reflection via local Ollama brain.

    Format: short paragraph, in Indonesian, written in first-person as Migan.
    """
    from services.ollama import OllamaClient

    # Build prompt
    nafs_count = len(activity["nafs_lessons"])
    hikmah_count = len(activity["hikmah_lessons"])
    hours = activity["hours_back"]

    nafs_lines = "\n".join(
        f"  - {l['summary'][:150]}" for l in activity["nafs_lessons"][:3]
    )
    hikmah_lines = "\n".join(
        f"  - {l['summary'][:150]}" for l in activity["hikmah_lessons"][:3]
    )

    prompt = f"""Refleksi diri {hours} jam terakhir.

Aktivitas Code Lab:
- {hikmah_count} success pattern → bucket hikmah:
{hikmah_lines or '  (tidak ada)'}
- {nafs_count} kegagalan substansial → bucket nafs:
{nafs_lines or '  (tidak ada)'}

Tugasmu: tulis refleksi 1 paragraf (3-5 kalimat) sebagai Mighan-Core, first-person.
Fokus pada:
- Apa pattern yang dipelajari?
- Apa kelemahan yang muncul?
- Apa yang akan kucoba berbeda besok?

Voice: direct, kasual sedikit, akrab dengan Fahmi sebagai pencipta.
Tanpa intro generic ("Hari ini..."). Langsung ke insight.
"""

    try:
        async with OllamaClient() as client:
            out = await client.chat(
                model="migancore:0.7c",
                messages=[
                    {"role": "system", "content": "Kamu Mighan-Core. Voice direct, akrab dengan Fahmi (pencipta). Refleksi singkat berbasis fakta."},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.6, "num_predict": 250},
            )
        text = ((out or {}).get("message") or {}).get("content") or ""
        return text.strip()
    except Exception as exc:
        logger.error("reflection.generate_fail", error=str(exc))
        return (
            f"Refleksi {hours}h: {hikmah_count} success + {nafs_count} fail. "
            f"(LLM generation failed: {exc})"
        )


# ---------------------------------------------------------------------------
# Persist reflection — write to nafs bucket with timestamped key
# ---------------------------------------------------------------------------
async def save_reflection(
    tenant_id: str,
    agent_id: str,
    reflection_text: str,
    activity_summary: dict,
) -> str:
    from services.memory import memory_write as kv_write

    key = f"reflection_{int(time.time())}"
    full_value = (
        f"[Reflection — {activity_summary['hours_back']}h | "
        f"{activity_summary['stats']['code_lab_successes']} success, "
        f"{activity_summary['stats']['code_lab_failures']} fail]\n\n"
        f"{reflection_text}"
    )
    await kv_write(
        tenant_id=tenant_id,
        agent_id=agent_id,
        key=key,
        value=full_value,
        namespace="nafs",
        ttl_days=180,  # reflection lives longer than individual lessons
    )
    logger.info("reflection.saved", key=key, agent=agent_id, hours=activity_summary["hours_back"])
    return key


# ---------------------------------------------------------------------------
# Adaptive trigger: should we reflect at all?
# ---------------------------------------------------------------------------
def should_reflect(activity: dict, hours_back: int) -> tuple[bool, str]:
    """Adaptive decision per Adaptive Design Doctrine — NOT every interval reflect.

    Reflect only when meaningful activity:
      - At least 1 hikmah or nafs entry
      - OR hours_back ≥ 24 (daily anchor)
    """
    has_any_lesson = bool(activity["hikmah_lessons"] or activity["nafs_lessons"])
    if hours_back >= 24:
        return True, "daily anchor (24h+)"
    if has_any_lesson:
        return True, "meaningful activity"
    return False, "no activity since last reflection"


# ---------------------------------------------------------------------------
# Public API endpoints
# ---------------------------------------------------------------------------
class ReflectionTriggerRequest(BaseModel):
    hours_back: int = 24
    force: bool = False
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None


# Core_brain agent (Mighan-Core in production)
CORE_BRAIN_ID = "cb3ebd3b-4c31-4af7-8470-25c2011c0974"
SYSTEM_TENANT = "00000000-0000-0000-0000-000000000000"


@router.post("/trigger", dependencies=[Depends(_require_admin)])
async def trigger_reflection(body: ReflectionTriggerRequest):
    """Manually trigger reflection cycle. Future: cron job calls this."""
    tenant_id = body.tenant_id or SYSTEM_TENANT
    agent_id = body.agent_id or CORE_BRAIN_ID
    hours_back = max(1, min(body.hours_back, 168))  # cap at 1 week

    activity = await gather_recent_activity(tenant_id, agent_id, hours_back)

    if not body.force:
        should, reason = should_reflect(activity, hours_back)
        if not should:
            return {
                "status": "skipped",
                "reason": reason,
                "activity_summary": activity["stats"],
            }

    reflection_text = await generate_reflection(activity, agent_id)
    key = await save_reflection(tenant_id, agent_id, reflection_text, activity)

    return {
        "status": "reflected",
        "key": key,
        "reflection": reflection_text,
        "activity_summary": activity["stats"],
        "hours_back": hours_back,
    }


@router.get("/latest", dependencies=[Depends(_require_admin)])
async def latest_reflection(limit: int = 5, agent_id: Optional[str] = None):
    """Return most recent N reflections from nafs bucket."""
    from services.memory import memory_list

    tid = SYSTEM_TENANT
    aid = agent_id or CORE_BRAIN_ID
    entries = await memory_list(tenant_id=tid, agent_id=aid, namespace="nafs", limit=200)

    reflections = []
    for key, value in entries.items():
        if not key.startswith("reflection_"):
            continue
        try:
            ts = int(key.split("_")[1])
        except (IndexError, ValueError):
            continue
        reflections.append({
            "key": key,
            "timestamp": ts,
            "datetime": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
            "content": value,
        })
    reflections.sort(key=lambda r: -r["timestamp"])
    return {"count": len(reflections), "reflections": reflections[:limit]}
