#!/usr/bin/env python3
"""
MiganCore — Harvest Real Conversations as Training Pairs
=========================================================
Extracts user↔assistant message pairs from the live conversations DB
and saves them as ORPO-ready JSONL for future training.

WHY: 156 real conversations = gold data. Real Fahmi utterances + real
MiganCore responses. Quality filter removes short/low-value exchanges.

OUTPUT FORMAT (ORPO / SFT compatible):
  {"prompt": "<user message>", "chosen": "<assistant response>",
   "rejected": "", "source": "real_conversation", "conv_id": "..."}

The "rejected" field is left empty — to be filled later by:
  (a) CAI self-critique  (b) teacher distillation  (c) manual annotation

Usage (inside Docker on VPS):
  # Copy script:
  scp training/harvest_real_conversations.py root@VPS:/opt/ado/data/workspace/

  # Dry run (count only):
  docker compose exec -T api python /app/workspace/harvest_real_conversations.py --dry-run

  # Full harvest:
  docker compose exec -T api python /app/workspace/harvest_real_conversations.py

  # With quality threshold:
  docker compose exec -T api python /app/workspace/harvest_real_conversations.py --min-chars 80

Author: Claude Sonnet 4.6, Day 72f
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import structlog

logger = structlog.get_logger()

OUT_PATH = Path("/app/workspace/harvest_real_conversations.jsonl")
DB_URL = os.environ.get("DATABASE_URL", "")

# Quality filters
DEFAULT_MIN_CHARS = 60       # min chars for user message
DEFAULT_MIN_REPLY = 80       # min chars for assistant reply
DEFAULT_MAX_PAIRS = 2000     # safety cap


async def harvest(min_chars: int, min_reply: int, max_pairs: int, dry_run: bool):
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    # Use superuser DSN to bypass RLS (read-only harvest)
    dsn = DB_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(dsn, echo=False)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    pairs: list[dict] = []
    skipped_short = 0
    skipped_tool = 0

    async with SessionLocal() as db:
        # Get all conversation IDs with at least 2 messages
        result = await db.execute(text("""
            SELECT c.id, c.message_count
            FROM conversations c
            WHERE c.message_count >= 2
            ORDER BY c.last_message_at DESC
            LIMIT 500
        """))
        conv_rows = result.fetchall()
        logger.info("harvest.conversations_found", count=len(conv_rows))

        for conv_id, msg_count in conv_rows:
            if len(pairs) >= max_pairs:
                break

            # Fetch messages ordered by time
            msgs_result = await db.execute(text("""
                SELECT role, content, tool_calls
                FROM messages
                WHERE conversation_id = :cid
                ORDER BY created_at ASC
            """), {"cid": conv_id})
            msgs = msgs_result.fetchall()

            # Slide a window: each user msg paired with following assistant msg
            for i, (role, content, tool_calls) in enumerate(msgs):
                if role != "user":
                    continue
                if i + 1 >= len(msgs):
                    continue

                next_role, next_content, _ = msgs[i + 1]
                if next_role != "assistant":
                    continue

                # Quality filters
                user_msg = (content or "").strip()
                asst_msg = (next_content or "").strip()

                if len(user_msg) < min_chars:
                    skipped_short += 1
                    continue
                if len(asst_msg) < min_reply:
                    skipped_short += 1
                    continue

                # Skip pure tool-call exchanges (no prose)
                if asst_msg.startswith("{") and '"tool_calls"' in asst_msg:
                    skipped_tool += 1
                    continue

                # Skip system/meta messages
                if user_msg.lower().startswith(("system:", "[system")):
                    skipped_short += 1
                    continue

                pairs.append({
                    "prompt": user_msg,
                    "chosen": asst_msg,
                    "rejected": "",  # filled by CAI/teacher later
                    "source": "real_conversation",
                    "conv_id": str(conv_id),
                })

                if len(pairs) >= max_pairs:
                    break

    logger.info(
        "harvest.complete",
        pairs=len(pairs),
        skipped_short=skipped_short,
        skipped_tool=skipped_tool,
    )

    if dry_run:
        print(f"\n[DRY RUN] Would harvest {len(pairs)} pairs")
        print(f"  Skipped (too short): {skipped_short}")
        print(f"  Skipped (tool-only): {skipped_tool}")
        if pairs:
            print(f"\nSample pair #1:")
            print(f"  PROMPT: {pairs[0]['prompt'][:120]}...")
            print(f"  CHOSEN: {pairs[0]['chosen'][:120]}...")
        return

    # Write JSONL
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\n✅ Harvested {len(pairs)} pairs → {OUT_PATH}")
    print(f"   Skipped (too short):  {skipped_short}")
    print(f"   Skipped (tool-only):  {skipped_tool}")
    print(f"\nNext steps:")
    print(f"  1. Review pairs: head -5 {OUT_PATH} | python3 -m json.tool")
    print(f"  2. Fill 'rejected' via CAI: generate_rejected_responses.py")
    print(f"  3. Export for training: export_cycle8_dataset.py")


def main():
    parser = argparse.ArgumentParser(description="Harvest real conversations as training pairs")
    parser.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS,
                        help=f"Min chars for user message (default: {DEFAULT_MIN_CHARS})")
    parser.add_argument("--min-reply", type=int, default=DEFAULT_MIN_REPLY,
                        help=f"Min chars for assistant reply (default: {DEFAULT_MIN_REPLY})")
    parser.add_argument("--max-pairs", type=int, default=DEFAULT_MAX_PAIRS,
                        help=f"Max pairs to harvest (default: {DEFAULT_MAX_PAIRS})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count only, don't write file")
    args = parser.parse_args()

    if not DB_URL:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    asyncio.run(harvest(
        min_chars=args.min_chars,
        min_reply=args.min_reply,
        max_pairs=args.max_pairs,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
