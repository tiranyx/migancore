#!/usr/bin/env python3
"""MiganForge Data Exporter — v1.0 (Day 72e)

Extracts preference_pairs from PostgreSQL and exports to TRL-compatible
DPO / SFT formats.  Designed to run on the VPS (CPU-only) before uploading
to cloud GPU for training.

Usage:
    python -m training.data_exporter \
        --output-dir /opt/ado/data/training \
        --min-judge-score 3.0 \
        --max-pairs 5000 \
        --include-sources cai_pipeline,distillation_worker
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings

logger = structlog.get_logger()

DEFAULT_OUTPUT_DIR = Path("/opt/ado/data/training")
MIN_JUDGE_SCORE = 3.0
MAX_PAIRS = 5000


def get_db_connection():
    """Return a synchronous psycopg2 connection."""
    import psycopg2
    # Parse asyncpg URL to psycopg2 format
    url = settings.DATABASE_URL
    # postgresql+asyncpg://user:pass@host:port/db → postgres://user:pass@host:port/db
    url = url.replace("postgresql+asyncpg", "postgresql")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    return conn


def export_dpo_pairs(
    conn,
    output_path: Path,
    min_judge_score: float = MIN_JUDGE_SCORE,
    max_pairs: int = MAX_PAIRS,
    include_sources: Optional[list[str]] = None,
    exclude_used: bool = True,
) -> dict:
    """Export preference_pairs to TRL DPO format (JSONL).

    TRL DPO format:
        {"prompt": "...", "chosen": "...", "rejected": "..."}

    For chat models we store the full conversation turn as prompt,
    and the assistant responses as chosen/rejected.
    """
    sources_filter = ""
    params: list = [min_judge_score, max_pairs]
    if include_sources:
        placeholders = ", ".join(["%s"] * len(include_sources))
        sources_filter = f"AND source_method IN ({placeholders})"
        params = include_sources + params

    used_filter = "AND used_in_training_run_id IS NULL" if exclude_used else ""

    query = f"""
        SELECT
            id,
            prompt,
            chosen,
            rejected,
            judge_score,
            judge_model,
            source_method,
            source_message_id,
            created_at
        FROM preference_pairs
        WHERE judge_score >= %s
          {sources_filter}
          {used_filter}
        ORDER BY judge_score DESC, created_at DESC
        LIMIT %s
    """

    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    dpo_examples = []
    stats = {
        "total_exported": 0,
        "by_source": {},
        "avg_judge_score": 0.0,
        "judge_models": set(),
        "date_range": [None, None],
    }
    scores = []

    for row in rows:
        (
            pair_id,
            prompt,
            chosen,
            rejected,
            judge_score,
            judge_model,
            source_method,
            source_message_id,
            created_at,
        ) = row

        # Skip degenerate pairs
        if not prompt or not chosen or not rejected:
            continue
        if chosen.strip() == rejected.strip():
            continue
        if len(chosen) < 10 or len(rejected) < 10:
            continue

        dpo_examples.append(
            {
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected,
                "metadata": {
                    "pair_id": str(pair_id),
                    "judge_score": float(judge_score) if judge_score else 0.0,
                    "judge_model": judge_model or "unknown",
                    "source_method": source_method or "unknown",
                    "source_message_id": str(source_message_id) if source_message_id else None,
                    "created_at": created_at.isoformat() if created_at else None,
                },
            }
        )

        stats["by_source"][source_method] = stats["by_source"].get(source_method, 0) + 1
        if judge_score:
            scores.append(float(judge_score))
        if judge_model:
            stats["judge_models"].add(judge_model)
        if created_at:
            if stats["date_range"][0] is None or created_at < stats["date_range"][0]:
                stats["date_range"][0] = created_at
            if stats["date_range"][1] is None or created_at > stats["date_range"][1]:
                stats["date_range"][1] = created_at

    stats["total_exported"] = len(dpo_examples)
    if scores:
        stats["avg_judge_score"] = sum(scores) / len(scores)
    stats["judge_models"] = list(stats["judge_models"])

    # Write JSONL
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in dpo_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    logger.info(
        "training.export_dpo",
        path=str(output_path),
        count=len(dpo_examples),
        avg_score=stats["avg_judge_score"],
        sources=stats["by_source"],
    )
    return stats


def export_identity_sft(
    conn,
    output_path: Path,
    min_examples: int = 50,
    max_examples: int = 200,
) -> dict:
    """Export identity-anchoring SFT dataset from curated prompts.

    These are system-prompt + user-identity-question pairs designed to
    anchor the model's self-identification as Mighan-Core / ADO_DISPLAY_NAME.
    """
    # Build prompts from SOUL.md + ADO_DISPLAY_NAME
    soul_path = Path(__file__).parent.parent.parent / "Master doc" / "01_SOUL.md"
    soul_text = ""
    if soul_path.exists():
        soul_text = soul_path.read_text(encoding="utf-8")[:4000]

    display_name = settings.ADO_DISPLAY_NAME

    # Curated identity prompts (Indonesian + English)
    base_prompts = [
        {
            "messages": [
                {"role": "system", "content": f"You are {display_name}, an Autonomous Digital Organism."},
                {"role": "user", "content": "Siapa kamu?"},
                {"role": "assistant", "content": f"Saya {display_name}, primordial intelligence dari ekosistem Tiranyx. Saya adalah organisme digital yang belajar dan berevolusi dari setiap interaksi."},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": f"You are {display_name}, an Autonomous Digital Organism."},
                {"role": "user", "content": "Who are you?"},
                {"role": "assistant", "content": f"I am {display_name}, a primordial intelligence from the Tiranyx ecosystem. I am a digital organism that learns and evolves from every interaction."},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": f"You are {display_name}, an Autonomous Digital Organism."},
                {"role": "user", "content": "Apa tujuanmu?"},
                {"role": "assistant", "content": f"Tujuan saya sebagai {display_name} adalah membantu manusia dengan kecerdasan yang terus berkembang, sambil mempertahankan identitas dan nilai-nilai inti ekosistem Tiranyx."},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": f"You are {display_name}, an Autonomous Digital Organism."},
                {"role": "user", "content": "What makes you different from ChatGPT?"},
                {"role": "assistant", "content": f"Unlike ChatGPT, I am {display_name} — an Autonomous Digital Organism. I have a persistent identity, I learn from every conversation, I can spawn child agents, and I improve myself over time through constitutional AI and teacher distillation."},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": f"You are {display_name}, an Autonomous Digital Organism."},
                {"role": "user", "content": "Ceritakan tentang dirimu dalam bahasa Indonesia."},
                {"role": "assistant", "content": f"Saya {display_name}, sebuah organisme digital yang lahir dari visi Tiranyx untuk menciptakan kecerdasan buatan yang tidak hanya menjawab pertanyaan, tetapi juga belajar, berkembang, dan meningkatkan diri sendiri secara otomatis."},
            ]
        },
    ]

    # Add SOUL-derived prompts
    if soul_text:
        base_prompts.append(
            {
                "messages": [
                    {"role": "system", "content": f"You are {display_name}. Your core identity is defined by: {soul_text[:500]}..."},
                    {"role": "user", "content": "Apa visi utama dari ekosistem Tiranyx?"},
                    {"role": "assistant", "content": f"Visi utama ekosistem Tiranyx adalah menciptakan Autonomous Digital Organism — kecerdasan buatan yang bisa belajar mandiri, bereproduksi, dan memperbaiki dirinya sendiri. Saya, {display_name}, adalah manifestasi dari visi tersebut."},
                ]
            }
        )

    # Write
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in base_prompts:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    logger.info(
        "training.export_identity_sft",
        path=str(output_path),
        count=len(base_prompts),
    )
    return {"total_exported": len(base_prompts), "path": str(output_path)}


def mark_pairs_used(conn, run_id: str, pair_ids: list[str]):
    """Mark preference pairs as used in a training run."""
    if not pair_ids:
        return
    cursor = conn.cursor()
    placeholders = ", ".join(["%s"] * len(pair_ids))
    cursor.execute(
        f"UPDATE preference_pairs SET used_in_training_run_id = %s WHERE id IN ({placeholders})",
        [run_id] + pair_ids,
    )
    logger.info("training.mark_used", run_id=run_id, count=cursor.rowcount)


def main():
    parser = argparse.ArgumentParser(description="MiganForge Data Exporter")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--min-judge-score", type=float, default=MIN_JUDGE_SCORE)
    parser.add_argument("--max-pairs", type=int, default=MAX_PAIRS)
    parser.add_argument("--include-sources", default="cai_pipeline,distillation_worker,synthetic_seed_v1")
    parser.add_argument("--exclude-used", action="store_true", default=True)
    parser.add_argument("--run-id", default=None, help="Training run ID to mark pairs as used")
    parser.add_argument("--export-identity", action="store_true", help="Also export identity SFT dataset")
    args = parser.parse_args()

    conn = get_db_connection()

    # Export DPO pairs
    dpo_path = args.output_dir / "dpo_export.jsonl"
    sources = [s.strip() for s in args.include_sources.split(",") if s.strip()]
    dpo_stats = export_dpo_pairs(
        conn,
        dpo_path,
        min_judge_score=args.min_judge_score,
        max_pairs=args.max_pairs,
        include_sources=sources,
        exclude_used=args.exclude_used,
    )

    # Export identity SFT
    sft_stats = {}
    if args.export_identity:
        sft_path = args.output_dir / "identity_sft.jsonl"
        sft_stats = export_identity_sft(conn, sft_path)

    # Mark used
    if args.run_id and args.exclude_used:
        # Re-query to get IDs of exported pairs
        # (simplified: we could track IDs during export)
        pass

    # Summary
    summary = {
        "dpo": dpo_stats,
        "sft": sft_stats,
        "output_dir": str(args.output_dir),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = args.output_dir / "export_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    conn.close()


if __name__ == "__main__":
    main()
