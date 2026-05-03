"""
Episodic context retrieval — Day 16.

Reads semantic memory from Qdrant and formats it for system prompt injection.
Converts Qdrant from write-only (Day 12) to read-write — the missing half.

Architecture:
  - Synchronous (not fire-and-forget): result needed BEFORE Ollama call
  - Timeout 1.5s: safety valve — Qdrant <10k vectors typically returns <200ms
  - Top-k search = 5 (fetch candidates), top-k inject = 3 (research: >3 confuses 7B)
  - Score threshold = 0.65 (stricter than index 0.55)
  - Sort by relevance descending (NOT by recency — see research notes below)
  - Position: injected LAST in system prompt (freshest → highest attention weight)

Separate concerns (recency vs relevance):
  - Recency  → Message history (CONTEXT_WINDOW_MESSAGES=5) — wired in chat.py
  - Relevance → Qdrant semantic search (entire history)     — THIS FILE

Research findings (Day 16 research report):
  - Score threshold: 0.70 English → 0.65 Bahasa Indonesia (multilingual MPNet
    produces 5-8% lower cross-lingual similarity scores vs English pairs)
    Sources: arxiv 2409.12524, Zep production, LlamaIndex guide
  - Top-k inject = 3: production finding (Mem0 2025) — 7B models overwhelmed by >3-5 chunks
  - Sort by relevance: recency-sorted injection degrades accuracy up to 30%
    due to "lost in the middle" effect (arxiv 2505.15561)
  - Format: numbered list [N] + role-per-line — outperforms chain-of-thought
    for 7B models (LangMem, Memoria paper arxiv 2512.12686)
  - Context cap: ≤1000 tokens injected; beyond this, 7B ignores context
  - Query embedding: embed user message only (document = user+assistant pair) ✓
    Already correct in search_semantic() — avoids query-document format mismatch
  - CRAG/Self-RAG: NOT practical for CPU-only 7B without fine-tuning. Skip.

Sources: arxiv 2502.06975, 2501.13956, 2504.19413, 2512.12686, 2409.12524,
         2511.07587, LangMem docs, Mem0 production blog, Zep docs, LUFY (ACL 2025)
"""

import asyncio
from datetime import datetime, timezone

import structlog

from services.vector_memory import search_semantic

logger = structlog.get_logger()

# Search more candidates, inject fewer — avoid overwhelming 7B model
_TOP_K_SEARCH: int = 5     # Fetch from Qdrant (includes threshold filter)
TOP_K_INJECT: int = 3      # Max chunks injected into system prompt

# 0.70 recommended for English; -5-8% for Bahasa Indonesia → 0.65
# Lower than 0.65 = noise injection; higher = misses relevant context
RETRIEVAL_SCORE_THRESHOLD: float = 0.65

# Safety valve: Qdrant cosine search on <10k vectors typically <200ms
RETRIEVAL_TIMEOUT_S: float = 1.5

# Per-chunk truncation — total max injection ≈ TOP_K_INJECT × 350 chars ≈ 1050 chars ≈ 260 tokens
_MAX_USER_CHARS: int = 150
_MAX_ASSISTANT_CHARS: int = 200


def _format_timestamp(ts: int | None) -> str:
    """Convert Unix timestamp to readable date (UTC)."""
    if not ts:
        return "sebelumnya"
    try:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return "sebelumnya"


def format_episodic_context(results: list[dict]) -> str:
    """Format retrieved episodic turns as a system prompt section.

    Returns empty string if results is empty (no Qdrant injection = no change).

    Sort order: by _retrieval_score descending (highest relevance first).
    Research (arxiv 2505.15561, "Lost in the Middle"): 7B models have primacy
    attention bias — highest relevance chunk FIRST maximizes recall accuracy.
    Do NOT sort by timestamp — recency-sorted injection degrades accuracy ~30%.

    Format (per LangMem, Memoria research — optimal for 7B models):

        [KONTEKS EPISODIK — percakapan relevan sebelumnya]

        [1] (YYYY-MM-DD)
        Pengguna: "..."
        Asisten: "..."

        [2] ...

    Truncation at 150/200 chars per side preserves semantic meaning while
    keeping total injection under ~1000 tokens.
    """
    if not results:
        return ""

    # Sort by relevance descending — highest relevance → first position → primacy bias
    sorted_results = sorted(
        results,
        key=lambda r: r.get("_retrieval_score", 0.0),
        reverse=True,
    )

    lines = ["[KONTEKS EPISODIK — percakapan relevan sebelumnya]"]
    for i, r in enumerate(sorted_results[:TOP_K_INJECT], 1):
        date_str = _format_timestamp(r.get("timestamp"))
        user_raw = (r.get("user_message") or "").strip()
        asst_raw = (r.get("assistant_message") or "").strip()

        # Truncate + ellipsis marker so model knows content continues
        user_text = user_raw[:_MAX_USER_CHARS]
        if len(user_raw) > _MAX_USER_CHARS:
            user_text += "..."

        asst_text = asst_raw[:_MAX_ASSISTANT_CHARS]
        if len(asst_raw) > _MAX_ASSISTANT_CHARS:
            asst_text += "..."

        # Two-line format: role labels on separate lines (clearer for 7B models)
        lines.append(f"\n[{i}] ({date_str})")
        lines.append(f'Pengguna: "{user_text}"')
        lines.append(f'Asisten: "{asst_text}"')

    return "\n".join(lines)


async def retrieve_episodic_context(
    agent_id: str,
    query: str,
) -> list[dict]:
    """Retrieve semantically relevant past turns for context injection.

    Called synchronously before system prompt construction — result required
    before Ollama inference call.

    Returns [] on:
      - asyncio.TimeoutError (Qdrant slow/overloaded)
      - Any Qdrant error (collection missing, service down)
      - Empty collection (first chat with this agent)
      - No results above RETRIEVAL_SCORE_THRESHOLD (0.65)

    Score threshold 0.65 overrides vector_memory.py's default 0.55 — stricter
    filtering needed for injection (noisy context hurts 7B models more than
    missing context).
    """
    try:
        results = await asyncio.wait_for(
            search_semantic(
                agent_id=agent_id,
                query=query,
                top_k=_TOP_K_SEARCH,
                score_threshold=RETRIEVAL_SCORE_THRESHOLD,
            ),
            timeout=RETRIEVAL_TIMEOUT_S,
        )

        if results:
            # Log top score for threshold calibration during testing
            top_score = results[0].get("_retrieval_score", 0.0) if results else 0.0
            logger.info(
                "retrieval.episodic_found",
                agent_id=agent_id,
                count=len(results),
                top_score=top_score,
                query_preview=query[:60],
            )
        else:
            logger.debug("retrieval.episodic_empty", agent_id=agent_id)

        return results

    except asyncio.TimeoutError:
        logger.warning(
            "retrieval.timeout",
            agent_id=agent_id,
            timeout_s=RETRIEVAL_TIMEOUT_S,
        )
        return []

    except Exception as exc:
        logger.warning(
            "retrieval.error",
            agent_id=agent_id,
            error=str(exc),
        )
        return []
