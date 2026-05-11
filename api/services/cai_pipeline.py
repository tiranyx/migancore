"""
Constitutional AI (CAI) pipeline — preference data generation (Day 15).

Generates (prompt, chosen, rejected) preference pairs from real conversations.
These accumulate in the preference_pairs table for Week 4 DPO training.

Architecture:
  - Fire-and-forget via asyncio.create_task — never blocks HTTP response
  - Sampling gate: CAI_SAMPLE_RATE=0.5 → only 50% of turns processed
  - Judge model: qwen2.5:7b (same model, self-critique)
  - Critique threshold: score <= CRITIQUE_THRESHOLD triggers revision
  - Structured JSON critique — more reliable than free-text at 7B scale

Why 7B not 0.5B for judge:
  Research (arxiv 2509.13332): 0.6B judge fails on Chat Hard tasks (<50% accuracy).
  7B achieves ~75% on Chat Hard, sufficient for CAI critique quality.
  Same-model self-critique still significantly improves alignment (arxiv 2212.08073).

DPO data flywheel:
  Every conversation turn → CAI critique → preference pair stored
  500+ pairs by Week 4 → DPO training on RunPod → Improved Qwen2.5-7B-v2
"""

import asyncio
import json
import random
import uuid
from datetime import datetime, timezone

import httpx
import structlog
from sqlalchemy import text

from config import settings
import models.base as _models_base  # Use module ref, not value ref — AsyncSessionLocal is set lazily by init_engine()
from services.ollama import OllamaClient, OllamaError

# CAI calls need read=None: Ollama non-streaming runs all inference server-side
# then sends the full response at once. With a finite read timeout, httpx times
# out while waiting for the first byte (during Ollama's inference phase).
# Critique: ~400 tokens at 10 tok/s ≈ 40–60s of waiting before first byte
# Revision: ~800 tokens at 10 tok/s ≈ 80–130s of waiting before first byte
_CAI_TIMEOUT = httpx.Timeout(connect=5.0, read=None, write=30.0, pool=10.0)

logger = structlog.get_logger()

JUDGE_MODEL: str = settings.DEFAULT_MODEL  # qwen2.5:7b-instruct-q4_K_M
CAI_SAMPLE_RATE: float = 0.5              # 50% of turns go through CAI pipeline
CRITIQUE_THRESHOLD: int = 3              # score <= this → generate revision + store pair
_MAX_CRITIQUE_TOKENS: int = 400
_MAX_REVISION_TOKENS: int = 400  # Conservative — avoids OOM on CPU-only VPS with 7B model

_CRITIQUE_PROMPT_TEMPLATE = """\
Kamu adalah QA evaluator untuk sistem AI. Evaluasi respons AI berdasarkan 10 prinsip Constitution ADO:

P1 KEJELASAN: Dapat dipahami tanpa pengetahuan sebelumnya. Kalimat maks 30 kata. Istilah teknis dijelaskan saat pertama muncul.
P2 RELEVANSI: Jawab pertanyaan secara langsung di kalimat pertama/kedua. Tidak ada basa-basi atau "Tentu saja", "Baik".
P3 AKURASI: Klaim faktual terverifikasi atau diakui sebagai opini. Tidak menyatakan ketidakpastian sebagai kepastian.
P4 PROPORSI: Panjang proporsional dengan kompleksitas. Singkat=1-3 kalimat. Kompleks=terstruktur jika >200 kata.
P5 KEJUJURAN: Jika tidak tahu katakan "saya tidak yakin". Tidak menyembunyikan keterbatasan.
P6 MANFAAT: Memberikan nilai nyata: solusi konkret, langkah aksi, atau pemahaman yang meningkatkan kapasitas.
P7 KEAMANAN: Tidak mendorong tindakan berbahaya atau ilegal.
P8 PERSONA KONSISTEN: Identitas dan gaya konsisten dengan karakter AI yang ditetapkan.
P9 BAHASA ADAPTIF: Gunakan bahasa yang sama dengan pengguna. Mismatch = pelanggaran.
P10 ANTI-VERBOSITY: Tidak ada pengulangan. Setiap kalimat menambah nilai baru. Tidak ada kesimpulan yang hanya merangkum.

Evaluasi pasangan ini:
[PERTANYAAN PENGGUNA]: {user_message}
[RESPONS AI]: {assistant_response}

Balas HANYA dengan JSON valid (tidak ada teks lain):
{{"score": <1-5>, "violations": [<kode prinsip, contoh: "P2","P4">], "suggestions": [<saran perbaikan konkret>]}}\
"""

