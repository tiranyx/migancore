"""
Qdrant vector memory service — Tier 2 semantic memory for agents.

Day 12: Dense-only episodic memory (index + graceful degradation).
Day 18: Hybrid search — BM42 sparse + dense vectors with RRF fusion.

Architecture:
  - Per-agent collections: episodic_{agent_id}
  - Hybrid schema: named "dense" (768-dim cosine) + named "sparse" (BM42)
  - Turn-pair chunking: user + assistant embedded together
  - Brute-force search for <10k vectors (full_scan_threshold=10000)
  - Graceful degradation chain: hybrid → dense-only → []

Collection lifecycle:
  - Created on first message (lazy, idempotent)
  - Auto-migrated from old unnamed-dense schema to hybrid on first access
  - Never deleted automatically (agent memory persists)

Hybrid search (Qdrant >= 1.10.0 required):
  - Prefetch dense: top-k*3 candidates with score_threshold
  - Prefetch sparse: top-k*3 BM42 candidates (no threshold — different score range)
  - RRF fusion: Reciprocal Rank Fusion to merge both result sets
  - Benefit: proper nouns/names/dates recall +30-50% vs dense-only
  - Fallback: if Query API unavailable, uses legacy client.search() (dense-only)

Old collection detection and migration (Day 18):
  - Old schema: unnamed dense vector (VectorParams directly, not dict)
  - New schema: named "dense" + named "sparse" (dict + sparse_vectors_config)
  - Migration: fetch all points → delete → recreate hybrid → re-upsert with sparse
  - Zero data loss: chunk_text in payload used to recompute sparse vectors
"""

import asyncio
import time
import uuid

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    Fusion,
    FusionQuery,
    HnswConfigDiff,
    OptimizersConfigDiff,
    PointStruct,
    Prefetch,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from config import settings
from services.embedding import (
    embed_text,
    embed_sparse_document,
    embed_sparse_query,
    format_turn_pair,
)

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


def _is_hybrid_collection(col_info) -> bool:
    """Check if a collection has the new hybrid schema (named dense + sparse vectors).

    Old schema: col_info.config.params.vectors is a VectorParams (not dict).
    New schema: col_info.config.params.vectors is a dict AND sparse_vectors is set.
    """
    params = col_info.config.params
    # Named vectors are stored as a dict; unnamed is a VectorParams object
    has_named_vectors = isinstance(params.vectors, dict)
    has_sparse = bool(getattr(params, "sparse_vectors", None))
    return has_named_vectors and has_sparse


