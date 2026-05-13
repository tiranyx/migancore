#!/usr/bin/env python3
"""
Import harvested real conversation pairs into preference_pairs DB.
=========================================================
Reads harvest_real_conversations.jsonl from VPS workspace and inserts
each pair into the preference_pairs table with source_method='real_conversation'.

This makes real data available to:
  - auto_train_watchdog (triggers when real_pairs >= 80)
  - export_cycle8_dataset.py (30% real / 70% synthetic mix)
  - Admin dashboard (shows real_conversation in "Pairs by Source" chart)

Usage (inside Docker on VPS):
  docker compose exec -T api python /app/workspace/import_real_pairs.py
  docker compose exec -T api python /app/workspace/import_real_pairs.py --dry-run
  docker compose exec -T api python /app/workspace/import_real_pairs.py --path /app/workspace/harvest_real_conversations.jsonl

Author: MiganCore Day 73 — autonomous growth sprint
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

import structlog

logger = structlog.get_logger()

DEFAULT_JSONL = "/app/workspace/harvest_real_conversations.jsonl"
SOURCE_METHOD = "real_conversation"
DEFAULT_JUDGE_SCORE = 0.65  # conservative score for real pairs (not teacher-judged)


async def import_pairs(jsonl_path: str, dry_run: bool, skip_existing: bool) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    import os

    dsn = os.environ.get("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
    if not dsn:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    path = Path(jsonl_path)
    if not path.exists():
        print(f"ERROR: file not found: {path}")
        sys.exit(1)

    pairs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if d.get("prompt") and d.get("chosen"):
                    pairs.append(d)
            except json.JSONDecodeError:
                continue

    print(f"Loaded {len(pairs)} pairs from {path}")
    if not pairs:
        print("Nothing to import.")
        return

    if dry_run:
        print(f"[DRY RUN] Would insert {len(pairs)} pairs with source_method='{SOURCE_METHOD}'")
        print(f"Sample: {pairs[0]['prompt'][:80]}...")
        return

    engine = create_async_engine(dsn, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    inserted = 0
    skipped = 0

    async with SessionLocal() as db:
        for pair in pairs:
            prompt  = pair["prompt"].strip()
            chosen  = pair["chosen"].strip()
            rejected = (pair.get("rejected") or "").strip()
            conv_id = pair.get("conv_id")

            if skip_existing:
                # Check if a pair with same prompt+source already exists
                exists = (await db.execute(
                    text("""
                        SELECT 1 FROM preference_pairs
                        WHERE source_method = :src
                          AND LEFT(prompt, 120) = LEFT(:prompt, 120)
                        LIMIT 1
                    """),
                    {"src": SOURCE_METHOD, "prompt": prompt},
                )).fetchone()
                if exists:
                    skipped += 1
                    continue

            pair_id = str(uuid.uuid4())
            msg_id  = None
            if conv_id:
                try:
                    msg_id = str(uuid.UUID(conv_id))
                except ValueError:
                    msg_id = None

            await db.execute(
                text("""
                    INSERT INTO preference_pairs
                        (id, prompt, chosen, rejected, judge_score, judge_model,
                         source_method, created_at)
                    VALUES (:id, :prompt, :chosen, :rejected, :score, :model, :src, NOW())
                """),
                {
                    "id":       pair_id,
                    "prompt":   prompt,
                    "chosen":   chosen,
                    "rejected": rejected,
                    "score":    DEFAULT_JUDGE_SCORE,
                    "model":    "human_conversation",
                    "src":      SOURCE_METHOD,
                },
            )
            inserted += 1

        await db.commit()

    print(f"\n✅ Import complete")
    print(f"   Inserted: {inserted}")
    print(f"   Skipped (duplicate): {skipped}")
    print(f"\nNext steps:")
    print(f"  1. Check dashboard: pairs 'real_conversation' should now appear")
    print(f"  2. Auto-train watchdog will trigger when ≥ 80 real pairs exist")
    print(f"  3. Or manually: python training/cycle8_orpo_vast.py")


def main():
    parser = argparse.ArgumentParser(description="Import real conversation pairs into DB")
    parser.add_argument("--path", default=DEFAULT_JSONL, help="Path to harvest JSONL file")
    parser.add_argument("--dry-run", action="store_true", help="Simulate only, don't insert")
    parser.add_argument("--no-skip", action="store_true", help="Don't skip duplicates")
    args = parser.parse_args()

    asyncio.run(import_pairs(
        jsonl_path=args.path,
        dry_run=args.dry_run,
        skip_existing=not args.no_skip,
    ))


if __name__ == "__main__":
    main()