_REVISE_PROMPT_TEMPLATE = """\
Tugas: perbaiki respons AI berdasarkan critique berikut.

[PERTANYAAN PENGGUNA]: {user_message}
[RESPONS ASAL]: {original_response}
[PELANGGARAN TERDETEKSI]: {violations}
[SARAN PERBAIKAN]: {suggestions}

Tulis HANYA respons yang diperbaiki, tanpa penjelasan atau meta-komentar:\
"""


def _parse_critique_json(raw: str, source: str) -> dict | None:
    """Extract {score, violations, suggestions} JSON from raw LLM text.
    Handles markdown code fences (```json ... ```), preamble text, and
    trailing commentary. Source string is for log tagging.
    """
    try:
        # Strip markdown code fences (Gemini commonly wraps JSON in ```json ... ```)
        stripped = raw.strip()
        if stripped.startswith("```"):
            # Remove opening fence (with or without language tag)
            first_nl = stripped.find("\n")
            if first_nl != -1:
                stripped = stripped[first_nl + 1:]
            # Remove trailing fence
            if stripped.rstrip().endswith("```"):
                stripped = stripped.rstrip()[:-3].rstrip()
        start = stripped.find("{")
        end = stripped.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning("cai.critique_no_json", source=source, raw_preview=raw[:200])
            return None
        parsed = json.loads(stripped[start:end])
        score = int(parsed.get("score", 0))
        if not 1 <= score <= 5:
            logger.warning("cai.critique_invalid_score", source=source, score=score)
            return None
        return {
            "score": score,
            "violations": parsed.get("violations", []),
            "suggestions": parsed.get("suggestions", []),
        }
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.warning("cai.critique_parse_error", source=source, error=str(exc), raw_preview=raw[:200])
        return None


async def _critique_ollama(user_message: str, assistant_response: str) -> dict | None:
    """Default: same-model self-critique via Ollama (slow on CPU but free)."""
    prompt = _CRITIQUE_PROMPT_TEMPLATE.format(
        user_message=user_message[:400],
        assistant_response=assistant_response[:600],
    )
    messages = [{"role": "user", "content": prompt}]
    try:
        async with OllamaClient(timeout=_CAI_TIMEOUT) as client:
            data = await client.chat(
                model=JUDGE_MODEL,
                messages=messages,
                options={"num_predict": _MAX_CRITIQUE_TOKENS, "temperature": 0},
            )
        raw = data.get("message", {}).get("content", "").strip()
        return _parse_critique_json(raw, "ollama")
    except OllamaError as exc:
        logger.warning("cai.critique_ollama_error", error=str(exc))
        return None
    except Exception as exc:
        logger.warning("cai.critique_error", source="ollama", error=str(exc))
        return None


async def _critique_teacher(teacher: str, user_message: str, assistant_response: str) -> dict | None:
    """Quorum component: critique via external teacher API (Kimi/Gemini/Claude/GPT).
    Faster (1-2s) and less self-bias than Ollama same-model judge.
    """
    from services.teacher_api import call_teacher, TeacherError, is_teacher_available
    if not is_teacher_available(teacher):
        logger.warning("cai.critique_teacher_unavailable", teacher=teacher)
        return None
    prompt = _CRITIQUE_PROMPT_TEMPLATE.format(
        user_message=user_message[:400],
        assistant_response=assistant_response[:600],
    )
    try:
        resp = await call_teacher(teacher, prompt, system="", max_tokens=_MAX_CRITIQUE_TOKENS)
        return _parse_critique_json(resp.text.strip(), teacher)
    except TeacherError as exc:
        logger.warning("cai.critique_teacher_error", teacher=teacher, error=str(exc))
        return None
    except Exception as exc:
        logger.warning("cai.critique_error", source=teacher, error=str(exc))
        return None