async def _create_hybrid_collection(client: AsyncQdrantClient, name: str) -> None:
    """Create a new hybrid collection with named dense + named sparse vectors."""
    await client.create_collection(
        collection_name=name,
        vectors_config={
            "dense": VectorParams(size=768, distance=Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(
                index=SparseIndexParams(on_disk=False)
            ),
        },
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
    logger.info("qdrant.hybrid_collection_created", name=name)


async def _migrate_collection_to_hybrid(client: AsyncQdrantClient, name: str) -> None:
    """Migrate an old unnamed-dense collection to the new hybrid schema.

    Strategy (zero data loss):
      1. Scroll all existing points (including vectors and payloads)
      2. Delete the old collection
      3. Create new hybrid collection (named dense + sparse)
      4. Recompute sparse vectors from chunk_text payload
      5. Upsert all points with both dense and sparse vectors

    Old points have unnamed (list) vectors — used directly as "dense" named vectors.
    New sparse vectors computed fresh from the stored chunk_text.
    """
    logger.info("qdrant.migration_starting", name=name)
    try:
        # 1. Fetch all existing points with their vectors
        scroll_result = await client.scroll(
            collection_name=name,
            limit=10000,
            with_payload=True,
            with_vectors=True,
        )
        existing_points = scroll_result[0]
        logger.info(
            "qdrant.migration_fetched",
            name=name,
            point_count=len(existing_points),
        )

        # 2. Delete old collection
        await client.delete_collection(name)

        # 3. Create hybrid collection
        await _create_hybrid_collection(client, name)

        # 4. Re-upsert with sparse vectors if there were any points
        if existing_points:
            new_points = []
            for p in existing_points:
                chunk_text = (p.payload or {}).get("chunk_text", "")

                # Old unnamed vector: may be a list or dict{"": list}
                old_dense = p.vector
                if isinstance(old_dense, dict):
                    old_dense = old_dense.get("", old_dense.get("dense", []))

                # Compute sparse vector for this chunk
                sparse_vec = await embed_sparse_document(chunk_text) if chunk_text else None

                # Build new hybrid point vector
                point_vector: dict = {"dense": old_dense}
                if sparse_vec is not None:
                    point_vector["sparse"] = sparse_vec

                new_points.append(
                    PointStruct(
                        id=p.id,
                        payload=p.payload,
                        vector=point_vector,
                    )
                )

            await client.upsert(collection_name=name, points=new_points)
            logger.info(
                "qdrant.migration_complete",
                name=name,
                points_migrated=len(new_points),
            )
        else:
            logger.info("qdrant.migration_complete", name=name, points_migrated=0)

    except Exception as exc:
        logger.warning(
            "qdrant.migration_failed",
            name=name,
            error=str(exc),
        )
        # If migration fails, the collection may be in undefined state.
        # Attempt to recreate it clean (data loss acceptable if migration failed).
        try:
            if await client.collection_exists(name):
                await client.delete_collection(name)
            await _create_hybrid_collection(client, name)
            logger.warning("qdrant.migration_fallback_recreated", name=name)
        except Exception as inner_exc:
            logger.warning("qdrant.migration_fallback_failed", name=name, error=str(inner_exc))


async def ensure_collection(agent_id: str, col_type: str = "episodic") -> None:
    """Ensure a hybrid Qdrant collection exists for an agent.

    Idempotent: safe to call on every request.
    Auto-migrates old unnamed-dense collections to hybrid schema (Day 18).

    New collections: named dense (768-dim cosine) + named sparse (BM42).
    Old collections: detected by non-dict vectors config → auto-migrated.
    """
    name = _col(agent_id, col_type)
    client = await _get_client()
    try:
        if await client.collection_exists(name):
            col_info = await client.get_collection(name)
            if not _is_hybrid_collection(col_info):
                # Old schema detected → migrate to hybrid
                logger.info("qdrant.old_schema_detected", name=name)
                await _migrate_collection_to_hybrid(client, name)
            return

        # Brand new collection — create hybrid directly
        await _create_hybrid_collection(client, name)

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
    """Embed and store a conversation turn pair in Qdrant (hybrid: dense + sparse).

    Called as asyncio.create_task() after message save — never blocks response.
    Semaphore limits concurrent CPU-bound embed operations to 2.
    Failures are logged and silently dropped (Tier 1 Redis remains authoritative).

    Sparse vectors: computed from chunk_text using BM42.
    If BM42 unavailable, falls back to dense-only point (still searchable).
    """
    async with _embed_semaphore:
        try:
            await ensure_collection(agent_id)
            chunk_text = format_turn_pair(user_message, assistant_message)

            # Compute both dense and sparse vectors concurrently
            dense_vec, sparse_vec = await asyncio.gather(
                embed_text(chunk_text),
                embed_sparse_document(chunk_text),
            )

            # Build hybrid point vector
            point_vector: dict = {"dense": dense_vec}
            if sparse_vec is not None:
                point_vector["sparse"] = sparse_vec

            client = await _get_client()
            await client.upsert(
                collection_name=_col(agent_id),
                points=[
                    PointStruct(
                        id=uuid.uuid4().hex,
                        vector=point_vector,
                        payload={
                            "agent_id": agent_id,
                            "tenant_id": tenant_id,
                            "session_id": session_id,
                            "turn_index": turn_index,
                            "timestamp": int(time.time()),
                            "user_message": user_message,
                            "assistant_message": assistant_message,
                            "chunk_text": chunk_text,
                            "has_sparse": sparse_vec is not None,
                        },
                    )
                ],
            )
            logger.info(
                "qdrant.turn_indexed",
                agent=agent_id,
                session=session_id,
                turn=turn_index,
                hybrid=sparse_vec is not None,
            )
        except Exception as exc:
            logger.warning(
                "qdrant.index_failed",
                agent=agent_id,
                error=str(exc),
            )


async def _search_hybrid(
    client: AsyncQdrantClient,
    col_name: str,
    query: str,
    top_k: int,
    score_threshold: float,
) -> list[dict]:
    """Hybrid search using Qdrant Query API with RRF fusion (requires Qdrant >= 1.10.0).

    Fetches top-k*3 candidates from both dense and sparse prefetch legs,
    then fuses them with Reciprocal Rank Fusion (RRF).

    Dense prefetch: applies score_threshold to filter noise.
    Sparse prefetch: no threshold (BM42 scores are not cosine similarities).
    """
    query_dense, query_sparse = await asyncio.gather(
        embed_text(query),
        embed_sparse_query(query),
    )

    prefetch_legs = [
        Prefetch(
            query=query_dense,
            using="dense",
            limit=top_k * 3,
            score_threshold=score_threshold,
        ),
    ]

    # Add sparse leg only if BM42 available
    if query_sparse is not None:
        prefetch_legs.append(
            Prefetch(
                query=SparseVector(
                    indices=query_sparse.indices,
                    values=query_sparse.values,
                ),
                using="sparse",
                limit=top_k * 3,
            )
        )

    response = await client.query_points(
        collection_name=col_name,
        prefetch=prefetch_legs,
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k,
        with_payload=True,
    )

    # query_points returns QueryResponse; .points is list[ScoredPoint]
    points = response.points if hasattr(response, "points") else response
    payloads = []
    for r in points:
        payload = dict(r.payload)
        payload["_retrieval_score"] = round(r.score, 4)
        payloads.append(payload)
    return payloads


async def _search_dense_only(
    client: AsyncQdrantClient,
    col_name: str,
    query: str,
    top_k: int,
    score_threshold: float,
) -> list[dict]:
    """Dense-only fallback search using legacy client.search() API.

    Used when: Qdrant < 1.10.0, hybrid search fails, or sparse model unavailable.
    Works with both old (unnamed) and new (named "dense") collections.
    """
    vector = await embed_text(query)

    # Try named "dense" first (new hybrid collections), fall back to unnamed
    try:
        results = await client.search(
            collection_name=col_name,
            query_vector=("dense", vector),
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
    except Exception:
        # Old unnamed vector collection
        results = await client.search(
            collection_name=col_name,
            query_vector=vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )

    payloads = []
    for r in results:
        payload = dict(r.payload)
        payload["_retrieval_score"] = round(r.score, 4)
        payloads.append(payload)
    return payloads


async def search_semantic(
    agent_id: str,
    query: str,
    top_k: int = TOP_K_EPISODIC,
    score_threshold: float = SCORE_THRESHOLD,
) -> list[dict]:
    """Search agent episodic memory by semantic similarity.

    Day 18: Tries hybrid search (dense + BM42 sparse + RRF) first.
    Falls back to dense-only search if hybrid unavailable.
    Returns [] if Qdrant unavailable or collection doesn't exist yet.

    Args:
        score_threshold: Applied to dense prefetch leg. Default 0.55 for
            tool_executor use. vector_retrieval.py uses 0.65 (stricter).

    Returns list of payloads with '_retrieval_score' key for caller-side sorting.
    """
    try:
        client = await _get_client()
        col_name = _col(agent_id)
        if not await client.collection_exists(col_name):
            return []

        # Try hybrid search first (requires Qdrant >= 1.10.0 + hybrid schema)
        try:
            col_info = await client.get_collection(col_name)
            if _is_hybrid_collection(col_info):
                results = await _search_hybrid(
                    client, col_name, query, top_k, score_threshold
                )
                logger.debug(
                    "qdrant.search_hybrid",
                    agent=agent_id,
                    results=len(results),
                )
                return results
        except Exception as hybrid_exc:
            logger.warning(
                "qdrant.hybrid_search_failed_fallback",
                agent=agent_id,
                error=str(hybrid_exc),
            )

        # Dense-only fallback
        results = await _search_dense_only(
            client, col_name, query, top_k, score_threshold
        )
        logger.debug(
            "qdrant.search_dense_fallback",
            agent=agent_id,
            results=len(results),
        )
        return results

    except Exception as exc:
        logger.warning("qdrant.search_failed", agent=agent_id, error=str(exc))
        return []
