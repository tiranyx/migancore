"""
Embedding service — Tier 2 semantic memory (Day 12 + Day 18 hybrid upgrade).

Dense model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
  - 768 dimensions, Cosine distance
  - Bahasa Indonesia native (50-language multilingual)
  - Max 128 WordPiece tokens per input (~80-100 words conversational)

Sparse model: Qdrant/bm42-all-minilm-l6-v2-attentions (Day 18)
  - BM42 = BM25 scoring on attention-weighted token importance
  - Multilingual via all-MiniLM-L6
  - Better recall for proper nouns, names, dates, product terms
  - CRITICAL: use query_embed() for queries, embed() for documents

Architecture:
  - Singleton models initialized at FastAPI lifespan startup
  - CPU inference via ONNX Runtime (no GPU required)
  - All inference offloaded to thread pool to avoid blocking async event loop
  - Semaphore in vector_memory.py limits concurrent embed ops to 2
  - Model cache: /app/.cache/fastembed (persistent volume across rebuilds)
"""

import asyncio

import structlog
from fastembed import TextEmbedding, SparseTextEmbedding
from qdrant_client.models import SparseVector as QdrantSparseVector
from starlette.concurrency import run_in_threadpool

logger = structlog.get_logger()

# Dense model — primary semantic similarity
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
EMBED_DIM = 768

# Sparse model — keyword recall boost (BM42, Day 18)
SPARSE_MODEL_NAME = "Qdrant/bm42-all-minilm-l6-v2-attentions"

CACHE_DIR = "/app/.cache/fastembed"

_model: TextEmbedding | None = None
_model_lock = asyncio.Lock()

_sparse_model: SparseTextEmbedding | None = None
_sparse_model_lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# Dense model
# ---------------------------------------------------------------------------

async def get_model() -> TextEmbedding:
    """Return the singleton dense TextEmbedding model, initializing if needed."""
    global _model
    if _model is None:
        async with _model_lock:
            if _model is None:
                logger.info("embedding.model_loading", model=MODEL_NAME)
                _model = await run_in_threadpool(
                    lambda: TextEmbedding(
                        model_name=MODEL_NAME,
                        cache_dir=CACHE_DIR,
                        threads=2,
                    )
                )
                logger.info("embedding.model_ready", model=MODEL_NAME, dim=EMBED_DIM)
    return _model


async def embed_text(text: str) -> list[float]:
    """Embed a single text string. Offloads CPU work to thread pool."""
    model = await get_model()
    vectors = await run_in_threadpool(
        lambda: list(model.embed([text], batch_size=1))
    )
    return vectors[0].tolist()


# ---------------------------------------------------------------------------
# Sparse model (BM42) — Day 18
# ---------------------------------------------------------------------------

async def get_sparse_model() -> SparseTextEmbedding | None:
    """Return the singleton BM42 sparse model, initializing if needed.

    Returns None if the model fails to load — callers degrade gracefully
    to dense-only search. BM42 model: ~90MB ONNX download on first use,
    cached at CACHE_DIR for subsequent container restarts (persistent volume).
    """
    global _sparse_model
    if _sparse_model is None:
        async with _sparse_model_lock:
            if _sparse_model is None:
                try:
                    logger.info("embedding.sparse_model_loading", model=SPARSE_MODEL_NAME)
                    _sparse_model = await run_in_threadpool(
                        lambda: SparseTextEmbedding(
                            model_name=SPARSE_MODEL_NAME,
                            cache_dir=CACHE_DIR,
                        )
                    )
                    logger.info("embedding.sparse_model_ready", model=SPARSE_MODEL_NAME)
                except Exception as exc:
                    logger.warning(
                        "embedding.sparse_model_failed",
                        model=SPARSE_MODEL_NAME,
                        error=str(exc),
                    )
                    return None
    return _sparse_model


async def embed_sparse_document(text: str) -> QdrantSparseVector | None:
    """Generate BM42 sparse vector for indexing a document.

    Uses model.embed() — BM42 uses different weights for documents vs queries.
    Returns None if sparse model unavailable (caller degrades to dense-only).
    """
    model = await get_sparse_model()
    if model is None:
        return None
    try:
        result = await run_in_threadpool(
            lambda: list(model.embed([text], batch_size=1))[0]
        )
        return QdrantSparseVector(
            indices=result.indices.tolist(),
            values=result.values.tolist(),
        )
    except Exception as exc:
        logger.warning("embedding.sparse_doc_failed", error=str(exc))
        return None


async def embed_sparse_query(text: str) -> QdrantSparseVector | None:
    """Generate BM42 sparse vector for querying.

    Uses model.query_embed() — BM42 REQUIRES this for queries (different
    token weighting than document embedding). Do NOT use embed() for queries.
    Returns None if sparse model unavailable (caller degrades to dense-only).
    """
    model = await get_sparse_model()
    if model is None:
        return None
    try:
        result = await run_in_threadpool(
            lambda: list(model.query_embed(text))[0]
        )
        return QdrantSparseVector(
            indices=result.indices.tolist(),
            values=result.values.tolist(),
        )
    except Exception as exc:
        logger.warning("embedding.sparse_query_failed", error=str(exc))
        return None


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def format_turn_pair(user_message: str, assistant_message: str) -> str:
    """Format a user+assistant turn pair for embedding.

    Uses Bahasa Indonesia labels matching the model's training language.
    Structured concatenation with newline separator improves semantic coherence
    (MemMachine research: +2% accuracy vs space-concatenation).
    """
    user_text = user_message.strip()[:300]
    assistant_text = assistant_message.strip()[:300]
    return f"Pengguna: {user_text}\nAsisten: {assistant_text}"