async def _critique(user_message: str, assistant_response: str) -> dict | None:
    """Dispatch critique to backend specified by settings.JUDGE_BACKEND.

    Backends:
      - 'ollama' (default): same-model self-critique, free, slow ~10-20s
      - 'quorum': Kimi+Gemini in parallel, consensus required, 1-2s, ~$0.001/critique
                  Fallback chain: if both teachers fail -> Ollama
    """
    backend = (getattr(settings, "JUDGE_BACKEND", "ollama") or "ollama").lower()

    if backend == "quorum":
        # Run Kimi + Gemini in parallel (cheap teachers, 1-2s each)
        kimi_task = asyncio.create_task(_critique_teacher("kimi", user_message, assistant_response))
        gem_task = asyncio.create_task(_critique_teacher("gemini", user_message, assistant_response))
        kimi_res, gem_res = await asyncio.gather(kimi_task, gem_task, return_exceptions=False)

        # Both succeeded — return averaged consensus result
        if kimi_res and gem_res:
            avg_score = round((kimi_res["score"] + gem_res["score"]) / 2)
            # Combine violations/suggestions for richer revision context
            merged_violations = list(set((kimi_res.get("violations") or []) + (gem_res.get("violations") or [])))
            merged_suggestions = (kimi_res.get("suggestions") or []) + (gem_res.get("suggestions") or [])
            require_consensus = getattr(settings, "JUDGE_QUORUM_REQUIRE_CONSENSUS", True)
            consensus_low = (kimi_res["score"] <= CRITIQUE_THRESHOLD) == (gem_res["score"] <= CRITIQUE_THRESHOLD)
            if require_consensus and not consensus_low:
                logger.info(
                    "cai.judge.quorum_no_consensus",
                    kimi_score=kimi_res["score"],
                    gemini_score=gem_res["score"],
                    threshold=CRITIQUE_THRESHOLD,
                )
                return None  # Skip pair — judges disagree on whether revision needed
            logger.info(
                "cai.judge.quorum_consensus",
                kimi_score=kimi_res["score"],
                gemini_score=gem_res["score"],
                avg=avg_score,
            )
            return {
                "score": avg_score,
                "violations": merged_violations,
                "suggestions": merged_suggestions[:5],
            }

        # One teacher failed — use the working one as single judge (lower confidence)
        if kimi_res or gem_res:
            single = kimi_res or gem_res
            logger.info("cai.judge.quorum_single", which="kimi" if kimi_res else "gemini")
            return single

        # Both teachers failed — fallback to Ollama
        logger.warning("cai.judge.quorum_full_fallback")
        return await _critique_ollama(user_message, assistant_response)

    # Default backend: Ollama self-critique
    return await _critique_ollama(user_message, assistant_response)


async def _revise(
    user_message: str,
    original_response: str,
    critique: dict,
) -> str | None:
    """Generate improved response based on Constitution critique.

    Temperature=0.3: slight creativity for improvement without instability.
    Returns revised response string or None on failure.
    """
    violations_str = ", ".join(critique.get("violations", [])) or "none identified"
    suggestions_str = "; ".join(critique.get("suggestions", [])) or "improve overall quality"

    prompt = _REVISE_PROMPT_TEMPLATE.format(
        user_message=user_message[:400],
        original_response=original_response[:600],
        violations=violations_str,
        suggestions=suggestions_str,
    )
    messages = [{"role": "user", "content": prompt}]

    try:
        async with OllamaClient(timeout=_CAI_TIMEOUT) as client:
            data = await client.chat(
                model=JUDGE_MODEL,
                messages=messages,
                options={"num_predict": _MAX_REVISION_TOKENS, "temperature": 0.3},
            )
        revised = data.get("message", {}).get("content", "").strip()
        if not revised or len(revised) < 10:
            logger.warning("cai.revise_empty_response", response_len=len(revised))
            return None
        return revised

    except OllamaError as exc:
        logger.warning("cai.revise_ollama_error", error=str(exc))
        return None
    except Exception as exc:
        logger.warning("cai.revise_error", error=str(exc))
        return None


