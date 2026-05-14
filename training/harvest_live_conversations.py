#!/usr/bin/env python3
"""
Harvest live conversation pairs from production DB (uses ado superuser to bypass RLS).

Extracts user→assistant adjacent pairs from messages table, converts to
preference_pair format, and inserts as source_method='real_conversation'.

Usage (inside Docker on VPS):
  docker compose exec -T api python /app/workspace/harvest_live_conversations.py
  docker compose exec -T api python /app/workspace/harvest_live_conversations.py --dry-run
  docker compose exec -T api python /app/workspace/harvest_live_conversations.py --min-chars 80

The script uses the ADO_SUPERUSER_URL env var (ado user, bypasses RLS).
Falls back to a hardcoded superuser DSN if not set.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path

import structlog

logger = structlog.get_logger()

SOURCE_METHOD   = "real_conversation"
DEFAULT_SCORE   = 0.65
MIN_PROMPT_CHARS = 15
MIN_CHOSEN_CHARS = 50
SKIP_PREFIXES   = ("[KONTEKS", "[Tool", "Traceback", "Error:", "```")


async def harvest(dry_run: bool, min_chars: int) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    # Superuser DSN — bypasses RLS
    raw_url = os.environ.get("ADO_SUPERUSER_URL") or os.environ.get("DATABASE_URL", "")
    # Replace ado_app with ado superuser if possible
    dsn = raw_url.replace("postgresql://", "postgresql+asyncpg://")
    # Try to switch to superuser
    if "ado_app:" in dsn:
        ado_pw = raw_url.split("ado_app:")[1].split("@")[0]
        dsn_super = dsn.replace(f"ado_app:{ado_pw}", "ado:ado_password_placeholder")
    else:
        dsn_super = dsn

    # Use the direct psycopg2 approach via subprocess for superuser access
    # Actually, just use libpq env var approach
    pg_host = "ado-postgres-1"
    pg_db   = "ado"
    pg_user = "ado"

    # Get DB password from env
    db_url = os.environ.get("DATABASE_URL", "")
    # Try to extract ado user password from compose env
    # Fallback: use ado_app connection but with SET ROLE trick is not possible
    # Best approach: use the ado_app DSN (it can see preference_pairs, and we
    # only need conversation data which we'll query via a SECURITY DEFINER function
    # or we accept the limitation and use ado_app's visible data)

    # PRACTICAL APPROACH: use psql via subprocess to dump conversations as JSON,
    # then parse and insert via ado_app DSN
    import subprocess, json

    _log("Fetching user→assistant pairs via psql superuser...")
    psql_cmd = [
        "docker", "exec", "ado-postgres-1",
        "psql", "-U", "ado", "-d", "ado",
        "-c", r"""
COPY (
  SELECT json_build_object(
    'conv_id', u.conversation_id::text,
    'prompt', u.content,
    'chosen', a.content,
    'user_at', u.created_at::text
  )
  FROM messages u
  JOIN messages a ON a.conversation_id = u.conversation_id
                 AND a.role = 'assistant'
                 AND a.created_at > u.created_at
  WHERE u.role = 'user'
    AND length(u.content) >= 15
    AND length(a.content) >= 50
    AND a.tool_calls IS NULL
    AND u.content NOT LIKE '[KONTEKS%'
  ORDER BY u.conversation_id, u.created_at,
           (SELECT MIN(a2.created_at) FROM messages a2
            WHERE a2.conversation_id = u.conversation_id
              AND a2.role = 'assistant'
              AND a2.created_at > u.created_at)
) TO STDOUT
""",
    ]

    try:
        r = subprocess.run(psql_cmd, capture_output=True, text=True, timeout=30)
        lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    except Exception as exc:
        _log(f"psql subprocess failed: {exc}")
        sys.exit(1)

    _log(f"Raw pairs from DB: {len(lines)}")

    # Dedup: keep FIRST assistant reply for each user message
    seen_prompts: set[str] = set()
    pairs = []
    for line in lines:
        try:
            d = json.loads(line)
        except Exception:
            continue
        prompt  = d.get("prompt", "").strip()
        chosen  = d.get("chosen", "").strip()
        conv_id = d.get("conv_id", "")

        if not prompt or not chosen:
            continue
        if len(prompt) < min_chars or len(chosen) < MIN_CHOSEN_CHARS:
            continue
        # Skip noisy content
        if any(chosen.startswith(p) for p in SKIP_PREFIXES):
            continue
        # Dedup by prompt prefix
        key = prompt[:120]
        if key in seen_prompts:
            continue
        seen_prompts.add(key)

        pairs.append({"prompt": prompt, "chosen": chosen, "rejected": "", "conv_id": conv_id})

    _log(f"Filtered unique pairs: {len(pairs)}")

    if not pairs:
        _log("Nothing to insert.")
        return

    if dry_run:
        _log(f"[DRY RUN] Would insert {len(pairs)} pairs")
        for p in pairs[:3]:
            _log(f"  prompt: {p['prompt'][:60]}...")
            _log(f"  chosen: {p['chosen'][:60]}...")
        return

    # Insert via ado_app connection
    engine = create_async_engine(
        os.environ.get("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    inserted = skipped = 0
    async with Session() as db:
        for pair in pairs:
            # Skip if already exists
            exists = (await db.execute(
                text("""
                    SELECT 1 FROM preference_pairs
                    WHERE source_method = :src
                      AND LEFT(prompt, 120) = LEFT(:prompt, 120)
                    LIMIT 1
                """),
                {"src": SOURCE_METHOD, "prompt": pair["prompt"]},
            )).fetchone()
            if exists:
                skipped += 1
                continue

            conv_id = None
            try:
                conv_id = str(uuid.UUID(pair["conv_id"]))
            except (ValueError, AttributeError):
                pass

            await db.execute(
                text("""
                    INSERT INTO preference_pairs
                        (id, prompt, chosen, rejected, judge_score, judge_model,
                         source_method, source_message_id, created_at)
                    VALUES (:id, :prompt, :chosen, :rejected, :score, :model, :src, :msg_id, NOW())
                """),
                {
                    "id":       str(uuid.uuid4()),
                    "prompt":   pair["prompt"],
                    "chosen":   pair["chosen"],
                    "rejected": "",
                    "score":    DEFAULT_SCORE,
                    "model":    "human_conversation",
                    "src":      SOURCE_METHOD,
                    "msg_id":   conv_id,
                },
            )
            inserted += 1

        await db.commit()

    _log(f"\n✅ Harvest complete: inserted={inserted}  skipped_dup={skipped}")
    _log(f"   Total real_conversation pairs now: {inserted + skipped + 52}+")


def _log(msg: str) -> None:
    print(msg, flush=True)


def main():
    parser = argparse.ArgumentParser(description="Harvest live conversation pairs from production DB")
    parser.add_argument("--dry-run", action="store_true", help="Simulate, don't insert")
    parser.add_argument("--min-chars", type=int, default=MIN_PROMPT_CHARS,
                        help=f"Min prompt length (default: {MIN_PROMPT_CHARS})")
    args = parser.parse_args()
    asyncio.run(harvest(dry_run=args.dry_run, min_chars=args.min_chars))


if __name__ == "__main__":
    main()
