"""
Onboarding router (Day 37) — first-run experience for new beta users.

Pattern adopted: "two-question onboarding" (Perplexity Spaces / Letta blog Mar 2026)
                 instead of multi-template picker (Cursor/Claude killed it Q1 2026).

Endpoints:
  - GET /v1/onboarding/starters?usecase=...&lang=... -> 3 dynamic starter prompts
    Backed by Gemini 2.5 Flash (cheap: ~$0.0001/call). Fallback to hardcoded.

Auth: open (no JWT) — onboarding fires before/during first login. Rate-limited.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Query
from pydantic import BaseModel

from deps.rate_limit import limiter
from fastapi import Request

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/onboarding", tags=["onboarding"])


# ---------------------------------------------------------------------------
# Hardcoded fallback starters — ALWAYS returned if dynamic generation fails.
# Designed to be useful regardless of the user's stated use case.
# ---------------------------------------------------------------------------
_FALLBACK_STARTERS_ID = {
    "research": [
        "Bantu saya rangkum tren AI agent 2026 dalam 5 poin",
        "Apa perbedaan SimPO vs DPO untuk training LLM kecil?",
        "Buatkan outline riset tentang memory persistence di LLM",
    ],
    "coding": [
        "Review fungsi Python ini dan kasih saran perbaikan",
        "Bantu saya debug error 'TypeError: cannot read property of undefined'",
        "Jelaskan trade-off async/await vs threading dalam Python",
    ],
    "writing": [
        "Bantu saya buat draf email follow-up ke calon investor",
        "Edit paragraf ini biar lebih ringkas tanpa kehilangan makna",
        "Brainstorm 5 judul artikel tentang produktivitas remote",
    ],
    "general": [
        "Apa yang bisa kamu lakukan? Kasih 3 contoh konkret",
        "Bantu saya rencanakan to-do list hari ini",
        "Jelaskan satu konsep kompleks dengan analogi sederhana",
    ],
}

_FALLBACK_STARTERS_EN = {
    "research": [
        "Summarize the top AI agent trends of 2026 in 5 bullet points",
        "What's the difference between SimPO and DPO for small LLM training?",
        "Draft a research outline on persistent memory in LLMs",
    ],
    "coding": [
        "Review this Python function and suggest improvements",
        "Help me debug a 'TypeError: cannot read property of undefined' error",
        "Explain async/await vs threading trade-offs in Python",
    ],
    "writing": [
        "Help me draft a follow-up email to a potential investor",
        "Edit this paragraph to be more concise without losing meaning",
        "Brainstorm 5 article titles about remote productivity",
    ],
    "general": [
        "What can you do? Give me 3 concrete examples",
        "Help me plan my to-do list for today",
        "Explain a complex concept with a simple analogy",
    ],
}


class StartersResponse(BaseModel):
    starters: list[str]
    source: str  # "gemini" | "fallback_id" | "fallback_en"
    lang: str
    usecase: str


def _normalize_usecase(usecase: str) -> str:
    """Map free-text usecase to one of our 4 buckets."""
    u = (usecase or "").lower().strip()
    if any(k in u for k in ["riset", "research", "study", "belajar", "academic", "paper"]):
        return "research"
    if any(k in u for k in ["code", "coding", "program", "develop", "engineer", "debug"]):
        return "coding"
    if any(k in u for k in ["tulis", "write", "writ", "edit", "content", "copy", "blog"]):
        return "writing"
    return "general"


def _normalize_lang(lang: str) -> str:
    """Map lang to 'id' or 'en'. Mix defaults to id."""
    l = (lang or "id").lower().strip()
    if l in ("en", "english", "inggris"):
        return "en"
    return "id"


def _hardcoded_starters(usecase: str, lang: str) -> list[str]:
    pool = _FALLBACK_STARTERS_ID if lang == "id" else _FALLBACK_STARTERS_EN
    return pool.get(usecase, pool["general"])


async def _generate_dynamic_starters(usecase: str, lang: str) -> list[str] | None:
    """Try Gemini Flash for personalized starters. Returns None on any failure."""
    from services.teacher_api import call_teacher, is_teacher_available, TeacherError
    if not is_teacher_available("gemini"):
        return None

    lang_label = "Bahasa Indonesia natural" if lang == "id" else "English"
    sys = (
        "You output EXACTLY 3 starter prompts for an AI chat, one per line. "
        "Strict format: each line is a complete actionable prompt the user could "
        "click to begin a conversation. NO numbering. NO bullets. NO preamble. "
        "NO trailing punctuation other than what belongs in a sentence. "
        "Just 3 lines separated by single newlines, nothing else."
    )
    user = (
        f"Use case the user described: {usecase}\n"
        f"Write the 3 prompts in: {lang_label}\n"
        f"Tone: practical, friendly, professional. Avoid generic small talk.\n"
        f"Each prompt should be 8-25 words. Concrete, specific, useful.\n\n"
        f"Output now (3 lines):"
    )
    try:
        # max_tokens=400 — 3 ID prompts ~80-120 tokens each + safety margin
        resp = await call_teacher("gemini", user, system=sys, max_tokens=400)
        # Strip bullets/numbering at line start, then filter by length
        lines = []
        for raw_l in resp.text.splitlines():
            l = raw_l.strip()
            if not l:
                continue
            # Strip leading bullets / numbering
            l = l.lstrip("0123456789.)-•*–— ").strip()
            # Strip surrounding quotes
            if (l.startswith('"') and l.endswith('"')) or (l.startswith("'") and l.endswith("'")):
                l = l[1:-1].strip()
            if 8 <= len(l) <= 200:
                lines.append(l)
        if len(lines) >= 3:
            return lines[:3]
        logger.warning("onboarding.starters_too_few_lines", got=len(lines), raw_preview=resp.text[:200])
        return None
    except TeacherError as exc:
        logger.warning("onboarding.starters_gemini_error", error=str(exc))
        return None
    except Exception as exc:
        logger.warning("onboarding.starters_unknown_error", error=str(exc))
        return None


@router.get("/starters", response_model=StartersResponse)
@limiter.limit("30/minute")
async def get_starters(
    request: Request,
    usecase: str = Query("general", description="Free text from user; mapped to research/coding/writing/general"),
    lang: str = Query("id", description="id | en"),
):
    """Return 3 starter prompts, dynamic via Gemini if available, hardcoded fallback otherwise.

    Called by chat.html First-Run modal AFTER the user answers 2 questions:
      Q1: 'Apa yang ingin kamu lakukan dengan MiganCore?' (free text -> usecase)
      Q2: 'Bahasa: ID/EN/Mix?' (-> lang)
    """
    usecase_n = _normalize_usecase(usecase)
    lang_n = _normalize_lang(lang)

    dynamic = await _generate_dynamic_starters(usecase_n, lang_n)
    if dynamic:
        return StartersResponse(
            starters=dynamic,
            source="gemini",
            lang=lang_n,
            usecase=usecase_n,
        )

    return StartersResponse(
        starters=_hardcoded_starters(usecase_n, lang_n),
        source=f"fallback_{lang_n}",
        lang=lang_n,
        usecase=usecase_n,
    )
