"""
Day 71d: Semantic Tool Filter
==============================
Reduces tool-detection prompt size by selecting top-K most relevant tools per query.

Problem (Lesson #180): Sending all 29 tool specs to LLM = ~3000 tokens of context
  per chat → tool-detection inference time 60-180s on CPU 7B model.

Solution: Pre-compute tool description embeddings once. On each chat:
  1. Embed user query (paraphrase-multilingual-mpnet, 768-dim, ~50ms)
  2. Compute cosine similarity vs each tool embedding
  3. Return top-K (default 6) most relevant + always-include set

Empirical impact: 29 tools (3000 tokens) → 6 tools (~600 tokens) = 5x prompt reduction.
Translates to ~40-60% faster tool-detection on CPU inference.

Strategy:
  - ALWAYS include core tools (memory_write, memory_search) — proactive use
  - Top-K=4 from semantic match
  - Total per query: 4 semantic + 2 always = 6 tools
  - Fallback to all tools if embedding model unavailable
"""

from __future__ import annotations

import math
from typing import Optional

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Tools that are ALWAYS in spec (proactive/general-purpose)
# Memory: brain should write/search proactively
ALWAYS_INCLUDE = {'memory_write', 'memory_search'}

# Top-K from semantic match (excluding ALWAYS_INCLUDE)
DEFAULT_TOP_K = 4

# Day 74 — minimum cosine similarity to even pass a tool to the brain.
# Below this, the brain answers from its own knowledge (per biomimetic
# doctrine: tools are vitamin, not oxygen). Empirically 0.56 was the
# top score on a URL-bearing prompt that triggered 180s tool-call
# timeouts — well below this threshold, so no tool should have been
# offered. Tunable via env.
import os as _os
RELEVANCE_THRESHOLD = float(_os.getenv("TOOL_RELEVANCE_THRESHOLD", "0.60"))

# Pre-computed embeddings cache: dict[tool_name, list[float]]
_tool_embeddings: dict[str, list[float]] = {}
_embeddings_ready = False


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two embedding vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    n1 = math.sqrt(sum(x * x for x in a))
    n2 = math.sqrt(sum(y * y for y in b))
    return dot / (n1 * n2 + 1e-12)


async def precompute_tool_embeddings() -> int:
    """Embed all tool descriptions from skills.json once at boot.

    Returns: number of tools embedded (or 0 if model unavailable).
    Idempotent: safe to call multiple times.
    """
    global _tool_embeddings, _embeddings_ready

    if _embeddings_ready:
        return len(_tool_embeddings)

    try:
        from services.tool_executor import load_skills_config
        from services.embedding import get_model
    except ImportError as e:
        logger.warning("tool_relevance.import_fail: %s", e)
        return 0

    skills_cfg = load_skills_config()
    skills = skills_cfg.get('skills', [])
    if not skills:
        logger.warning("tool_relevance.no_skills")
        return 0

    try:
        model = await get_model()
    except Exception as e:
        logger.warning("tool_relevance.model_unavailable: %s", e)
        return 0

    # Build description corpus: id + display_name + description
    docs = []
    ids = []
    for s in skills:
        sid = s.get('id', '')
        if not sid:
            continue
        text = f"{sid}: {s.get('display_name', '')} — {s.get('description', '')[:300]}"
        docs.append(text)
        ids.append(sid)

    try:
        embeddings = list(model.embed(docs))
    except Exception as e:
        logger.error("tool_relevance.embed_fail: %s", e)
        return 0

    _tool_embeddings = {sid: list(map(float, emb)) for sid, emb in zip(ids, embeddings)}
    _embeddings_ready = True
    logger.info("tool_relevance.ready", count=len(_tool_embeddings))
    return len(_tool_embeddings)


async def select_relevant_tools(
    user_query: str,
    available_tools: list[str],
    top_k: int = DEFAULT_TOP_K,
) -> list[str]:
    """Return top-K most relevant tools for user_query, plus ALWAYS_INCLUDE.

    Args:
        user_query: User's last message (or last few turns concatenated).
        available_tools: List of tool names available to the agent.
        top_k: How many semantic-match tools to include (excluding ALWAYS_INCLUDE).

    Returns:
        Ordered list of tool names. Length ≤ top_k + len(ALWAYS_INCLUDE).
        On embedding failure: returns full available_tools (safe fallback).
    """
    # Boot embeddings if not ready
    if not _embeddings_ready:
        await precompute_tool_embeddings()

    if not _embeddings_ready or not user_query.strip():
        # Fallback: return all tools
        return list(available_tools)

    # If we have <= top_k + ALWAYS, no filtering needed
    if len(available_tools) <= top_k + len(ALWAYS_INCLUDE):
        return list(available_tools)

    try:
        from services.embedding import get_model
        model = await get_model()
        query_emb_list = list(model.embed([user_query[:500]]))
        if not query_emb_list:
            return list(available_tools)
        query_emb = list(map(float, query_emb_list[0]))
    except Exception as e:
        logger.warning("tool_relevance.query_embed_fail: %s", e)
        return list(available_tools)

    # Score available tools (skip ALWAYS_INCLUDE in ranking)
    candidate_tools = [t for t in available_tools if t not in ALWAYS_INCLUDE]
    scored = []
    for tool in candidate_tools:
        emb = _tool_embeddings.get(tool)
        if not emb:
            continue
        score = _cosine_sim(query_emb, emb)
        scored.append((score, tool))

    scored.sort(key=lambda x: -x[0])

    # Day 74 — only offer tools whose score exceeds RELEVANCE_THRESHOLD.
    # If best score < threshold, return EMPTY so chat skips the tool loop
    # entirely and goes straight to plain streaming. Even handing brain just
    # memory_* tools forces Ollama's tool-call mode (extra reasoning + slower
    # generation on CPU 7B), which was hitting the 90s timeout on substantive
    # prompts. Background CAI still extracts facts post-response.
    top_score = scored[0][0] if scored else 0.0
    if top_score < RELEVANCE_THRESHOLD:
        logger.info(
            "tool_relevance.low_confidence_skip",
            query_len=len(user_query),
            top_score=f"{top_score:.3f}",
            threshold=RELEVANCE_THRESHOLD,
            kept=0,
        )
        return []

    top_tools = [tool for _score, tool in scored[:top_k] if _score >= RELEVANCE_THRESHOLD]

    # Combine: ALWAYS_INCLUDE (filtered to available) + top-K
    always_present = [t for t in ALWAYS_INCLUDE if t in available_tools]
    result = always_present + top_tools

    logger.info(
        "tool_relevance.selected",
        query_len=len(user_query),
        available=len(available_tools),
        selected=len(result),
        top_scores=[f"{s:.3f}" for s, _t in scored[:3]],
        threshold=RELEVANCE_THRESHOLD,
    )
    return result


def is_ready() -> bool:
    """Check if tool embeddings are pre-computed."""
    return _embeddings_ready


def stats() -> dict:
    """Diagnostic: how many tool embeddings cached."""
    return {
        'ready': _embeddings_ready,
        'count': len(_tool_embeddings),
        'always_include': sorted(ALWAYS_INCLUDE),
        'default_top_k': DEFAULT_TOP_K,
    }
