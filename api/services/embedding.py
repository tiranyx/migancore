"""
Embedding service — Tier 2 semantic memory.

Model: sentence-transformers/paraphrase-multilingual-mpnet-base-v2
  - 768 dimensions, Cosine distance
  - Bahasa Indonesia native (50-language multilingual)
  - Max 128 WordPiece tokens per input (~80-100 words conversational)

Architecture:
  - Singleton TextEmbedding instance initialized at FastAPI lifespan startup
  - CPU inference via ONNX Runtime (no GPU required)
  - Embedding offloaded to thread pool to avoid blocking async event loop
  - Semaphore in vector_memory.py limits concurrent embed ops to 2
"""

import asyncio

import structlog
from fastembed import TextEmbedding
from starlette.concurrency import run_in_threadpool

logger = structlog.get_logger()

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
CACHE_DIR = "/app/.cache/fastembed"
EMBED_DIM = 768

_model: TextEmbedding | None = None
_model_lock = asyncio.Lock()


async def get_model() -> TextEmbedding:
    """Return the singleton TextEmbedding model, initializing if needed."""
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


def format_turn_pair(user_message: str, assistant_message: str) -> str:
    """Format a user+assistant turn pair for embedding.

    Uses Bahasa Indonesia labels matching the model's training language.
    Structured concatenation with newline separator improves semantic coherence
    (MemMachine research: +2% accuracy vs space-concatenation).
    """
    user_text = user_message.strip()[:300]
    assistant_text = assistant_message.strip()[:300]
    return f"Pengguna: {user_text}\nAsisten: {assistant_text}"
