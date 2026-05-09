#!/usr/bin/env python3
"""
Diagnostic script for DB ingestion — Day 71.

Run inside the API container:
    docker compose exec api python -m scripts.diagnose_db_ingestion

Checks:
    1. Can connect to PostgreSQL?
    2. How many messages total / last 24h / last 6h?
    3. How many assistant messages with preceding user?
    4. Are there assistant messages with NULL or short content?
    5. Timezone check — what does NOW() return in the DB?
    6. Sample of recent messages (roles, lengths, timestamps)

Author: MiganCore ADO — Day 71
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings


async def main():
    import asyncpg

    dsn = settings.DATABASE_URL.replace("+asyncpg", "", 1)
    print("=" * 60)
    print("MIGANCORE DB INGESTION DIAGNOSTIC — Day 71")
    print("=" * 60)
    print(f"DSN (redacted): {dsn.split('@')[1] if '@' in dsn else dsn}")
    print(f"Python time (UTC): {datetime.now(timezone.utc).isoformat()}")

    try:
        conn = await asyncpg.connect(dsn)
    except Exception as exc:
        print(f"\n[FAIL] Cannot connect to PostgreSQL: {exc}")
        return 1

    print("\n[OK] Connected to PostgreSQL")

    # 1. Server time
    db_now = await conn.fetchval("SELECT NOW()")
    db_now_utc = await conn.fetchval("SELECT NOW() AT TIME ZONE 'UTC'")
    print(f"\n[TIME] DB NOW():          {db_now}")
    print(f"[TIME] DB NOW() UTC:      {db_now_utc}")
    print(f"[TIME] Python UTC:        {datetime.now(timezone.utc)}")

    # 2. Table counts
    counts = await conn.fetch(
        """
        SELECT
            (SELECT COUNT(*) FROM messages) AS total_messages,
            (SELECT COUNT(*) FROM conversations) AS total_conversations,
            (SELECT COUNT(*) FROM messages WHERE role = 'assistant') AS total_assistant,
            (SELECT COUNT(*) FROM messages WHERE role = 'user') AS total_user,
            (SELECT COUNT(*) FROM messages WHERE role = 'system') AS total_system,
            (SELECT COUNT(*) FROM messages WHERE role = 'tool') AS total_tool
        """
    )
    c = counts[0]
    print(f"\n[COUNTS]")
    print(f"  Total messages:      {c['total_messages']}")
    print(f"  Total conversations: {c['total_conversations']}")
    print(f"  Assistant:           {c['total_assistant']}")
    print(f"  User:                {c['total_user']}")
    print(f"  System:              {c['total_system']}")
    print(f"  Tool:                {c['total_tool']}")

    # 3. Time-window counts
    for hours in [1, 6, 24, 168]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE role = 'assistant') AS assistant,
                COUNT(*) FILTER (WHERE role = 'user') AS user,
                COUNT(*) FILTER (WHERE role = 'assistant' AND LENGTH(content) > 10) AS assistant_long,
                COUNT(*) FILTER (WHERE role = 'assistant' AND LENGTH(content) <= 10) AS assistant_short,
                COUNT(*) FILTER (WHERE role = 'assistant' AND content IS NULL) AS assistant_null
            FROM messages
            WHERE created_at > $1
            """,
            cutoff,
        )
        print(f"\n[WINDOW last {hours}h]")
        print(f"  Assistant:           {row['assistant']}")
        print(f"  User:                {row['user']}")
        print(f"  Assistant len>10:    {row['assistant_long']}")
        print(f"  Assistant len<=10:   {row['assistant_short']}")
        print(f"  Assistant NULL:      {row['assistant_null']}")

    # 4. Check for user→assistant pairs (the distillation query logic)
    cutoff_6h = datetime.now(timezone.utc) - timedelta(hours=6)
    pairs = await conn.fetch(
        """
        WITH ranked AS (
            SELECT
                m.id AS assistant_msg_id,
                m.conversation_id,
                m.content AS assistant_content,
                m.created_at,
                LAG(m.role) OVER w AS prev_role,
                LAG(m.content) OVER w AS prev_content
            FROM messages m
            WHERE m.created_at > $1
            WINDOW w AS (
                PARTITION BY m.conversation_id
                ORDER BY m.created_at
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        )
        SELECT assistant_msg_id, created_at, assistant_content, prev_role, prev_content
        FROM ranked
        WHERE prev_role = 'user'
          AND assistant_content IS NOT NULL
          AND LENGTH(assistant_content) > 10
        ORDER BY created_at DESC
        LIMIT 10
        """,
        cutoff_6h,
    )
    print(f"\n[PAIRS last 6h] Found {len(pairs)} user→assistant pairs")
    for p in pairs[:5]:
        print(f"  {p['created_at']} | user: {p['prev_content'][:40]}... | assist: {p['assistant_content'][:40]}...")

    # 5. Recent messages sample (last 10)
    recent = await conn.fetch(
        """
        SELECT role, content, created_at, LENGTH(content) AS len
        FROM messages
        ORDER BY created_at DESC
        LIMIT 10
        """
    )
    print(f"\n[RECENT last 10 messages]")
    for r in recent:
        ts = r["created_at"]
        role = r["role"]
        length = r["len"]
        content_preview = (r["content"] or "")[:50].replace("\n", " ")
        print(f"  {ts} | {role:10s} | len={length:4d} | {content_preview}...")

    # 6. Check for conversations with user but NO assistant
    orphaned = await conn.fetch(
        """
        SELECT c.id, c.message_count, c.last_message_at
        FROM conversations c
        WHERE c.message_count > 0
          AND NOT EXISTS (
              SELECT 1 FROM messages m
              WHERE m.conversation_id = c.id AND m.role = 'assistant'
          )
        LIMIT 10
        """
    )
    print(f"\n[ORPHANED] Conversations with messages but NO assistant: {len(orphaned)}")
    for o in orphaned[:5]:
        print(f"  conv={o['id'][:8]}... count={o['message_count']} last_at={o['last_message_at']}")

    await conn.close()
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
