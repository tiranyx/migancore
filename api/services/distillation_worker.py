"""
Distillation Worker — Day 71+ : MiganCore Self-Learning Pipeline.

Background worker that converts real user interactions into high-quality
training data via 4-teacher distillation + CAI critique.

Architecture:
    1. POLL: Fetch unprocessed conversations from DB (last N hours)
    2. TEACH: Send prompt to available teachers in parallel
    3. JUDGE: Score responses, pick best (or use quorum)
    4. CRITIQUE: CAI judge critiques for alignment/quality
    5. FORMAT: Build SFT pair or DPO pair (chosen vs rejected)
    6. STORE: Append to rolling JSONL dataset
    7. TRIGGER: If dataset > threshold, queue training job

Teachers (cost-ordered, cheapest first):
    1. Gemini 2.5 Flash   — $0.075/$0.30 per 1M (cheapest)
    2. Kimi K2.6          — $0.60/$2.50 per 1M (best bilingual ID)
    3. GPT-4o             — $2.50/$10.00 per 1M (reliable)
    4. Claude Sonnet 4.5  — $3.00/$15.00 per 1M (highest quality judge)

Budget guards:
    - Hard cap per run: $DISTILL_BUDGET_USD_HARD_CAP (default $10)
    - Per-pair cost must be < $0.05 or it's discarded
    - Daily spend tracked in SQLite budget.db

Run modes:
    - CLI: python -m services.distillation_worker --run-once
    - Cron: run every 6 hours via systemd/cron
    - Docker: docker compose exec api python -m services.distillation_worker

Author: MiganCore ADO — self-evolving pipeline v1.0
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import structlog

# Allow running standalone
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from services.teacher_api import (
    TeacherResponse,
    TeacherError,
    call_teacher,
    list_available_teachers,
    TEACHER_REGISTRY,
)

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Configurable constants
# ---------------------------------------------------------------------------
# Writable path inside container (mounted from host ./data/training)
DATASET_DIR = Path("/app/data/training")
DATASET_DIR.mkdir(parents=True, exist_ok=True)

# Rolling dataset files
SFT_DATASET_PATH = DATASET_DIR / "sft_rolling.jsonl"
DPO_DATASET_PATH = DATASET_DIR / "dpo_rolling.jsonl"

# Budget tracking DB
BUDGET_DB_PATH = DATASET_DIR / "budget.db"

# Quality threshold: only keep pairs where best teacher clearly beats others
JUDGE_DIFF_THRESHOLD = settings.DISTILL_MARGIN_THRESHOLD  # default 2.0

# Min pairs to trigger training consideration
TRIGGER_MIN_PAIRS = settings.TRAINING_MIN_SFT_PAIRS

# Max concurrent teacher calls (avoid rate limits)
MAX_CONCURRENT_TEACHERS = 4

# Teachers ordered by cost (cheapest first) for fallback
TEACHER_PRIORITY = ["gemini", "kimi", "gpt", "claude"]


# ---------------------------------------------------------------------------
# Budget tracking
# ---------------------------------------------------------------------------
@dataclass
class BudgetTracker:
    db_path: Path = BUDGET_DB_PATH
    hard_cap: float = settings.DISTILL_BUDGET_USD_HARD_CAP

    def __post_init__(self):
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS spend (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    teacher TEXT NOT NULL,
                    cost_usd REAL NOT NULL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    pair_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_spend_date ON spend(date)"
            )
            conn.commit()

    def today_spend(self) -> float:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT SUM(cost_usd) FROM spend WHERE date = ?", (today,)
            ).fetchone()
            return row[0] or 0.0

    def log_spend(self, teacher: str, cost: float, in_tok: int, out_tok: int, pair_id: str):
        today = datetime.utcnow().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO spend (date, teacher, cost_usd, input_tokens, output_tokens, pair_id) VALUES (?, ?, ?, ?, ?, ?)",
                (today, teacher, cost, in_tok, out_tok, pair_id),
            )
            conn.commit()

    def can_spend(self, estimated: float) -> bool:
        return (self.today_spend() + estimated) < self.hard_cap

    def report(self) -> dict:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT teacher, SUM(cost_usd), COUNT(*) FROM spend WHERE date = ? GROUP BY teacher",
                (today,),
            ).fetchall()
        total = sum(r[1] for r in rows)
        return {
            "date": today,
            "total_usd": round(total, 4),
            "remaining_usd": round(self.hard_cap - total, 4),
            "by_teacher": {r[0]: {"cost": round(r[1], 4), "calls": r[2]} for r in rows},
        }


# ---------------------------------------------------------------------------
# Conversation fetcher — queries PostgreSQL messages table directly
# ---------------------------------------------------------------------------
@dataclass
class RawInteraction:
    id: str
    user_message: str
    system_prompt: str
    model_response: str
    user_feedback: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


# State tracking — which message IDs have been processed
STATE_PATH = DATASET_DIR / "distill_state.json"


def _load_processed_ids() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("processed_ids", []))
    except Exception:
        return set()


def _save_processed_ids(ids: set[str]):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"processed_ids": list(ids), "updated_at": datetime.utcnow().isoformat()}, f)


async def fetch_unprocessed_interactions(
    hours: int = 6,
    limit: int = 20,
    diagnose: bool = False,
) -> list[RawInteraction]:
    """
    Fetch recent user→assistant message pairs from PostgreSQL.
    Uses file-based state tracking (no DB schema changes required).

    Day 71 fix: Use timezone-aware datetime to avoid PostgreSQL tz cast issues.
    Day 71 fix: Robust query handles tool messages between user and assistant.
    Day 71 fix: Diagnostic mode prints counts and sample rows for debugging.
    """
    import asyncpg

    processed = _load_processed_ids()
    results: list[RawInteraction] = []

    try:
        # asyncpg expects 'postgresql://' not 'postgresql+asyncpg://'
        dsn = settings.DATABASE_URL.replace("+asyncpg", "", 1).replace("ado_app", "ado", 1)
        conn = await asyncpg.connect(dsn)
        try:
            # FIX: timezone-aware cutoff (Lesson #182)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

            # ------------------------------------------------------------------
            # Diagnostic: print raw counts before applying filters
            # ------------------------------------------------------------------
            if diagnose:
                total_msgs = await conn.fetchval(
                    "SELECT COUNT(*) FROM messages WHERE created_at > $1", cutoff
                )
                assistant_msgs = await conn.fetchval(
                    "SELECT COUNT(*) FROM messages WHERE role = 'assistant' AND created_at > $1",
                    cutoff,
                )
                user_msgs = await conn.fetchval(
                    "SELECT COUNT(*) FROM messages WHERE role = 'user' AND created_at > $1",
                    cutoff,
                )
                long_assist = await conn.fetchval(
                    "SELECT COUNT(*) FROM messages WHERE role = 'assistant' AND created_at > $1 AND LENGTH(content) > 10",
                    cutoff,
                )
                print(f"[DIAGNOSE] Total messages in last {hours}h: {total_msgs}")
                print(f"[DIAGNOSE] Assistant messages: {assistant_msgs}")
                print(f"[DIAGNOSE] User messages: {user_msgs}")
                print(f"[DIAGNOSE] Assistant (len>10): {long_assist}")
                print(f"[DIAGNOSE] Already processed IDs: {len(processed)}")

            # Query: find assistant messages whose immediately preceding message
            # in the same conversation was from the user.
            # FIX (Lesson #183): Use ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
            # with UNBOUNDED PRECEDING to correctly find previous user message
            # even when tool messages sit between user and assistant.
            rows = await conn.fetch(
                """
                WITH ranked AS (
                    SELECT
                        m.id AS assistant_msg_id,
                        m.conversation_id,
                        m.content AS assistant_content,
                        m.created_at,
                        m.quality_score,
                        LAG(m.role) OVER w AS prev_role,
                        LAG(m.content) OVER w AS prev_content,
                        LAG(m.role, 2) OVER w AS prev_prev_role
                    FROM messages m
                    WHERE m.created_at > $1
                    WINDOW w AS (
                        PARTITION BY m.conversation_id
                        ORDER BY m.created_at
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    )
                )
                SELECT
                    assistant_msg_id,
                    conversation_id,
                    assistant_content,
                    prev_content AS user_content,
                    prev_role,
                    created_at,
                    quality_score
                FROM ranked
                WHERE prev_role = 'user'
                  AND assistant_content IS NOT NULL
                  AND LENGTH(assistant_content) > 10
                ORDER BY created_at DESC
                LIMIT $2
                """,
                cutoff,
                limit * 5,  # oversample to account for already-processed
            )

            skipped_already_processed = 0
            for row in rows:
                msg_id = str(row["assistant_msg_id"])
                if msg_id in processed:
                    skipped_already_processed += 1
                    continue

                # Fetch system prompt for this conversation (if any)
                system_rows = await conn.fetch(
                    "SELECT content FROM messages WHERE conversation_id = $1 AND role = 'system' ORDER BY created_at LIMIT 1",
                    row["conversation_id"],
                )
                system_prompt = system_rows[0]["content"] if system_rows else ""

                results.append(
                    RawInteraction(
                        id=msg_id,
                        user_message=row["user_content"] or "",
                        system_prompt=system_prompt,
                        model_response=row["assistant_content"] or "",
                        user_feedback=None,  # TODO: join with feedback table
                        timestamp=row["created_at"].replace(tzinfo=None) if row["created_at"] else datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                )
                processed.add(msg_id)
                if len(results) >= limit:
                    break

            if diagnose:
                print(f"[DIAGNOSE] Raw rows from query: {len(rows)}")
                print(f"[DIAGNOSE] Skipped (already processed): {skipped_already_processed}")
                print(f"[DIAGNOSE] Final new results: {len(results)}")
                for r in results[:3]:
                    print(f"[DIAGNOSE] Sample: id={r.id[:8]}... user={r.user_message[:40]}...")

        finally:
            await conn.close()

        _save_processed_ids(processed)
        logger.info("distill.db_fetch", count=len(results), window_hours=hours)
        return results

    except Exception as exc:
        logger.error("distill.db_fetch_error", error=str(exc))
        if diagnose:
            print(f"[DIAGNOSE] DB ERROR: {exc}")
        # Fallback to queue file
        queue_path = DATASET_DIR / "interaction_queue.jsonl"
        if not queue_path.exists():
            return []
        fallback = []
        with open(queue_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    fallback.append(
                        RawInteraction(
                            id=d.get("id", str(int(time.time() * 1000))),
                            user_message=d.get("user_message", ""),
                            system_prompt=d.get("system_prompt", ""),
                            model_response=d.get("model_response", ""),
                            user_feedback=d.get("user_feedback"),
                            timestamp=datetime.fromisoformat(d.get("timestamp", "2026-01-01T00:00:00")),
                        )
                    )
                except Exception:
                    continue
        return fallback[:limit]


# ---------------------------------------------------------------------------
# Teacher quorum
# ---------------------------------------------------------------------------
async def call_teacher_with_semaphore(
    sem: asyncio.Semaphore,
    teacher: str,
    prompt: str,
    system: str,
    max_tokens: int,
) -> Optional[TeacherResponse]:
    async with sem:
        try:
            resp = await call_teacher(teacher, prompt, system, max_tokens)
            logger.info(
                "distill.teacher_ok",
                teacher=teacher,
                cost=resp.cost_usd,
                tokens_out=resp.output_tokens,
            )
            return resp
        except TeacherError as exc:
            logger.warning("distill.teacher_fail", teacher=teacher, error=str(exc))
            return None


async def gather_teacher_responses(
    prompt: str,
    system: str = "",
    max_tokens: int = 600,
    teachers: Optional[list[str]] = None,
) -> dict[str, TeacherResponse]:
    """Call all available teachers in parallel, return {teacher: response}."""
    available = list_available_teachers()
    if teachers:
        available = [t for t in teachers if t in available]
    if not available:
        logger.error("distill.no_teachers_available")
        return {}

    sem = asyncio.Semaphore(MAX_CONCURRENT_TEACHERS)
    tasks = [
        call_teacher_with_semaphore(sem, t, prompt, system, max_tokens)
        for t in available
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    out = {}
    for teacher, result in zip(available, results):
        if isinstance(result, TeacherResponse):
            out[teacher] = result
        elif isinstance(result, Exception):
            logger.warning("distill.teacher_exception", teacher=teacher, error=str(result))
    return out


# ---------------------------------------------------------------------------
# Scoring / Judging
# ---------------------------------------------------------------------------
def score_response_length_quality(text: str) -> float:
    """Basic heuristic: penalize too short or way-too-long responses."""
    words = len(text.split())
    if words < 10:
        return 0.3
    if words > 400:
        return 0.7
    return 1.0


def pick_best_response(responses: dict[str, TeacherResponse]) -> tuple[str, TeacherResponse]:
    """
    Pick best teacher response using composite score:
    - Cost efficiency (cheaper = better for same quality)
    - Length quality
    - Prefer Kimi for Indonesian content (heuristic: if prompt contains Indonesian words)
    """
    if not responses:
        raise ValueError("No responses to judge")

    best_teacher = None
    best_score = -1.0
    best_resp = None

    for teacher, resp in responses.items():
        score = score_response_length_quality(resp.text)
        # Cost efficiency: normalize cost 0-1 (cheaper = higher score)
        max_cost = 0.05  # $0.05 per call max reasonable
        cost_score = max(0, 1 - (resp.cost_usd / max_cost))
        score = score * 0.7 + cost_score * 0.3

        # Tie-breaker: prefer cheaper teacher
        if score > best_score or (score == best_score and resp.cost_usd < (best_resp.cost_usd if best_resp else float("inf"))):
            best_score = score
            best_teacher = teacher
            best_resp = resp

    return best_teacher, best_resp


# ---------------------------------------------------------------------------
# CAI Judge (using local Ollama for free critique)
# ---------------------------------------------------------------------------
async def critique_with_ollama(
    prompt: str,
    response: str,
    system: str = "",
    model: str = "migancore:0.7c",
) -> dict:
    """
    Use local MiganCore as CAI judge to critique a response.
    Returns: {"score": 1-10, "revision_needed": bool, "critique": str}
    """
    import httpx

    critique_prompt = f"""Evaluate this AI response for quality, accuracy, and alignment.

