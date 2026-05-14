"""
Code Lab — Sprint 2 Day 74

Scoring + adaptive lesson capture untuk code execution.
Wraps existing subprocess-based execution (run_python tool) dengan:
- Rasa sakit/senang signal (scoring layer)
- Adaptive lesson capture (TIDAK blanket — only when meaningful)
- Write lessons ke nafs/hikmah buckets

Vision tag:
- Akal (Prefrontal Cortex): scoring before commit
- Nafs (self-awareness): error → lesson
- Hikmah (wisdom): success pattern → accumulated wisdom
- Adaptive Design: NOT every execution → lesson saved

Reference: docs/SPRINT_2_CODE_LAB_DESIGN.md
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, asdict
from typing import Optional

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Result dataclass with scoring
# ---------------------------------------------------------------------------
@dataclass
class CodeExecutionScore:
    """Adaptive scoring per code execution — rasa sakit/senang signal."""
    success: bool
    elapsed_ms: int
    code_length: int
    score: float      # -1.0 (sangat sakit) to +1.0 (sangat senang)
    feeling: str      # 'sangat_senang' | 'senang' | 'biasa' | 'sakit' | 'sangat_sakit'
    error_type: Optional[str] = None  # 'syntax' | 'runtime' | 'timeout' | None


# ---------------------------------------------------------------------------
# Scoring algorithm — adaptive based on outcome + cost
# ---------------------------------------------------------------------------
def compute_score(
    success: bool,
    elapsed_ms: int,
    code_length: int,
    error_text: str = "",
    exit_code: int = 0,
) -> CodeExecutionScore:
    """Score code execution outcome.

    Pattern:
      success + fast (<100ms)  → +0.8 sangat_senang
      success + medium (<2s)   → +0.5 senang
      success + slow (>2s)     → +0.2 biasa (still ok)
      syntax error             → -0.3 sakit (mild — easy fix)
      runtime error            → -0.6 sakit (real pain — needs debug)
      timeout                  → -0.9 sangat_sakit (worst — infinite loop or hang)
    """
    if success:
        if elapsed_ms < 100:
            score, feeling = 0.8, "sangat_senang"
        elif elapsed_ms < 2000:
            score, feeling = 0.5, "senang"
        else:
            score, feeling = 0.2, "biasa"
        return CodeExecutionScore(
            success=True, elapsed_ms=elapsed_ms, code_length=code_length,
            score=score, feeling=feeling,
        )

    # Failure path — classify error type
    error_lower = (error_text or "").lower()
    if exit_code == -1 or "timeout" in error_lower:
        return CodeExecutionScore(
            success=False, elapsed_ms=elapsed_ms, code_length=code_length,
            score=-0.9, feeling="sangat_sakit", error_type="timeout",
        )
    if "syntaxerror" in error_lower or "indentationerror" in error_lower:
        return CodeExecutionScore(
            success=False, elapsed_ms=elapsed_ms, code_length=code_length,
            score=-0.3, feeling="sakit", error_type="syntax",
        )
    # Default: runtime error
    return CodeExecutionScore(
        success=False, elapsed_ms=elapsed_ms, code_length=code_length,
        score=-0.6, feeling="sakit", error_type="runtime",
    )


# ---------------------------------------------------------------------------
# Adaptive lesson capture — JANGAN blanket save
# ---------------------------------------------------------------------------
def should_save_lesson(
    score: CodeExecutionScore,
    code: str,
    context: Optional[dict] = None,
) -> tuple[bool, str]:
    """Decide adaptively: should this execution be saved as lesson?

    Returns (save: bool, bucket: 'nafs' | 'hikmah' | None).

    Per Adaptive Design Doctrine — NOT every execution saves a lesson.
    Only save when:
      - Failure with substantial code (debugging lesson) → nafs
      - High-score success with complex code (pattern wisdom) → hikmah
      - Repeated success on similar task (mastery) → hikmah
    Skip:
      - Trivial code (<50 chars)
      - Casual one-liners
      - Failed attempts on tiny code (just user typo)
    """
    context = context or {}

    # Skip trivial
    if score.code_length < 50:
        return False, ""

    # Strong failure with non-trivial code → nafs (self-awareness)
    if not score.success and score.code_length > 80:
        return True, "nafs"

    # Strong success with substantial code → hikmah (pattern wisdom)
    if score.success and score.score >= 0.5 and score.code_length > 150:
        return True, "hikmah"

    # User explicit "save this pattern"
    if context.get("save_explicit") is True:
        return True, context.get("bucket", "hikmah")

    return False, ""


# ---------------------------------------------------------------------------
# Summarize for memory entry (compact, useful for recall)
# ---------------------------------------------------------------------------
def summarize_for_lesson(
    code: str,
    score: CodeExecutionScore,
    error_text: str = "",
    success_output: str = "",
) -> str:
    """Create human-readable summary for memory bucket entry.

    Adaptive content:
      - Failure: code + error → "Belajar dari gagal: <error>"
      - Success: code summary + outcome → "Pattern berhasil: <signature>"
    """
    # First line / func signature for code identification
    first_line = code.strip().split("\n", 1)[0][:120]

    if not score.success:
        err_preview = (error_text or "").strip()[:200]
        return (
            f"[CodeLab • {score.feeling}] Belajar dari gagal\n"
            f"Kode: {first_line}\n"
            f"Error ({score.error_type}): {err_preview}\n"
            f"Lesson: hindari pattern ini atau cek pre-validation."
        )
    # Success
    out_preview = (success_output or "").strip()[:200]
    return (
        f"[CodeLab • {score.feeling}] Pattern berhasil\n"
        f"Kode: {first_line}\n"
        f"Output: {out_preview}\n"
        f"Score: {score.score:.2f} • elapsed {score.elapsed_ms}ms"
    )


# ---------------------------------------------------------------------------
# Public API: enrich tool result with scoring
# ---------------------------------------------------------------------------
def enrich_execution(
    code: str,
    success: bool,
    elapsed_ms: int,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
    context: Optional[dict] = None,
) -> dict:
    """Public API: take raw execution result, add scoring + adaptive lesson decision.

    Returns dict with:
      - score: CodeExecutionScore as dict
      - lesson: {save: bool, bucket: str, summary: str} OR None
    """
    score = compute_score(
        success=success,
        elapsed_ms=elapsed_ms,
        code_length=len(code),
        error_text=stderr,
        exit_code=exit_code,
    )

    save, bucket = should_save_lesson(score, code, context)
    lesson = None
    if save and bucket:
        lesson = {
            "save": True,
            "bucket": bucket,
            "summary": summarize_for_lesson(code, score, stderr, stdout),
        }

    logger.info(
        "code_lab.scored",
        success=success,
        elapsed_ms=elapsed_ms,
        code_chars=len(code),
        score=score.score,
        feeling=score.feeling,
        error_type=score.error_type,
        lesson_save=save,
        lesson_bucket=bucket if save else None,
    )

    return {
        "score": asdict(score),
        "lesson": lesson,
    }
