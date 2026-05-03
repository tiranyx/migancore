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


async def _critique(user_message: str, assistant_response: str) -> dict | None:
    """Evaluate response against Constitution principles using 7B judge.

    Returns {"score": int, "violations": list, "suggestions": list} or None on failure.
    Temperature=0: deterministic, reproducible quality assessment.
    """
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

        # Extract JSON — model may include preamble before the brace
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning("cai.critique_no_json", raw_preview=raw[:100])
            return None

        parsed = json.loads(raw[start:end])
        score = int(parsed.get("score", 0))
        if not 1 <= score <= 5:
            logger.warning("cai.critique_invalid_score", score=score)
            return None

        return {
            "score": score,
            "violations": parsed.get("violations", []),
            "suggestions": parsed.get("suggestions", []),
        }

    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.warning("cai.critique_parse_error", error=str(exc))
        return None
    except OllamaError as exc:
        logger.warning("cai.critique_ollama_error", error=str(exc))
        return None
    except Exception as exc:
        logger.warning("cai.critique_error", error=str(exc))
        return None


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
        logger.info("cai.revise_ollama_returned", data_keys=list(data.keys()))
        revised = data.get("message", {}).get("content", "").strip()
        if not revised or len(revised) < 10:
            logger.warning("cai.revise_empty_response", response_len=len(revised))
            return None
        logger.info("cai.revise_got_text", revised_len=len(revised))
        return revised

    except OllamaError as exc:
        logger.warning("cai.revise_ollama_error", error=str(exc))
        return None
    except Exception as exc:
        logger.warning("cai.revise_error", error=str(exc))
        return None
    except BaseException as exc:
        logger.error("cai.revise_base_exception", exc_type=type(exc).__name__, error=str(exc))
        raise


async def _store_preference_pair(
    prompt: str,
    chosen: str,
    rejected: str,
    score: float,
    source_message_id: uuid.UUID,
) -> None:
    """Insert a (chosen, rejected) preference pair into preference_pairs table.

    preference_pairs has no RLS — it is a global training table, not tenant-scoped.
    Uses AsyncSessionLocal directly (background task, no request DB session available).
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
                    "method": "cai_pipeline",
                    "msg_id": source_message_id,
                    "now": datetime.now(timezone.utc),
                },
            )
            await db.commit()
        logger.info(
            "cai.preference_pair_stored",
            score=score,
            source_message_id=str(source_message_id),
            chosen_len=len(chosen),
            rejected_len=len(rejected),
        )
    except Exception as exc:
        logger.warning(
            "cai.store_error",
            error=str(exc),
            source_message_id=str(source_message_id),
        )


async def run_cai_pipeline(
    user_message: str,
    assistant_response: str,
    source_message_id: uuid.UUID,
) -> None:
    """Constitutional AI pipeline entry point — fire-and-forget.

    Called via asyncio.create_task after each sync chat turn.
    50% sampling gate prevents CPU overload on CPU-only VPS.

    Flow:
      1. Sampling gate (50% pass rate) — skip if random > CAI_SAMPLE_RATE
      2. Critique: 7B judge evaluates response vs. 10 Constitution principles
      3. If score <= CRITIQUE_THRESHOLD: generate improved revision
      4. Store (revised=chosen, original=rejected) as DPO preference pair
    """
    logger.info("cai.pipeline_entered", source_message_id=str(source_message_id))
    if random.random() > CAI_SAMPLE_RATE:
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
        logger.info("cai.revise_returned", revised_is_none=revised is None)
        if not revised:
            logger.warning("cai.revise_returned_none", source_message_id=str(source_message_id))
            return

        # chosen=revised (better), rejected=original (worse)
        logger.info("cai.store_starting", source_message_id=str(source_message_id))
        await _store_preference_pair(
            prompt=user_message,
            chosen=revised,
            rejected=assistant_response,
            score=float(score),
            source_message_id=source_message_id,
        )
        logger.info("cai.store_done", source_message_id=str(source_message_id))

    except asyncio.CancelledError:
        logger.warning("cai.pipeline_cancelled", source_message_id=str(source_message_id))
        raise  # CancelledError must be re-raised to properly cancel the task
    except Exception as exc:
        logger.warning("cai.pipeline_error", error=str(exc))
    except BaseException as exc:
        logger.error("cai.pipeline_base_exception", exc_type=type(exc).__name__, error=str(exc))
        raise
