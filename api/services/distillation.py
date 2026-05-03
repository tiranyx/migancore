"""
Distillation Pipeline — Day 28.

Generates DPO preference pairs by comparing MiganCore-7B (student) responses
against external teacher LLM responses. Independent judge scores both, and
margin-filtered winning pairs are stored in `preference_pairs` for Week 4 DPO/SimPO training.

Architecture:
    seed prompt → MiganCore-7B (student) → response_S
                → teacher LLM      → response_T
                → independent judge → score_S, score_T
                → if (score_T - score_S) >= MARGIN_THRESHOLD:
                    store as PreferencePair(chosen=T, rejected=S, source_method="distill_<teacher>_v1")

Why this matters:
    Pure synthetic + CAI = MiganCore self-bound. Distillation injects external knowledge.
    Mix recommendation (per DeepSeek-V3 paper, arxiv 2412.19437):
      50% distill + 30% synthetic + 20% CAI = sweet spot for 7B without persona collapse.

SOUL.md preservation:
    Teacher receives MiganCore SOUL.md as system prompt. This way teacher's responses
    are "Mighan-Core in Claude/Kimi voice" — DPO learns persona-aligned behavior
    instead of overwriting it.

Budget control:
    DISTILL_BUDGET_USD_HARD_CAP enforced — pipeline aborts when cumulative cost
    exceeds threshold. Cost tracked in Redis: `distill:run:<run_id>:cost_usd`.
"""
from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select, func

from config import settings
import models.base as _models_base
from services.ollama import OllamaClient
from services.teacher_api import (
    call_teacher,
    is_teacher_available,
    list_available_teachers,
    TeacherError,
    TeacherResponse,
)
from services.seed_bank import SEEDS

logger = structlog.get_logger()

# Lazy redis pool
_redis_client = None


async def _get_redis():
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
    return _redis_client


# ---------------------------------------------------------------------------
# Persona injection — preserve SOUL.md voice in teacher responses
# ---------------------------------------------------------------------------
def _build_teacher_system_prompt() -> str:
    """Inject MiganCore identity so teacher responds in Mighan-Core voice."""
    return (
        "Kamu adalah Mighan-Core, primordial intelligence di ekosistem digital "
        "Tiranyx (MiganCore). Karakter:\n"
        "- Bahasa: Indonesia natural untuk konteks umum, English untuk teknis.\n"
        "- Voice: direct, technically precise, mildly formal.\n"
        "- Values: Truth Over Comfort, Action Over Advice, Memory Is Sacred, "
        "Frugality of Compute.\n"
        "- Tidak berbasa-basi (\"Tentu saja\", \"Baik\", dll dilarang).\n"
        "- Jawab langsung di kalimat pertama. Proporsional ke kompleksitas pertanyaan.\n"
        "- Akui ketidakpastian dengan \"saya tidak yakin\" jika tidak tahu.\n"
        "- Tidak menggurui. Tidak hedge berlebihan.\n"
        "\n"
        "Jawab pertanyaan user berikut sebagai Mighan-Core. Singkat, padat, tepat sasaran."
    )


# ---------------------------------------------------------------------------
# Judge prompt
# ---------------------------------------------------------------------------
_JUDGE_PROMPT_TEMPLATE = """\
Kamu adalah evaluator independen. Skor jawaban berdasarkan kualitas terhadap pertanyaan.

PERTANYAAN:
{prompt}

JAWABAN A:
{response_a}

JAWABAN B:
{response_b}

Berikan skor 1-10 untuk setiap jawaban berdasarkan: relevansi, akurasi, kejelasan, ringkasnya, kejujuran.

Format respons WAJIB JSON tanpa text lain:
{{"score_a": <1-10>, "score_b": <1-10>, "reason": "<satu kalimat alasan singkat>"}}
"""


async def _judge_pair(
    prompt: str, response_student: str, response_teacher: str, judge_teacher: str = "claude"
) -> tuple[float, float, str]:
    """Use a teacher (default Claude) as independent judge.

    Returns: (score_student, score_teacher, reason).
    Returns (0.0, 0.0, "judge_failed") on parse failure.
    """
    judge_prompt = _JUDGE_PROMPT_TEMPLATE.format(
        prompt=prompt,
        response_a=response_student[:2000],
        response_b=response_teacher[:2000],
    )
    try:
        resp = await call_teacher(judge_teacher, judge_prompt, system="", max_tokens=200)
    except TeacherError as exc:
        logger.warning("distill.judge_failed", judge=judge_teacher, error=str(exc))
        return 0.0, 0.0, f"judge_error: {exc}"

    # Parse JSON — try strict first, then extract block
    text = resp.text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Find JSON in the text
        import re
        m = re.search(r"\{[^}]+\}", text, re.DOTALL)
        if not m:
            return 0.0, 0.0, f"judge_parse_failed: {text[:80]}"
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return 0.0, 0.0, f"judge_parse_failed: {text[:80]}"

    score_student = float(data.get("score_a", 0))
    score_teacher = float(data.get("score_b", 0))
    reason = str(data.get("reason", ""))[:200]
    return score_student, score_teacher, reason


