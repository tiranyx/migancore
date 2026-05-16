"""
Backfill PreferencePair for existing FeedbackEvent without pair_id.
Run inside container: docker compose exec api python3 scripts/backfill_preference_pairs.py
"""
import asyncio, uuid, sys, os
sys.path.insert(0, "/app")

from models.base import init_engine
from deps.db import get_admin_db
from models.feedback import FeedbackEvent
from models.preference_pair import PreferencePair
from models.conversation import Conversation, ConversationMessage
from services.feedback import record_feedback
from sqlalchemy import select, func

async def backfill():
    # Use superuser connection to bypass RLS for cross-tenant backfill
    import asyncpg
    from config import settings
    dsn = settings.DATABASE_URL.replace("+asyncpg", "", 1).replace("ado_app", "ado", 1)
    conn = await asyncpg.connect(dsn)
    
    rows = await conn.fetch("""
        SELECT f.id as feedback_id, f.message_id, f.signal_type, f.comment,
               m.conversation_id, m.content as target_text, m.created_at as msg_at,
               c.tenant_id
        FROM interactions_feedback f
        LEFT JOIN messages m ON m.id = f.message_id
        LEFT JOIN conversations c ON c.id = m.conversation_id
        WHERE f.preference_pair_id IS NULL
    """)
    print(f"Found {len(rows)} feedback events to backfill")

    created = 0
    skipped = 0
    for row in rows:
        # Find preceding user message
        prev = await conn.fetchrow("""
            SELECT content FROM messages
            WHERE conversation_id = $1 AND created_at < $2 AND role = 'user'
            ORDER BY created_at DESC LIMIT 1
        """, row["conversation_id"], row["msg_at"])
        prompt_text = prev["content"] if prev else ""
        target_text = row["target_text"] or ""
        tenant_id = row["tenant_id"]

        # Insert PreferencePair
        if row["signal_type"] == "thumb_up":
            chosen = target_text
            rejected = "__AWAITING_REJECTED__"
        else:
            chosen = "__AWAITING_CHOSEN__"
            rejected = target_text

        pair_id = await conn.fetchval("""
            INSERT INTO preference_pairs (id, prompt, chosen, rejected, judge_score, source_method, source_message_id, processing_attempts, created_at)
            VALUES ($1, $2, $3, $4, 0.5, 'real_conversation', $5, 0, NOW())
            RETURNING id
        """, uuid.uuid4(), prompt_text, chosen, rejected, row["message_id"])

        # Update feedback
        await conn.execute("""
            UPDATE interactions_feedback SET preference_pair_id = $1 WHERE id = $2
        """, pair_id, row["feedback_id"])

        created += 1
        print(f"  PAIR {pair_id} for feedback {row['feedback_id']}")

    await conn.close()
    print(f"\nDone: {created} created, {skipped} skipped")

if __name__ == "__main__":
    asyncio.run(backfill())