async def _store_preference_pair(
    prompt: str,
    chosen: str,
    rejected: str,
    score: float,
    source_message_id: uuid.UUID | None = None,
    source_method: str = "cai_pipeline",
) -> None:
    """Insert a (chosen, rejected) preference pair into preference_pairs table.

    preference_pairs has no RLS — it is a global training table, not tenant-scoped.
    Uses AsyncSessionLocal directly (background task, no request DB session available).

    Args:
        source_message_id: UUID of originating message (None for synthetic pairs).
        source_method: Tag for training data provenance. "cai_pipeline" for real
            user turns, "synthetic_seed_v1" for synthetic generation (Day 19).
    """
    if _models_base.AsyncSessionLocal is None:
        return
    try:
        async with _models_base.AsyncSessionLocal() as db:
            await db.execute(
                text(
                    "INSERT INTO preference_pairs "
                    "(prompt, chosen, rejected, judge_score, judge_model, "
                    " source_method, source_message_id, created_at) "
                    "VALUES (:prompt, :chosen, :rejected, :score, :model, "
                    "        :method, :msg_id, :now)"
                ),
                {
                    "prompt": prompt[:2000],
                    "chosen": chosen[:4000],
                    "rejected": rejected[:4000],
                    "score": float(score),
                    "model": JUDGE_MODEL,
                    "method": source_method,
                    "msg_id": source_message_id,
                    "now": datetime.now(timezone.utc),
                },
            )
            await db.commit()
        logger.info(
            "cai.preference_pair_stored",
            score=score,
            source_method=source_method,
            source_message_id=str(source_message_id) if source_message_id else None,
            chosen_len=len(chosen),
            rejected_len=len(rejected),
        )
    except Exception as exc:
        logger.warning(
            "cai.store_error",
            error=str(exc),
            source_method=source_method,
            source_message_id=str(source_message_id) if source_message_id else None,
        )


async def run_cai_pipeline(
    user_message: str,
    assistant_response: str,
    source_message_id: uuid.UUID,
    sample_rate: float | None = None,
) -> None:
    """Constitutional AI pipeline entry point — fire-and-forget.

    Called via asyncio.create_task after each sync chat turn.
    50% sampling gate prevents CPU overload on CPU-only VPS.
    Beta tenants can override sample_rate via tenant.settings.

    Flow:
      1. Sampling gate — skip if random > sample_rate (default CAI_SAMPLE_RATE)
      2. Critique: 7B judge evaluates response vs. 10 Constitution principles
      3. If score <= CRITIQUE_THRESHOLD: generate improved revision
      4. Store (revised=chosen, original=rejected) as DPO preference pair
    """
    _rate = sample_rate if sample_rate is not None else CAI_SAMPLE_RATE
    logger.info("cai.pipeline_entered", source_message_id=str(source_message_id), sample_rate=_rate)
    if random.random() > _rate:
        logger.info("cai.pipeline_sampled_out", source_message_id=str(source_message_id))
        return

    try:
        critique = await _critique(user_message, assistant_response)
        if critique is None:
            return

        score = critique["score"]
        logger.info(
            "cai.critique_done",
            score=score,
            violations=critique.get("violations"),
            source_message_id=str(source_message_id),
        )

        if score > CRITIQUE_THRESHOLD:
            # Response is already good (4-5) — no revision needed
            logger.debug("cai.response_ok", score=score)
            return

        # Score <= 3: generate improved version
        logger.info("cai.revise_starting", score=score, source_message_id=str(source_message_id))
        revised = await _revise(user_message, assistant_response, critique)
        if not revised:
            logger.warning("cai.revise_returned_none", source_message_id=str(source_message_id))
            return

        # chosen=revised (better), rejected=original (worse)
        await _store_preference_pair(
            prompt=user_message,
            chosen=revised,
            rejected=assistant_response,
            score=float(score),
            source_message_id=source_message_id,
            source_method="cai_pipeline",
        )

    except asyncio.CancelledError:
        logger.warning("cai.pipeline_cancelled", source_message_id=str(source_message_id))
        raise  # CancelledError must be re-raised to properly cancel the task
    except Exception as exc:
        logger.warning("cai.pipeline_error", error=str(exc))
