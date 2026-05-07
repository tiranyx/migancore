#!/usr/bin/env python3
"""
MiganCore Cycle 7 Dataset Export — Day 70
==========================================
Combines pairs from DB for ORPO training.

CYCLE 7 PHILOSOPHY — VOICE FIRST, ZERO DOMAIN PAIRS:
Root cause of Cycle 6 ROLLBACK: 300 domain pairs diluted voice (0.705).
Rule: EXCLUDE all domain/engineering/UMKM/legalitas/adaptive pairs this cycle.

Mix formula (target ~260 pairs):
  [PILLAR — must always include, never dilute]
   194  identity_anchor_v2*           — WHO Migan is (P0 pillar, non-negotiable)
   16   cai_pipeline                  — real user conversations (authentic signal)
  ─────────────────────────────────
   ~210 subtotal pillar

  [CYCLE 7 TARGETED — voice recovery + tool fix]
    80  voice_anchor_v1:cycle7        — casual voice recovery (Q5: 0.438)
    40  voice_style_v1:cycle7         — style/tagline voice (Q13: 0.639)
    50  tool_use_v2:cycle7 (write)    — write_file confirm pattern (Q10: 0.698)
    30  tool_use_v2:cycle7 (image)    — generate_image trigger (Q9: 0.768)
    40  creative_v3:cycle7            — creative voice anchored
    20  honesty_v1:cycle7             — epistemic humility (Q19: 0.704)
  ─────────────────────────────────
   ~260 subtotal cycle7 targeted

  TOTAL: ~470 pairs

  EXCLUDED (Cycle 7 moratorium):
  - engineering_fullstack_v1:cycle5
  - umkm_business_v1:cycle5
  - bisnis_legalitas_v1:cycle5
  - indonesia_creative_v1:cycle5
  - adaptive_persona_v1:cycle5
  - evolution_aware_*:cycle5/cycle6
  - tool_use_anchor_v1 (old — superseded by v2:cycle7)
  - creative_anchor_v1:cycle6 (superseded by v3:cycle7)

Gate targets for Cycle 7 PROMOTE (from CYCLE7_DATASET_PLAN.md):
  weighted_avg  >= 0.92
  identity      >= 0.90  (Cycle 6: 0.9334 — already passing)
  voice         >= 0.85  (Cycle 6: 0.705  — need +0.145, hardest gate)
  evo-aware     >= 0.80  (Cycle 6: 0.8856 — already passing, not trained this cycle)
  tool-use      >= 0.85  (Cycle 6: 0.733  — need +0.117)
  creative      >= 0.80  (Cycle 6: 0.771  — need +0.029)

Usage:
  cp /opt/ado/training/export_cycle7_dataset.py /opt/ado/data/workspace/

  # Dry run:
  docker compose exec -T api python /app/workspace/export_cycle7_dataset.py --dry-run

  # Full export:
  docker compose exec -T api python /app/workspace/export_cycle7_dataset.py \\
    --output /app/workspace/cycle7_dataset.jsonl

Author: Claude Sonnet 4.6, Day 70
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, "/app")

# ─── Include sources ───────────────────────────────────────────────────────
INCLUDE_SOURCES = [
    # Pillar (always include)
    "identity_anchor_v2",
    "cai_pipeline",
    # Cycle 7 targeted
    "voice_anchor_v1:cycle7",
    "voice_style_v1:cycle7",
    "tool_use_v2:cycle7",
    "creative_v3:cycle7",
    "honesty_v1:cycle7",
]

# ─── Exclude sources (domain moratorium) ──────────────────────────────────
EXCLUDE_SOURCES = [
    "engineering_fullstack_v1:cycle5",
    "umkm_business_v1:cycle5",
    "bisnis_legalitas_v1:cycle5",
    "indonesia_creative_v1:cycle5",
    "adaptive_persona_v1:cycle5",
    "voice_anchor_v1:cycle5",      # older voice pairs superseded
    "evolution_aware_v2:cycle5",
    "evolution_aware_v3:cycle6",
    "tool_use_anchor_v1",          # old tool pairs
    "tool_use_anchor_v2:cycle6",   # old tool pairs (superseded by v2:cycle7)
    "creative_anchor_v1:cycle6",   # superseded by v3:cycle7
    "code_correctness_v1",         # exclude this cycle (not a failure)
    "distill_kimi_v1",             # small signal, exclude
]

# NOTE: preference_pairs table has NO category column (Day 70 schema audit).
# Filtering is done by source_method only. CATEGORY_INCLUDE removed.


def to_trl_format(row) -> dict:
    """Convert DB row to TRL ORPO format."""
    return {
        "prompt": row.prompt,
        "chosen": row.chosen,
        "rejected": row.rejected,
    }


async def export_async(args):
    from sqlalchemy import text
    import models.base as _base
    from models.base import init_engine
    init_engine()

    # Real schema columns: id, prompt, chosen, rejected, judge_score, judge_model,
    # source_method, source_message_id, created_at, used_in_training_run_id
    # NO category, quality_score, is_validated (Day 70 schema audit)

    async with _base.AsyncSessionLocal() as db:
        # Build query — filter by source_method only (no category/is_validated columns)
        source_placeholders = ", ".join(f":s{i}" for i in range(len(INCLUDE_SOURCES)))
        exclude_placeholders = ", ".join(f":e{i}" for i in range(len(EXCLUDE_SOURCES)))

        source_params = {f"s{i}": v for i, v in enumerate(INCLUDE_SOURCES)}
        exclude_params = {f"e{i}": v for i, v in enumerate(EXCLUDE_SOURCES)}

        query = text(f"""
            SELECT prompt, chosen, rejected, source_method
            FROM preference_pairs
            WHERE source_method IN ({source_placeholders})
              AND source_method NOT IN ({exclude_placeholders})
              AND LENGTH(chosen) > 20
              AND LENGTH(rejected) > 20
              AND chosen != rejected
            ORDER BY created_at ASC
        """)

        result = await db.execute(query, {**source_params, **exclude_params})
        rows = result.fetchall()

    # Stats
    from collections import Counter
    source_counts = Counter(r.source_method for r in rows)

    print(f"\n{'='*55}")
    print(f"CYCLE 7 EXPORT SUMMARY")
    print(f"{'='*55}")
    print(f"Total pairs: {len(rows)}")
    print(f"\nBy source:")
    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        included = "[include]" if any(src.startswith(s) for s in INCLUDE_SOURCES) else "[?]"
        print(f"  {included} {count:4d}  {src}")

    if args.dry_run:
        print(f"\n[DRY RUN] — no file written")
        print(f"Would write {len(rows)} pairs to JSONL")
        return

    # Write JSONL
    output_path = args.output
    written = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for row in rows:
            pair = to_trl_format(row)
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
            written += 1

    print(f"\nExported: {written} pairs → {output_path}")
    print(f"\nNext steps:")
    print(f"  1. Verify: wc -l {output_path}")
    print(f"  2. Train on Vast.ai: python training/cycle7_orpo_vast.py")
    print(f"  3. Eval: python eval/run_identity_eval.py --mode eval --model-tag migancore-7b-soul-cycle7")
    print(f"     Gate: weighted_avg >= 0.92 AND voice >= 0.85 AND tool-use >= 0.85")


def main():
    parser = argparse.ArgumentParser(description="MiganCore Cycle 7 Dataset Export")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show stats without writing file")
    parser.add_argument("--output", default="/app/workspace/cycle7_dataset.jsonl",
                        help="Output JSONL path")
    args = parser.parse_args()

    import asyncio
    asyncio.run(export_async(args))


if __name__ == "__main__":
    main()
