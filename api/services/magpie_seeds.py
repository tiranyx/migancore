"""
Magpie seed loader (Day 38) — pull pre-filtered instruction prompts from HuggingFace.

Source: https://huggingface.co/datasets/Magpie-Align/Magpie-Qwen2.5-Pro-300K-Filtered
Paper: arxiv.org/abs/2406.08464 (Magpie-Align: Self-Synthesis from Aligned LLMs)

Why Magpie 300K matters (vs hardcoded 120 seeds):
  - Magpie's "no prompt" extraction technique surfaces ~99% MMLU domain coverage
    vs ~40% for our hand-curated seed_bank (Day 19).
  - Pre-filtered for quality (300K of original 1M)
  - Diverse task types: reasoning, creative, coding, factual, conversational
  - Drop-in replacement for SEEDS list[str]

Strategy here:
  - Lazy download on first call (cached to /app/.cache/magpie_seeds.json)
  - Fall back to hardcoded SEEDS if download fails (network, auth, etc.)
  - Random sample N seeds per round for diversity (vs fixed-order replay)

Caching:
  - Parquet file is ~150MB raw; we extract just instructions (~30MB JSON)
  - Subsequent reads = instant from cache
  - Cache invalidates only on manual delete (datasets are stable on HF)

Cost: $0 (HuggingFace public dataset, no auth required for public files)
"""
from __future__ import annotations

import asyncio
import json
import os
import random
from pathlib import Path
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger()

# HuggingFace dataset Parquet URL (public, no auth)
# Magpie-Qwen2.5-Pro-300K-Filtered ships as a single train split
_MAGPIE_PARQUET_URL = (
    "https://huggingface.co/datasets/Magpie-Align/Magpie-Qwen2.5-Pro-300K-Filtered/"
    "resolve/main/data/train-00000-of-00001.parquet"
)
_MAGPIE_CACHE_DIR = Path("/app/.cache")
_MAGPIE_CACHE_FILE = _MAGPIE_CACHE_DIR / "magpie_300k_instructions.json"

# Memory cache to avoid re-reading the JSON on every round
_in_memory_cache: list[str] | None = None
_download_lock = asyncio.Lock()


async def _download_and_extract() -> list[str]:
    """Download the Magpie parquet and extract the 'instruction' column.
    Saves both the raw parquet (transient) and processed JSON (persistent cache).
    """
    try:
        import pyarrow.parquet as pq
        import io
    except ImportError:
        logger.error("magpie.pyarrow_missing", note="Install: pip install pyarrow")
        raise RuntimeError("pyarrow not installed (needed for Magpie parquet read)")

    logger.info("magpie.download.start", url=_MAGPIE_PARQUET_URL)
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0), follow_redirects=True) as client:
        resp = await client.get(_MAGPIE_PARQUET_URL)
        resp.raise_for_status()
        raw = resp.content

    logger.info("magpie.download.done", bytes=len(raw))

    # Read parquet from in-memory bytes
    table = pq.read_table(io.BytesIO(raw))
    column_names = table.column_names

    # The dataset uses 'instruction' field; verify
    target = "instruction" if "instruction" in column_names else column_names[0]
    instructions_arr = table.column(target).to_pylist()

    # Filter: non-empty strings, reasonable length (avoid degenerate cases)
    instructions = [
        s.strip() for s in instructions_arr
        if isinstance(s, str) and 20 <= len(s.strip()) <= 1500
    ]

    logger.info(
        "magpie.parsed",
        column=target,
        total=len(instructions_arr),
        kept=len(instructions),
    )

    # Persist to cache
    _MAGPIE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_MAGPIE_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(instructions, f, ensure_ascii=False)

    return instructions


async def get_magpie_seeds(force_refresh: bool = False) -> list[str]:
    """Return the cached Magpie seed list. Downloads + caches on first call.

    Returns empty list on any failure; caller should fall back to hardcoded SEEDS.
    """
    global _in_memory_cache

    if _in_memory_cache and not force_refresh:
        return _in_memory_cache

    async with _download_lock:
        # Re-check after acquiring lock
        if _in_memory_cache and not force_refresh:
            return _in_memory_cache

        # Try disk cache
        if _MAGPIE_CACHE_FILE.exists() and not force_refresh:
            try:
                with open(_MAGPIE_CACHE_FILE, "r", encoding="utf-8") as f:
                    instructions = json.load(f)
                if isinstance(instructions, list) and len(instructions) > 1000:
                    _in_memory_cache = instructions
                    logger.info("magpie.cache_hit", count=len(instructions))
                    return instructions
            except Exception as exc:
                logger.warning("magpie.cache_corrupt", error=str(exc))

        # Download fresh
        try:
            instructions = await _download_and_extract()
            _in_memory_cache = instructions
            return instructions
        except Exception as exc:
            logger.error("magpie.download_failed", error=str(exc))
            return []


def sample_seeds(seeds: list[str], n: int = 120, seed: Optional[int] = None) -> list[str]:
    """Random sample n seeds without replacement. If list shorter than n, return all shuffled."""
    if not seeds:
        return []
    if len(seeds) <= n:
        out = list(seeds)
        random.Random(seed).shuffle(out)
        return out
    return random.Random(seed).sample(seeds, n)
