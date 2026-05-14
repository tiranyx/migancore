#!/usr/bin/env python3
"""
Knowledge Graph Batch Activation — MiganCore Organic Growth Sprint
Processes all existing conversations to populate chat_entities + chat_relations.
Run once to bootstrap KG from historical data.

Usage:
    python scripts/activate_kg.py --batch_size 50
"""

import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import httpx
import structlog

LOG_PATH = Path("logs/organic_sprint/activate_kg.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = structlog.get_logger()


async def _call_ollama_extract(text: str, ollama_url: str, model: str) -> dict | None:
    """Extract entities via Ollama."""
    prompt = f"""Ekstrak entitas dan fakta penting dari teks ini. Kembalikan HANYA JSON valid.
Format: {{"entities": [{{"name": "...", "type": "PERSON|ORG|PLACE|CONCEPT|PRODUCT|SKILL"}}], "relations": [{{"subject": "...", "predicate": "...", "object": "..."}}]}}
Maksimal 5 entitas dan 4 relasi. Jika tidak ada: {{"entities": [], "relations": []}}
TEKS:
{text[:1500]}
"""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0, "num_predict": 256}},
            )
            if resp.status_code != 200:
                return None
            raw = resp.json().get("response", "")
            import re
            m = re.search(r"\{{[\s\S]*\}}", raw)
            if not m:
                return None
            return json.loads(m.group(0))
    except Exception as exc:
        logger.debug("kg.extract_failed", error=str(exc)[:80])
        return None


async def process_conversation(
    conv_id: str,
    tenant_id: str,
    messages: list[dict],
    ollama_url: str,
    model: str,
) -> tuple[int, int]:
    """Process one conversation: extract KG from assistant messages."""
    from sqlalchemy import text
    from deps.db import tenant_session
    
    entities_count = 0
    relations_count = 0
    
    async with tenant_session(tenant_id) as db:
        for i, msg in enumerate(messages):
            if msg.get("role") != "assistant":
                continue
            
            content = msg.get("content", "")
            if len(content) < 100:
                continue
            
            user_text = messages[i-1].get("content", "") if i > 0 else ""
            combined = f"{user_text}\n\n{content}".strip() if user_text else content
            
            extracted = await _call_ollama_extract(combined, ollama_url, model)
            if not extracted:
                continue
            
            entities = extracted.get("entities") or []
            relations = extracted.get("relations") or []
            
            now = datetime.now().astimezone()
            
            for ent in entities[:5]:
                name = (ent.get("name") or "").strip()
                etype = (ent.get("type") or "CONCEPT").upper()[:64]
                if len(name) < 2:
                    continue
                await db.execute(
                    text("""
                        INSERT INTO chat_entities (tenant_id, name, entity_type, mention_count, first_seen_at, last_seen_at)
                        VALUES (:tid, :name, :type, 1, :now, :now)
                        ON CONFLICT (tenant_id, name, entity_type)
                        DO UPDATE SET mention_count = chat_entities.mention_count + 1,
                                      last_seen_at = EXCLUDED.last_seen_at
                    """),
                    {"tid": tenant_id, "name": name, "type": etype, "now": now},
                )
                entities_count += 1
            
            for rel in relations[:4]:
                s = (rel.get("subject") or "").strip()
                p = (rel.get("predicate") or "").strip()
                o = (rel.get("object") or "").strip()
                if not (s and p and o):
                    continue
                await db.execute(
                    text("""
                        INSERT INTO chat_relations (tenant_id, subject, predicate, object, conversation_id, created_at)
                        VALUES (:tid, :s, :p, :o, :cid, :now)
                    """),
                    {"tid": tenant_id, "s": s, "p": p, "o": o, "cid": conv_id, "now": now},
                )
                relations_count += 1
        
        await db.commit()
    
    return entities_count, relations_count


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ollama_url", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen2.5:7b-instruct-q4_K_M")
    parser.add_argument("--batch_size", type=int, default=50)
    parser.add_argument("--limit", type=int, default=0, help="0 = all")
    args = parser.parse_args()
    
    print(f"=== KG Batch Activation ===")
    print(f"Ollama: {args.ollama_url}")
    print(f"Model: {args.model}")
    print(f"Batch size: {args.batch_size}")
    
    # Initialize DB
    from models.base import init_engine
    init_engine()
    
    from sqlalchemy import text
    from deps.db import get_admin_db
    
    async with get_admin_db() as db:
        # Get conversation count
        total = await db.scalar(text("SELECT COUNT(*) FROM conversations"))
        print(f"Total conversations to process: {total}")
        
        # Get all conversations with messages
        result = await db.execute(
            text("""
                SELECT c.id, c.tenant_id, 
                       jsonb_agg(jsonb_build_object('role', m.role, 'content', m.content) ORDER BY m.created_at) as msgs
                FROM conversations c
                JOIN messages m ON m.conversation_id = c.id
                GROUP BY c.id, c.tenant_id
                ORDER BY c.id
                LIMIT :limit
            """),
            {"limit": args.limit or total},
        )
        rows = result.fetchall()
    
    total_entities = 0
    total_relations = 0
    processed = 0
    
    for row in rows:
        conv_id = str(row.id)
        tenant_id = str(row.tenant_id)
        messages = row.msgs or []
        
        try:
            e, r = await process_conversation(conv_id, tenant_id, messages, args.ollama_url, args.model)
            total_entities += e
            total_relations += r
            processed += 1
            
            if processed % 10 == 0:
                print(f"  Progress: {processed}/{len(rows)} conversations | Entities: {total_entities} | Relations: {total_relations}")
        except Exception as exc:
            print(f"  ERROR processing {conv_id}: {exc}")
    
    print(f"\n=== DONE ===")
    print(f"Conversations processed: {processed}")
    print(f"Entities extracted: {total_entities}")
    print(f"Relations extracted: {total_relations}")


if __name__ == "__main__":
    asyncio.run(main())
