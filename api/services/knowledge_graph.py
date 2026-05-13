"""Knowledge Graph writer for extracted memory facts.

M1.5 bridge: facts already extracted for the Letta knowledge block are also
persisted into the legacy `kg_entities` / `kg_relations` tables so the graph is
no longer empty.
"""
from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy import text

logger = structlog.get_logger()


def _normalise_fact(line: str) -> str | None:
    fact = line.strip()
    if fact.startswith("- "):
        fact = fact[2:].strip()
    fact = " ".join(fact.split())
    if len(fact) < 8:
        return None
    return fact[:255]


async def _get_or_create_entity(session, name: str, entity_type: str, description: str | None = None):
    row = await session.execute(
        text(
            """
            SELECT id FROM kg_entities
            WHERE lower(name) = lower(:name)
              AND coalesce(entity_type, '') = :entity_type
            LIMIT 1
            """
        ),
        {"name": name, "entity_type": entity_type},
    )
    existing = row.scalar_one_or_none()
    if existing:
        return existing

    inserted = await session.execute(
        text(
            """
            INSERT INTO kg_entities (name, entity_type, description)
            VALUES (:name, :entity_type, :description)
            RETURNING id
            """
        ),
        {"name": name, "entity_type": entity_type, "description": description},
    )
    return inserted.scalar_one()


async def write_memory_facts_to_kg(
    letta_agent_id: str,
    facts_text: str,
    source: str = "fact_extractor",
) -> dict:
    """Persist extracted bullet facts into the knowledge graph.

    Returns a small report and never raises. The KG is auxiliary memory; chat
    must continue even if the graph write fails.
    """
    facts = []
    for line in facts_text.splitlines():
        fact = _normalise_fact(line)
        if fact:
            facts.append(fact)
    if not facts:
        return {"status": "skipped", "facts": 0}

    try:
        from models.base import AsyncSessionLocal

        if AsyncSessionLocal is None:
            return {"status": "skipped_db_not_ready", "facts": len(facts)}

        async with AsyncSessionLocal() as session:
            agent_entity_id = await _get_or_create_entity(
                session,
                name=f"agent:{letta_agent_id}",
                entity_type="agent",
                description="Letta agent memory owner",
            )

            inserted_relations = 0
            now = datetime.now(timezone.utc).isoformat()
            for fact in facts:
                fact_entity_id = await _get_or_create_entity(
                    session,
                    name=fact,
                    entity_type="memory_fact",
                    description=f"Extracted from conversation memory by {source} at {now}",
                )
                await session.execute(
                    text(
                        """
                        INSERT INTO kg_relations
                            (head_id, tail_id, relation, evidence, confidence)
                        VALUES
                            (:head_id, :tail_id, 'has_memory_fact', :evidence, 0.75)
                        """
                    ),
                    {
                        "head_id": agent_entity_id,
                        "tail_id": fact_entity_id,
                        "evidence": fact,
                    },
                )
                inserted_relations += 1

            await session.commit()

        logger.info(
            "knowledge_graph.memory_facts_written",
            letta_id=letta_agent_id,
            facts=len(facts),
            relations=inserted_relations,
        )
        return {"status": "written", "facts": len(facts), "relations": inserted_relations}

    except Exception as exc:
        logger.warning("knowledge_graph.write_failed", error=str(exc), letta_id=letta_agent_id)
        return {"status": "error", "error": str(exc), "facts": len(facts)}