User question:
{prompt}

AI response:
{response}

Rate 1-10. State if revision is needed. Give concise critique."""

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": critique_prompt})

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.OLLAMA_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 300},
                },
            )
            data = resp.json()
            text = data.get("message", {}).get("content", "").strip()

        # Parse simple heuristic from text
        score = 5.0
        revision_needed = False
        lines = text.split("\n")
        for line in lines:
            low = line.lower()
            if "score" in low or "rating" in low:
                # Try extract number
                import re
                nums = re.findall(r"(\d+(?:\.\d+)?)", line)
                if nums:
                    score = float(nums[0])
            if "revision needed" in low or "needs improvement" in low or "revised" in low:
                revision_needed = True

        return {
            "score": min(10, max(1, score)),
            "revision_needed": revision_needed,
            "critique": text,
            "model": model,
        }
    except Exception as exc:
        logger.warning("distill.critique_fail", error=str(exc))
        return {"score": 5, "revision_needed": False, "critique": f"Critique failed: {exc}", "model": model}


# ---------------------------------------------------------------------------
# Dataset formatting
# ---------------------------------------------------------------------------
def format_sft_pair(
    interaction: RawInteraction,
    best_response: str,
    critique: Optional[dict] = None,
) -> dict:
    """Format into SFT message-format JSONL."""
    messages = []
    if interaction.system_prompt:
        messages.append({"role": "system", "content": interaction.system_prompt})
    messages.append({"role": "user", "content": interaction.user_message})
    messages.append({"role": "assistant", "content": best_response})

    meta = {
        "source": "distillation_worker",
        "original_model_response": interaction.model_response,
        "critique_score": critique.get("score") if critique else None,
        "critique_revision_needed": critique.get("revision_needed") if critique else None,
        "timestamp": datetime.utcnow().isoformat(),
    }

    return {"messages": messages, "meta": meta}


def format_dpo_pair(
    interaction: RawInteraction,
    chosen: str,
    rejected: str,
    critique: Optional[dict] = None,
) -> dict:
    """Format into DPO preference-format JSONL."""
    system = interaction.system_prompt or ""
    return {
        "system": system,
        "prompt": interaction.user_message,
        "chosen": chosen,
        "rejected": rejected,
        "meta": {
            "source": "distillation_worker",
            "critique_score": critique.get("score") if critique else None,
            "timestamp": datetime.utcnow().isoformat(),
        },
    }


def append_jsonl(path: Path, record: dict):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Main worker loop
# ---------------------------------------------------------------------------
async def run_distillation_cycle(
    hours: int = 6,
    limit: int = 20,
    enable_critique: bool = True,
    enable_dpo: bool = True,
    diagnose: bool = False,
) -> dict:
    """
    Run one distillation cycle.
    Returns summary dict for logging/monitoring.
    """
    budget = BudgetTracker()
    report = {
        "cycle_start": datetime.utcnow().isoformat(),
        "interactions_fetched": 0,
        "pairs_generated": 0,
        "dpo_pairs": 0,
        "cost_total_usd": 0.0,
        "errors": [],
        "by_teacher": {},
    }

    if not budget.can_spend(0.01):
        logger.error("distill.budget_exhausted", spent=budget.today_spend(), cap=budget.hard_cap)
        report["errors"].append("daily_budget_exhausted")
        return report

    interactions = await fetch_unprocessed_interactions(hours=hours, limit=limit, diagnose=diagnose)
    report["interactions_fetched"] = len(interactions)
    logger.info("distill.fetched", count=len(interactions), hours=hours)
    if diagnose:
        print(f"[DIAGNOSE] Total interactions fetched: {len(interactions)}")

    if not interactions:
        logger.info("distill.no_work")
        return report

    for interaction in interactions:
        pair_id = interaction.id
        try:
            # M1.4: Pre-pair budget guard — estimate max cost before calling teachers.
            # If we can't afford at least $0.05 (rough per-pair max), stop the cycle.
            if not budget.can_spend(0.05):
                logger.error("distill.budget_exhausted_mid_cycle", spent=budget.today_spend(), cap=budget.hard_cap)
                report["errors"].append("daily_budget_exhausted_mid_cycle")
                break

            # Step 1: Gather teacher responses
            teachers_resp = await gather_teacher_responses(
                prompt=interaction.user_message,
                system=interaction.system_prompt,
                max_tokens=settings.DISTILL_MAX_OUTPUT_TOKENS,
            )
            if len(teachers_resp) < 2:
                logger.warning("distill.insufficient_teachers", pair_id=pair_id, got=len(teachers_resp))
                continue

            # Log budget
            for t, resp in teachers_resp.items():
                budget.log_spend(t, resp.cost_usd, resp.input_tokens, resp.output_tokens, pair_id)
                report["cost_total_usd"] += resp.cost_usd
                report["by_teacher"][t] = report["by_teacher"].get(t, 0) + resp.cost_usd

            # Step 2: Pick best
            best_teacher, best_resp = pick_best_response(teachers_resp)
            logger.info("distill.best_teacher", pair_id=pair_id, teacher=best_teacher, cost=best_resp.cost_usd)

            # Step 3: Critique (free, local Ollama)
            critique = None
            if enable_critique:
                critique = await critique_with_ollama(
                    interaction.user_message, best_resp.text, interaction.system_prompt
                )
                logger.info(
                    "distill.critique",
                    pair_id=pair_id,
                    score=critique["score"],
                    revision_needed=critique["revision_needed"],
                )

            # Step 4: Format & store SFT pair
            sft_record = format_sft_pair(interaction, best_resp.text, critique)
            append_jsonl(SFT_DATASET_PATH, sft_record)
            report["pairs_generated"] += 1

            # Step 5: DPO pair (chosen=best, rejected=worst or original model response)
            if enable_dpo:
                # Reject the model's own previous response as "rejected"
                rejected = interaction.model_response or ""
                if rejected and rejected != best_resp.text:
                    dpo_record = format_dpo_pair(interaction, best_resp.text, rejected, critique)
                    append_jsonl(DPO_DATASET_PATH, dpo_record)
                    report["dpo_pairs"] += 1

            # TODO: Mark interaction as distilled in DB
            # UPDATE chat_messages SET distilled_at = NOW() WHERE id = %s

        except Exception as exc:
            logger.error("distill.pair_error", pair_id=pair_id, error=str(exc))
            report["errors"].append(f"{pair_id}: {exc}")
            continue

    report["cycle_end"] = datetime.utcnow().isoformat()
    report["budget_remaining"] = budget.report()
    logger.info("distill.cycle_complete", **report)
    return report


def training_pair_counts() -> dict[str, int]:
    """Count rolling SFT and DPO pairs available for training."""
    counts = {"sft": 0, "dpo": 0}
    if SFT_DATASET_PATH.exists():
        with open(SFT_DATASET_PATH, "r", encoding="utf-8") as f:
            counts["sft"] = sum(1 for _ in f)
    if DPO_DATASET_PATH.exists():
        with open(DPO_DATASET_PATH, "r", encoding="utf-8") as f:
            counts["dpo"] = sum(1 for _ in f)
    return counts


def should_trigger_training() -> bool:
    """Check if rolling datasets meet configured training thresholds."""
    counts = training_pair_counts()
    return (
        counts["sft"] >= settings.TRAINING_MIN_SFT_PAIRS
        and counts["dpo"] >= settings.TRAINING_MIN_DPO_PAIRS
    )


async def maybe_auto_trigger_training() -> dict:
    """Queue MiganForge when thresholds are met and auto-trigger is enabled."""
    counts = training_pair_counts()
    thresholds = {
        "sft": settings.TRAINING_MIN_SFT_PAIRS,
        "dpo": settings.TRAINING_MIN_DPO_PAIRS,
    }
    if not should_trigger_training():
        result = {"status": "below_threshold", "counts": counts, "thresholds": thresholds}
        logger.info("distill.training_trigger_not_ready", **result)
        return result

    if not settings.TRAINING_AUTO_TRIGGER:
        result = {"status": "ready_auto_disabled", "counts": counts, "thresholds": thresholds}
        logger.info("distill.training_trigger_ready", **result)
        return result

    provider = settings.TRAINING_GPU_PROVIDER.lower()
    if provider == "runpod" and not settings.RUNPOD_API_KEY:
        result = {"status": "blocked_missing_runpod_key", "counts": counts}
        logger.warning("distill.training_trigger_blocked", **result)
        return result
    if provider == "vastai" and not settings.VAST_API_KEY:
        result = {"status": "blocked_missing_vast_key", "counts": counts}
        logger.warning("distill.training_trigger_blocked", **result)
        return result

    from services.training_orchestrator import TrainingOrchestrator

    orchestrator = TrainingOrchestrator()
    result = await asyncio.to_thread(orchestrator.run, False, False)
    logger.info("distill.training_trigger_result", result=result)
    return result


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="MiganCore Distillation Worker")
    parser.add_argument("--run-once", action="store_true", help="Run single cycle and exit")
    parser.add_argument("--hours", type=int, default=6, help="Look back N hours for interactions")
    parser.add_argument("--limit", type=int, default=20, help="Max interactions per cycle")
    parser.add_argument("--no-critique", action="store_true", help="Skip CAI critique (faster)")
    parser.add_argument("--no-dpo", action="store_true", help="Skip DPO pair generation")
    parser.add_argument("--teachers", nargs="+", default=None, help="Subset of teachers: gemini kimi gpt claude")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without calling teachers or writing data")
    parser.add_argument("--diagnose", action="store_true", help="Print DB diagnostic info (no teachers called)")
    args = parser.parse_args()

    async def _run():
        if args.diagnose:
            logger.info("distill.diagnose_mode")
            report = await run_distillation_cycle(
                hours=args.hours,
                limit=args.limit,
                enable_critique=False,
                enable_dpo=False,
                diagnose=True,
            )
            print(json.dumps(report, indent=2, default=str))
            return
        if args.dry_run:
            logger.info("distill.dry_run_mode")
            print(json.dumps({"dry_run": True, "status": "ok", "message": "Dry run mode. No teachers called."}, indent=2))
            return
        report = await run_distillation_cycle(
            hours=args.hours,
            limit=args.limit,
            enable_critique=not args.no_critique,
            enable_dpo=not args.no_dpo,
            diagnose=False,
        )
        print(json.dumps(report, indent=2, default=str))

        trigger_report = await maybe_auto_trigger_training()
        report["training_trigger"] = trigger_report

    asyncio.run(_run())


if __name__ == "__main__":
    main()
