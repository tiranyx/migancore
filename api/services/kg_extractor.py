"""
Knowledge Graph Extractor — MiganCore Self-Learning
====================================================
Extracts entities and relationships from every assistant response.
Fired as fire-and-forget after streaming completes.

Tables: chat_entities + chat_relations (migration 028)
These are separate from kg_entities/kg_relations which are for research papers.

Flow:
  chat.py streaming done → asyncio.create_task(extract_and_store(...))
                                   ↓
                           Ollama extraction (local, zero API cost)
                                   ↓
                  chat_entities + chat_relations UPSERT
                                   ↓
              recall_for_prompt() → injected into system prompt

Author: MiganCore Day 73 — autonomous growth sprint
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone

import httpx
import structlog

logger = structlog.get_logger()

_EXTRACT_PROMPT = """\
Ekstrak entitas dan fakta penting dari teks ini. Kembalikan HANYA JSON valid, tidak ada teks lain.

Format output:
{{"entities": [{{"name": "...", "type": "PERSON|ORG|PLACE|CONCEPT|PRODUCT|SKILL"}}], "relations": [{{"subject": "...", "predicate": "...", "object": "..."}}]}}

Aturan:
- Entitas: nama spesifik (orang, perusahaan, tempat, produk, konsep teknis)
- Relasi: fakta konkret, bukan generik
- Maksimal 5 entitas dan 4 relasi
- Jika tidak ada yang spesifik: {{"entities": [], "relations": []}}

TEKS:
{text}
"""

_MIN_TEXT_LEN = 100
_MAX_TEXT_LEN = 1800


async def _call_ollama_extract(text: str, ollama_url: str, model: str) -> dict | None:
    prompt = _EXTRACT_PROMPT.format(text=text[:_MAX_TEXT_LEN])
    try:
        async with httpx.AsyncClient(timeout=18) as client:
            resp = await client.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0, "num_predict": 256}},
            )
            if resp.status_code != 200:
                return None
            raw = resp.json().get("response", "")
            m = re.search(r"\{[\s\S]*\}", raw)
            if not m:
                return None
            return json.loads(m.group(0))
    except Exception as exc:
        logger.debug("kg.ollama_failed", error=str(exc)[:80])
        return None


async def extract_and_store(
    *,
    tenant_id: str,
    conversation_id: str,
    assistant_text: str,
    user_text: str = "",
    ollama_url: str,
    model: str,
) -> None:
    """Extract KG facts and store. Fire-and-forget safe."""
    combined = f"{user_text}\n\n{assistant_text}".strip() if user_text else assistant_text
    if len(combined) < _MIN_TEXT_LEN:
        return

    extracted = await _call_ollama_extract(combined, ollama_url, model)
    if not extracted:
        return

    entities = extracted.get("entities") or []
    relations = extracted.get("relations") or []
    if not entities and not relations:
        return

    try:
        from sqlalchemy import text
        from deps.db import tenant_session

        async with tenant_session(tenant_id) as db:
            now = datetime.now(timezone.utc)
            stored_entities: dict[str, None] = {}

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
                stored_entities[name] = None

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
                    {"tid": tenant_id, "s": s, "p": p, "o": o, "cid": conversation_id, "now": now},
                )

            await db.commit()
            logger.info("kg.stored", tenant=tenant_id[:8], entities=len(stored_entities), relations=len(relations))
    except Exception as exc:
        logger.warning("kg.store_failed", error=str(exc)[:120])


async def recall_for_prompt(*, tenant_id: str, user_text: str, max_facts: int = 6) -> str:
    """Recall relevant KG facts for the current user message.

    Returns a compact string for system prompt injection, or "" if nothing.
    """
    if not user_text or len(user_text) < 8:
        return ""
    try:
        from sqlalchemy import text
        from deps.db import tenant_session

        async with tenant_session(tenant_id) as db:
            # Top entities by mention count
            rows = (await db.execute(
                text("""
                    SELECT name, entity_type, mention_count
                    FROM chat_entities
                    WHERE tenant_id = :tid
                    ORDER BY mention_count DESC, last_seen_at DESC
                    LIMIT 40
                """),
                {"tid": tenant_id},
            )).fetchall()

        if not rows:
            return ""

        user_lower = user_text.lower()
        matched_names = [r[0] for r in rows if r[0].lower() in user_lower]
        if not matched_names:
            matched_names = [r[0] for r in rows[:4]]

        if not matched_names:
            return ""

        async with tenant_session(tenant_id) as db:
            rels = (await db.execute(
                text("""
                    SELECT DISTINCT subject, predicate, object
                    FROM chat_relations
                    WHERE tenant_id = :tid
                      AND (subject = ANY(:names) OR object = ANY(:names))
                    ORDER BY created_at DESC
                    LIMIT :max
                """),
                {"tid": tenant_id, "names": matched_names, "max": max_facts},
            )).fetchall()

        if not rels:
            return ""

        lines = ["[Konteks yang diketahui]"]
        for s, p, o in rels:
            lines.append(f"- {s} {p} {o}.")
        return "\n".join(lines) + "\n"
    except Exception:
        return ""
