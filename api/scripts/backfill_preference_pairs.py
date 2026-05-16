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
    init_engine()
    async with get_admin_db() as db:
        stmt = select(FeedbackEvent).where(FeedbackEvent.preference_pair_id.is_(None))
        result = await db.execute(stmt)
        events = result.scalars().all()
        print(f"Found {len(events)} feedback events to backfill")

        created = 0
        skipped = 0
        for event in events:
            # Fetch message
            msg = await db.get(ConversationMessage, event.message_id)
            if not msg:
                print(f"  SKIP {event.id}: message not found")
                skipped += 1
                continue

            # Fetch conversation for tenant_id
            conv = await db.get(Conversation, msg.conversation_id)
            tenant_id = conv.tenant_id if conv else None

            # Find preceding user message as prompt_text
            prompt_text = ""
            stmt = (
                select(ConversationMessage)
                .where(
                    ConversationMessage.conversation_id == msg.conversation_id,
                    ConversationMessage.created_at < msg.created_at,
                    ConversationMessage.role == "user",
                )
                .order_by(ConversationMessage.created_at.desc())
                .limit(1)
            )
            prev = await db.execute(stmt)
            prev_msg = prev.scalar_one_or_none()
            if prev_msg:
                prompt_text = prev_msg.content or ""

            target_text = msg.content or ""

            result = await record_feedback(
                db,
                message_id=event.message_id,
                tenant_id=tenant_id,
                signal_type=event.signal_type,
                rating="thumbs_up" if event.signal_type == "thumb_up" else "thumbs_down",
                comment=event.comment or "",
                prompt_text=prompt_text,
                target_text=target_text,
            )
            pair_id = result["pair_id"]
            event.preference_pair_id = pair_id
            await db.commit()
            created += 1
            print(f"  PAIR {pair_id} for feedback {event.id}")

        print(f"\nDone: {created} created, {skipped} skipped")

if __name__ == "__main__":
    asyncio.run(backfill())
