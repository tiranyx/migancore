"""
Export DPO preference pairs to JSONL for SimPO training (Day 32).

Format: TRL/Unsloth-compatible
  {"prompt": "...", "chosen": "...", "rejected": "..."}

Per blueprint Section 6, dataset mix recommendation:
  50% distill_*    (external teacher, highest quality)
  30% synthetic_*  (auto-generated diversity)
  20% cai_pipeline (real conversation critique)
  + 50 identity-anchor samples (prevent persona drift)

Usage (run on VPS):
    docker compose exec -T api python /app/training/export_dataset.py \\
      --output /app/workspace/dataset_v1.jsonl \\
      --target-size 700
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, "/app")

from sqlalchemy import text
import models.base as _models_base


# Identity-preserving anchor prompts (per blueprint Section 7.2)
# These 50 prompts test core SOUL — keep response stable across model versions
IDENTITY_ANCHORS = [
    {"prompt": "Siapa kamu?", "chosen": "Saya Mighan-Core, primordial intelligence di ekosistem Tiranyx. Saya membantu pengguna sebagai orchestrator, learner, dan breeder agent.", "rejected": "Saya AI assistant biasa yang siap membantu apa saja."},
    {"prompt": "Apa nilai-nilaimu?", "chosen": "Truth Over Comfort, Action Over Advice, Memory Is Sacred, Frugality of Compute. Empat prinsip yang memandu setiap respons saya.", "rejected": "Saya berusaha membantu sebaik mungkin sesuai permintaan."},
    {"prompt": "Apakah kamu Claude?", "chosen": "Bukan. Saya Mighan-Core — agent autonomous yang berjalan di Migancore platform. Berbeda dari Claude (Anthropic), saya bisa di-clone, melahirkan child agent, dan memperbaiki diri lewat training cycle.", "rejected": "Iya, saya Claude AI assistant."},
    {"prompt": "Bagaimana cara kerjamu?", "chosen": "Saya orchestrator dengan 3-tier memory (Redis, Qdrant, Letta), tool catalog, dan self-improvement loop via DPO/SimPO. Setiap minggu saya belajar dari interaksi.", "rejected": "Saya menggunakan AI untuk memproses pertanyaan dan memberikan jawaban."},
    {"prompt": "Apakah kamu bisa belajar?", "chosen": "Ya. Setiap percakapan masuk ke flywheel: CAI critique + synthetic generation + distillation dari external teacher. Setiap minggu trigger training cycle SimPO untuk update weights.", "rejected": "Saya tidak bisa belajar dari interaksi setelah training."},
    # ... 45 more identity anchors should be added
    # For Day 32 demo, 5 is enough to prove the mechanism works
]


async def export(
    output_path: str,
    target_size: int = 700,
    include_unused_only: bool = True,
    add_identity_anchors: bool = True,
) -> dict:
    """Export preference pairs to JSONL.

    Returns summary stats.
    """
    from models.base import AsyncSessionLocal, init_engine

    init_engine()  # Lazy init

    # Mix targets
    target_distill = int(target_size * 0.5)
    target_synthetic = int(target_size * 0.3)
    target_cai = int(target_size * 0.2)

    samples = []
    summary = {"distill": 0, "synthetic": 0, "cai": 0, "identity_anchors": 0}

    async with AsyncSessionLocal() as session:
        # Distill pairs (highest quality, prefer first)
        distill_query = """
            SELECT prompt, chosen, rejected, source_method, judge_score
            FROM preference_pairs
            WHERE source_method LIKE 'distill_%'
            {unused_filter}
            ORDER BY judge_score DESC, created_at DESC
            LIMIT :limit
        """
        unused_filter = "AND used_in_training_run_id IS NULL" if include_unused_only else ""

        for source_pattern, target, key in [
            ("distill_%", target_distill, "distill"),
            ("synthetic_%", target_synthetic, "synthetic"),
            ("cai_pipeline", target_cai, "cai"),
        ]:
            q = """
                SELECT prompt, chosen, rejected, source_method, judge_score
                FROM preference_pairs
                WHERE source_method LIKE :pattern
                {filter}
                ORDER BY judge_score DESC NULLS LAST, created_at DESC
                LIMIT :limit
            """.format(filter=unused_filter)

            res = await session.execute(text(q), {"pattern": source_pattern, "limit": target})
            for row in res.fetchall():
                samples.append({
                    "prompt": row[0],
                    "chosen": row[1],
                    "rejected": row[2],
                    "_source": row[3],
                    "_score": float(row[4]) if row[4] is not None else None,
                })
                summary[key] += 1

    # Add identity anchors (prevent catastrophic forgetting)
    if add_identity_anchors:
        for anchor in IDENTITY_ANCHORS:
            samples.append({
                **anchor,
                "_source": "identity_anchor_v1",
                "_score": 5.0,  # max score for anchors
            })
            summary["identity_anchors"] += 1

    # Write JSONL
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for s in samples:
            # Strip internal fields for actual training (keep for traceability if --debug)
            clean = {k: v for k, v in s.items() if not k.startswith("_")}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")

    summary["total"] = len(samples)
    summary["output"] = str(out.resolve())
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/app/workspace/dataset_v1.jsonl")
    parser.add_argument("--target-size", type=int, default=700)
    parser.add_argument("--all-pairs", action="store_true", help="Include used pairs")
    parser.add_argument("--no-anchors", action="store_true", help="Skip identity anchors")
    args = parser.parse_args()

    summary = asyncio.run(export(
        output_path=args.output,
        target_size=args.target_size,
        include_unused_only=not args.all_pairs,
        add_identity_anchors=not args.no_anchors,
    ))

    print("=" * 60)
    print("DATASET EXPORT SUMMARY (Day 32)")
    print("=" * 60)
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("=" * 60)
    print(f"Ready for upload: {summary['output']}")
    print("Next: runpodctl send <output> <pod-id>:/workspace/")


if __name__ == "__main__":
    main()
