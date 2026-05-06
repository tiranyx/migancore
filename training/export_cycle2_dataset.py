#!/usr/bin/env python3
"""
Cycle 2 Dataset Export — Day 58

Exports the curated Cycle 2 training mix for SimPO fine-tuning.
All 620 high-quality pairs — 0% generic synthetic (Day 56 root cause fix).

Mix formula:
  194  identity_anchor_v2      (31%)  — WHO Migan is
  200  tool_use_anchor_v1      (32%)  — HOW Migan uses tools
  200  code_correctness_v1     (32%)  — HOW Migan writes code
   16  cai_pipeline            (3%)   — real user conversations
   10  distill_kimi_v1         (2%)   — teacher-quality distillation
  ─────────────────────────────────────
  620  total                          — 100% curated, 0% generic

Why NO synthetic_seed_v1:
  Day 56 root cause: 84.5% generic synthetic overwrote identity.
  Cycle 2 = clean slate: all 620 pairs are identity/voice/task-anchored.
  Add synthetic back in Cycle 3 if diversity gap emerges in eval.

Output format: TRL/Unsloth-compatible JSONL
  {"prompt": "...", "chosen": "...", "rejected": "..."}

Usage:
  docker compose exec -T api python /app/workspace/export_cycle2_dataset.py \
    --output /app/workspace/cycle2_dataset.jsonl

Day 58 — Claude Code implementor
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")

from sqlalchemy import text


# Sources to include in Cycle 2 mix — in priority order
CYCLE2_SOURCES = [
    # (source_pattern, limit, label)
    ("identity_anchor_v2%", 200, "identity"),   # all 194
    ("tool_use_anchor_v1%", 200, "tool_use"),   # all 200
    ("code_correctness_v1%", 200, "code"),      # all 200
    ("cai_pipeline", 20, "cai"),               # all 16
    ("distill_kimi_v1", 20, "distill"),        # all 10
]


async def export_cycle2(output_path: str, verbose: bool = False) -> dict:
    """Export Cycle 2 dataset. Returns summary dict."""
    import models.base as _base
    from models.base import init_engine

    init_engine()

    samples = []
    by_source: dict[str, int] = {}

    async with _base.AsyncSessionLocal() as session:
        for source_pattern, limit, label in CYCLE2_SOURCES:
            if "%" in source_pattern:
                q = """
                    SELECT prompt, chosen, rejected, source_method, judge_score
                    FROM preference_pairs
                    WHERE source_method LIKE :pattern
                    ORDER BY judge_score DESC NULLS LAST, created_at ASC
                    LIMIT :limit
                """
            else:
                q = """
                    SELECT prompt, chosen, rejected, source_method, judge_score
                    FROM preference_pairs
                    WHERE source_method = :pattern
                    ORDER BY judge_score DESC NULLS LAST, created_at ASC
                    LIMIT :limit
                """

            res = await session.execute(
                text(q), {"pattern": source_pattern, "limit": limit}
            )
            rows = res.fetchall()
            for row in rows:
                samples.append({
                    "prompt": row[0],
                    "chosen": row[1],
                    "rejected": row[2],
                    "_source": row[3],
                    "_score": float(row[4]) if row[4] is not None else None,
                    "_label": label,
                })
                by_source[label] = by_source.get(label, 0) + 1

            print(f"  {label:15s}: {len(rows)} pairs (pattern: {source_pattern})")

    # Sanity check: no duplicates
    seen_prompts = set()
    deduped = []
    dupe_count = 0
    for s in samples:
        key = s["prompt"][:100]  # first 100 chars as dedup key
        if key not in seen_prompts:
            seen_prompts.add(key)
            deduped.append(s)
        else:
            dupe_count += 1
    if dupe_count:
        print(f"  WARN: removed {dupe_count} duplicate prompts")
    samples = deduped

    # Validate: check no "Anthropic" in chosen
    anthropic_hits = [s for s in samples if "Anthropic" in s["chosen"] and "onamix_search" not in s["chosen"]]
    if anthropic_hits:
        print(f"  WARN: {len(anthropic_hits)} chosen responses mention 'Anthropic' without tool call")
        for h in anthropic_hits[:3]:
            print(f"    - {h['_source']}: {h['chosen'][:100]}")

    # Write JSONL (clean format, no internal fields)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for s in samples:
            clean = {k: v for k, v in s.items() if not k.startswith("_")}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")

    # Detailed source breakdown
    detailed_sources: dict[str, int] = {}
    for s in samples:
        src = s["_source"]
        detailed_sources[src] = detailed_sources.get(src, 0) + 1

    summary = {
        "total": len(samples),
        "by_label": by_source,
        "by_source_method": detailed_sources,
        "duplicates_removed": dupe_count,
        "anthropic_in_chosen_warns": len(anthropic_hits),
        "output": str(out.resolve()),
    }

    return summary


def main():
    parser = argparse.ArgumentParser(description="Export Cycle 2 training dataset")
    parser.add_argument("--output", default="/app/workspace/cycle2_dataset.jsonl",
                        help="Output JSONL path")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Cycle 2 Dataset Export")
    print(f"{'='*60}")
    print(f"Sources:")

    summary = asyncio.run(export_cycle2(args.output, args.verbose))

    print(f"\n{'='*60}")
    print(f"EXPORT SUMMARY")
    print(f"{'='*60}")
    print(f"  Total pairs: {summary['total']}")
    print(f"  By label:")
    for label, cnt in sorted(summary['by_label'].items(), key=lambda x: -x[1]):
        print(f"    {label:20s} {cnt}")
    if summary['duplicates_removed']:
        print(f"  Duplicates removed: {summary['duplicates_removed']}")
    if summary['anthropic_in_chosen_warns']:
        print(f"  WARN - Anthropic mentions: {summary['anthropic_in_chosen_warns']}")
    print(f"  Output: {summary['output']}")
    print(f"{'='*60}")
    print(f"\nKPI check: 550-650 pairs → {'PASS' if 550 <= summary['total'] <= 650 else 'FAIL'}")
    print(f"Next: Copy to GPU cloud and run SimPO training (separate GO required)\n")


if __name__ == "__main__":
    main()
