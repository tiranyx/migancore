"""
Qdrant vector memory service — Tier 2 semantic memory for agents.

Architecture:
  - Per-agent collections: episodic_{agent_id}, semantic_{agent_id}
  - Turn-pair chunking: user + assistant messages embedded together
  - Brute-force search for <10k vectors (full_scan_threshold=10000)
  - Graceful degradation: returns [] on Qdrant unavailability
  - Semaphore limits concurrent background embed ops to 2

Collection lifecycle:
  - Created on first message (lazy, idempotent)
  - Never deleted automatically (agent memory persists)
"""

import asyncio
import time
import uuid

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    OptimizersConfigDiff,
    PointStruct,
    VectorParams,
)

from config import settings
from services.embedding import embed_text, format_turn_pair

logger = structlog.get_logger()

SCORE_THRESHOLD = 0.55
TOP_K_EPISODIC = 5

_qdrant: AsyncQdrantClient | None = None
_qdrant_lock = asyncio.Lock()
_embed_semaphore = asyncio.Semaphore(2)


def _col(agent_id: str, col_type: str = "episodic") -> str:
    return f"{col_type}_{agent_id}"


async def _get_client() -> AsyncQdrantClient:
    global _qdrant
    if _qdrant is None:
        async with _qdrant_lock:
            if _qdrant is None:
                kwargs: dict = {"url": settings.QDRANT_URL}
                if settings.QDRANT_API_KEY:
                    kwargs["api_key"] = settings.QDRANT_API_KEY
                _qdrant = AsyncQdrantClient(**kwargs)
    return _qdrant


async def ensure_collection(agent_id: str, col_type: str = "episodic") -> None:
    """Create Qdrant collection for an agent if it does not exist.

    Idempotent: safe to call on every request. Handles race conditions from
    multiple workers trying to create the same collection simultaneously.

    HNSW config: full_scan_threshold=10000 means Qdrant uses exact brute-force
    search for collections under 10k vectors — faster and more accurate than
    HNSW for small agent memory collections.
    """
    name = _col(agent_id, col_type)
    client = await _get_client()
    try:
        if await client.collection_exists(name):
            return
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            hnsw_config=HnswConfigDiff(
                m=16,
                ef_construct=100,
                full_scan_threshold=10000,
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=20000,
                memmap_threshold=50000,
            ),
            on_disk_payload=False,
        )
        logger.info("qdrant.collection_created", name=name)
    except Exception as exc:
        if "already exists" in str(exc).lower():
            return
        raise


async def index_turn_pair(
    agent_id: str,
    tenant_id: str,
    user_message: str,
    assistant_message: str,
    session_id: str,
    turn_index: int,
) -> None:
    """Embed and store a conversation turn pair in Qdrant.

    Called as asyncio.create_task() after message save — never blocks response.
    Semaphore limits concurrent CPU-bound embed operations to 2.
    Failures are logged and silently dropped (Tier 1 Redis remains authoritative).
    """
    async with _embed_semaphore:
        try:
            await ensure_collection(agent_id)
            chunk_text = format_turn_pair(user_message, assistant_message)
            vector = await embed_text(chunk_text)
            client = await _get_client()
            await client.upsert(
                collection_name=_col(agent_id),
                points=[
                    PointStruct(
                        id=uuid.uuid4().hex,
                        vector=vector,
                        payload={
                            "agent_id": agent_id,
                            "tenant_id": tenant_id,
                            "session_id": session_id,
                            "turn_index": turn_index,
                            "timestamp": int(time.time()),
                            "user_message": user_message,
                            "assistant_message": assistant_message,
                            "chunk_text": chunk_text,
                        },
                    )
                ],
            )
            logger.info(
                "qdrant.turn_indexed",
                agent=agent_id,
                session=session_id,
                turn=turn_index,
            )
        except Exception as exc:
            logger.warning(
                "qdrant.index_failed",
                agent=agent_id,
                error=str(exc),
            )


async def search_semantic(
    agent_id: str,
    query: str,
    top_k: int = TOP_K_EPISODIC,
    score_threshold: float = SCORE_THRESHOLD,
) -> list[dict]:
    """Search agent episodic memory by semantic similarity.

    Returns list of payloads (user_message, assistant_message, session_id,
    turn_index, timestamp, _retrieval_score). Returns [] if Qdrant is
    unavailable or collection doesn't exist yet.

    Args:
        score_threshold: Minimum cosine similarity score. Default 0.55 for
            tool_executor use. Callers like vector_retrieval use 0.65 for
            stricter filtering (research: 0.70 English → 0.65 Bahasa Indonesia
            due to 5-8% lower cross-lingual scores on multilingual MPNet).

    Results include '_retrieval_score' key so callers can sort by relevance.
    Qdrant already returns results sorted by score desc, but explicit key
    enables caller-side re-sorting if combining multiple sources.
    """
    try:
        client = await _get_client()
        col_name = _col(agent_id)
        if not await client.collection_exists(col_name):
            return []
        vector = await embed_text(query)
        results = await client.search(
            collection_name=col_name,
            query_vector=vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        # Inject retrieval score into payload — enables caller-side sorting
        payloads = []
        for r in results:
            payload = dict(r.payload)
            payload["_retrieval_score"] = round(r.score, 4)
            payloads.append(payload)
        return payloads
    except Exception as exc:
        logger.warning("qdrant.search_failed", agent=agent_id, error=str(exc))
        return []