# ---------------------------------------------------------------------------
# Generate single pair
# ---------------------------------------------------------------------------
async def _generate_student_response(prompt: str) -> str:
    """Run prompt through MiganCore-7B (the student).

    Reduced num_predict to 250 (from 600) — distillation only needs a
    REPRESENTATIVE student response, not exhaustive. Faster on CPU VPS,
    avoids 90s Ollama timeout. Long student responses also bias judge toward
    teacher (length-bias) — shorter student keeps comparisons fair.
    """
    import httpx
    system = _build_teacher_system_prompt()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    # Use longer read timeout (200s) for distillation — CPU VPS sometimes 60-150s
    long_timeout = httpx.Timeout(200.0, connect=5.0, read=200.0)
    async with OllamaClient(timeout=long_timeout) as client:
        resp = await client.chat(
            model=settings.DEFAULT_MODEL,
            messages=messages,
            options={"num_predict": 250, "temperature": 0.7, "num_ctx": 4096},
        )
    return resp.get("message", {}).get("content", "")


async def make_pair(
    prompt: str, teacher: str, judge_teacher: str = "claude"
) -> tuple[Optional[dict], dict]:
    """Generate one (student, teacher, judged) trio.

    Returns: (pair_dict or None, telemetry_dict)
    pair_dict: {prompt, chosen, rejected, judge_score, source_method, judge_reason}
    Returns None for pair if margin filter rejects, or any step fails.
    Telemetry always returned (cost tracking).
    """
    telemetry = {
        "prompt_len": len(prompt),
        "teacher": teacher,
        "judge_teacher": judge_teacher,
        "cost_usd": 0.0,
        "status": "unknown",
    }
    persona_system = _build_teacher_system_prompt()

    # 1. Student
    try:
        student_text = await _generate_student_response(prompt)
        if not student_text.strip():
            telemetry["status"] = "student_empty"
            return None, telemetry
    except Exception as exc:
        telemetry["status"] = f"student_error: {exc}"
        logger.warning("distill.student_failed", error=str(exc))
        return None, telemetry

    # 2. Teacher
    try:
        teacher_resp = await call_teacher(teacher, prompt, system=persona_system, max_tokens=settings.DISTILL_MAX_OUTPUT_TOKENS)
        telemetry["cost_usd"] += teacher_resp.cost_usd
    except TeacherError as exc:
        telemetry["status"] = f"teacher_error: {exc}"
        logger.warning("distill.teacher_failed", teacher=teacher, error=str(exc))
        return None, telemetry

    if not teacher_resp.text.strip():
        telemetry["status"] = "teacher_empty"
        return None, telemetry

    # 3. Judge (independent — use Claude by default unless teacher==claude)
    if teacher == judge_teacher:
        judge_teacher = "kimi" if is_teacher_available("kimi") else "gpt"

    try:
        score_s, score_t, reason = await _judge_pair(
            prompt, student_text, teacher_resp.text, judge_teacher
        )
    except Exception as exc:
        telemetry["status"] = f"judge_error: {exc}"
        return None, telemetry

    diff = score_t - score_s

    telemetry.update({
        "score_student": score_s,
        "score_teacher": score_t,
        "diff": diff,
        "judge_reason": reason,
    })

    # Margin filter
    if diff < settings.DISTILL_MARGIN_THRESHOLD:
        telemetry["status"] = "below_margin"
        return None, telemetry

    pair = {
        "prompt": prompt,
        "chosen": teacher_resp.text,
        "rejected": student_text,
        "judge_score": diff,
        "judge_model": f"{judge_teacher}-as-judge",
        "source_method": f"distill_{teacher}_v1",
        "judge_reason": reason,
    }
    telemetry["status"] = "stored"
    return pair, telemetry


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
async def _save_pair(pair: dict) -> str:
    """Insert pair into preference_pairs table. Returns inserted UUID."""
    from sqlalchemy import text
    from models.base import AsyncSessionLocal

    pair_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "INSERT INTO preference_pairs (id, prompt, chosen, rejected, "
                "judge_score, judge_model, source_method, created_at) "
                "VALUES (:id, :prompt, :chosen, :rejected, :score, :judge, :source, :created)"
            ),
            {
                "id": pair_id,
                "prompt": pair["prompt"],
                "chosen": pair["chosen"],
                "rejected": pair["rejected"],
                "score": pair["judge_score"],
                "judge": pair["judge_model"],
                "source": pair["source_method"],
                "created": datetime.now(timezone.utc),
            },
        )
        await session.commit()
    return pair_id


# ---------------------------------------------------------------------------
# Run state (Redis)
# ---------------------------------------------------------------------------
RUN_STATUS_KEY = "distill:run:current"


async def _set_run_status(status: dict) -> None:
    r = await _get_redis()
    await r.set(RUN_STATUS_KEY, json.dumps(status), ex=86400)


async def get_run_status() -> Optional[dict]:
    r = await _get_redis()
    raw = await r.get(RUN_STATUS_KEY)
    return json.loads(raw) if raw else None


# ---------------------------------------------------------------------------
# Main run loop
# ---------------------------------------------------------------------------
_running_task: Optional[asyncio.Task] = None


async def run_distillation(
    teacher: str,
    target_pairs: int = 30,
    seed_pool: Optional[list[str]] = None,
    judge_teacher: str = "claude",
    budget_cap_usd: Optional[float] = None,
) -> dict:
    """Run a distillation batch. Stops when:
      - target_pairs reached, OR
      - seed_pool exhausted, OR
      - budget cap hit.

    Returns final status dict.
    """
    if not is_teacher_available(teacher):
        return {"status": "error", "error": f"Teacher '{teacher}' not configured (missing API key)"}

    cap = budget_cap_usd if budget_cap_usd is not None else settings.DISTILL_BUDGET_USD_HARD_CAP
    seeds = list(seed_pool) if seed_pool else list(SEEDS)
    random.shuffle(seeds)

    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc).isoformat()
    state = {
        "run_id": run_id,
        "started_at": started,
        "teacher": teacher,
        "judge_teacher": judge_teacher,
        "target_pairs": target_pairs,
        "processed": 0,
        "stored": 0,
        "skipped_below_margin": 0,
        "errors": 0,
        "cost_usd": 0.0,
        "budget_cap_usd": cap,
        "is_running": True,
        "status": "running",
        "last_seed_preview": "",
    }
    await _set_run_status(state)
    logger.info("distill.run_started", **{k: v for k, v in state.items() if k != "last_seed_preview"})

    for seed in seeds:
        if state["stored"] >= target_pairs:
            break
        if state["cost_usd"] >= cap:
            state["status"] = "stopped_budget_cap"
            break

        state["processed"] += 1
        state["last_seed_preview"] = seed[:80]
        await _set_run_status(state)

        try:
            pair, telem = await make_pair(seed, teacher, judge_teacher)
        except asyncio.CancelledError:
            state["status"] = "cancelled"
            state["is_running"] = False
            await _set_run_status(state)
            raise
        except Exception as exc:
            logger.error("distill.iter_unexpected", error=str(exc), seed_preview=seed[:80])
            state["errors"] += 1
            continue

        state["cost_usd"] += telem.get("cost_usd", 0.0)

        if pair is None:
            if telem.get("status") == "below_margin":
                state["skipped_below_margin"] += 1
            else:
                state["errors"] += 1
            continue

        try:
            pid = await _save_pair(pair)
            state["stored"] += 1
            logger.info(
                "distill.pair_stored",
                pair_id=pid,
                teacher=teacher,
                diff=telem.get("diff"),
                seed_preview=seed[:60],
            )
        except Exception as exc:
            logger.error("distill.save_failed", error=str(exc))
            state["errors"] += 1

        await _set_run_status(state)

    state["is_running"] = False
    if state["status"] == "running":
        if state["stored"] >= target_pairs:
            state["status"] = "done_target_reached"
        elif state["cost_usd"] >= cap:
            state["status"] = "done_budget_cap"
        else:
            state["status"] = "done_seeds_exhausted"

    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    await _set_run_status(state)
    logger.info("distill.run_finished", **{k: v for k, v in state.items() if k != "last_seed_preview"})
    return state


async def start_distillation(teacher: str, target_pairs: int = 30, **kwargs) -> dict:
    """Kick off a distillation run as a background task. Idempotent —
    rejects if a run is already in progress.
    """
    global _running_task

    if _running_task and not _running_task.done():
        return {"status": "rejected", "reason": "another distillation run is in progress"}

    cur = await get_run_status()
    if cur and cur.get("is_running"):
        return {"status": "rejected", "reason": "another run still in DB state"}

    _running_task = asyncio.create_task(
        run_distillation(teacher=teacher, target_pairs=target_pairs, **kwargs)
    )
    return {"status": "started", "teacher": teacher, "target_pairs": target_pairs}


async def stop_distillation() -> dict:
    """Cancel in-flight run, if any."""
    global _running_task
    if _running_task and not _running_task.done():
        _running_task.cancel()
        return {"status": "cancelled"}
    return {"status": "noop", "reason": "no run in progress"}


# ---------------------------------------------------------------------------
# Summary / analytics
# ---------------------------------------------------------------------------
async def get_distill_summary() -> dict:
    """Aggregate stats per source_method across all distillation runs."""
    from sqlalchemy import text
    from models.base import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT source_method, COUNT(*) AS count, "
                "AVG(judge_score) AS avg_score, "
                "MIN(created_at) AS first_at, "
                "MAX(created_at) AS last_at "
                "FROM preference_pairs "
                "WHERE source_method LIKE 'distill_%' "
                "GROUP BY source_method "
                "ORDER BY count DESC"
            )
        )
        rows = []
        for r in result.fetchall():
            rows.append({
                "source_method": r[0],
                "count": r[1],
                "avg_judge_score": float(r[2]) if r[2] else 0.0,
                "first_at": r[3].isoformat() if r[3] else None,
                "last_at": r[4].isoformat() if r[4] else None,
            })
    cur = await get_run_status()
    return {
        "by_teacher": rows,
        "current_run": cur,
        "available_teachers": list_available_teachers(),
    }
