"""
Tool executor — dispatches skill_id to handler functions.

Architecture:
  TOOL_REGISTRY: dict[str, handler_fn]
  ToolContext: carries tenant/agent info for storage-aware tools
  ToolExecutor.execute(): validate → dispatch → return structured result

Handlers:
  web_search     — DuckDuckGo Instant Answers (free, no key)
  memory_write   — Redis K-V tier 1 storage
  memory_search  — Redis K-V prefix + substring search (Qdrant hybrid + Redis fallback)
  python_repl    — subprocess isolation (process boundary = real sandbox)
  generate_image — fal.ai FLUX schnell (Day 24) — needs FAL_KEY env
  read_file      — Read file from /app/workspace/ sandbox (Day 24)
  write_file     — Write file to /app/workspace/ sandbox (Day 24)

Tool calling flow (in chat.py):
  1. Build Ollama tools spec from skills.json
  2. Call Ollama with messages + tools
  3. If response.tool_calls → execute each → inject role:"tool" message
  4. Re-call Ollama (loop max MAX_TOOL_ITERATIONS)
  5. Persist all tool_calls in messages.tool_calls column

Research notes (2026-05-03):
  - Qwen2.5-7B-Instruct supports Ollama native tool calling (stream=false required)
  - Tool result format: {"role": "tool", "content": "<json string>"}
  - DuckDuckGo JSON API: no key, ~20 req/s per IP, good for MVP
  - subprocess gives real process isolation vs exec() which is easily escaped

Day 24 notes (2026-05-04):
  - fal.ai FLUX schnell: POST https://fal.run/fal-ai/flux/schnell, sync response ~3-8s
  - File sandbox: WORKSPACE_DIR=/app/workspace, path traversal blocked via Path.resolve()
  - generate_image timeout: 60s (fal.ai cold start can hit 15-20s occasionally)
"""

import asyncio
import json
import os
import subprocess
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Coroutine

import httpx
import structlog

from config import settings
from services.config_loader import load_skills_config
from services.memory import memory_write, memory_list
from services.tool_policy import ToolPolicyChecker, validate_python_code, PolicyViolation

logger = structlog.get_logger()

MAX_TOOL_ITERATIONS = 5
DDG_ENDPOINT = "https://api.duckduckgo.com/"
FAL_FLUX_ENDPOINT = "https://fal.run/fal-ai/flux/schnell"

# Day 27 — ElevenLabs TTS
ELEVENLABS_TTS_ENDPOINT = "https://api.elevenlabs.io/v1/text-to-speech"
TTS_MAX_CHARS = 2500     # Free tier 10k/month — cap per-call to ~250 cents budget
TTS_MAX_AUDIO_BYTES = 2_000_000  # 2MB cap on returned audio (avoid MCP payload bloat)
FAL_VALID_SIZES = {
    "square_hd", "square", "portrait_4_3", "portrait_16_9",
    "landscape_4_3", "landscape_16_9",
}


# ---------------------------------------------------------------------------
# Context passed to all handlers
# ---------------------------------------------------------------------------

@dataclass
class ToolContext:
    tenant_id: str
    agent_id: str
    tenant_plan: str = "free"
    tool_policies: dict | None = None


class ToolExecutionError(Exception):
    """Raised for expected handler errors (bad args, API failure, etc.)."""
    pass


# ---------------------------------------------------------------------------
# Handlers — each returns a JSON-serializable dict
# ---------------------------------------------------------------------------

async def _web_search(args: dict, ctx: ToolContext) -> dict:
    """DuckDuckGo Instant Answers — free, no API key, works server-side."""
    query = args.get("query", "").strip()
    limit = min(int(args.get("limit", 5)), 10)

    if not query:
        raise ToolExecutionError("'query' is required")

    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
        "kl": "id-id",
    })

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(
                f"{DDG_ENDPOINT}?{params}",
                headers={"User-Agent": "MiganCore/0.3.0"},
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException as exc:
        raise ToolExecutionError("Web search timed out") from exc
    except Exception as exc:
        raise ToolExecutionError(f"Web search failed: {exc}") from exc

    results: list[dict] = []

    # Direct one-box answer (highest priority)
    if data.get("Answer"):
        results.append({
            "title": "Jawaban Langsung",
            "snippet": data["Answer"],
            "url": "",
            "source": "DuckDuckGo",
        })

    # Abstract (Wikipedia / knowledge graph)
    if data.get("Abstract"):
        results.append({
            "title": data.get("Heading", query),
            "snippet": data["Abstract"],
            "url": data.get("AbstractURL", ""),
            "source": data.get("AbstractSource", ""),
        })

    # Related topics
    for topic in data.get("RelatedTopics", []):
        if len(results) >= limit:
            break
        if isinstance(topic, dict) and topic.get("Text"):
            results.append({
                "title": topic["Text"][:80],
                "snippet": topic["Text"],
                "url": topic.get("FirstURL", ""),
                "source": "DuckDuckGo",
            })

    logger.info("tool.web_search", query=query, results=len(results))
    return {
        "results": results[:limit],
        "query": query,
        "result_count": len(results),
    }


async def _memory_write(args: dict, ctx: ToolContext) -> dict:
    """Write a key-value pair to agent's Redis memory (Tier 1)."""
    key = args.get("key", "").strip()
    value = args.get("value", "").strip()
    namespace = args.get("namespace", "default").strip() or "default"

    if not key:
        raise ToolExecutionError("'key' is required")
    if not value:
        raise ToolExecutionError("'value' is required")

    await memory_write(ctx.tenant_id, ctx.agent_id, key, value, namespace)
    logger.info("tool.memory_write", key=key, ns=namespace, agent=ctx.agent_id)

    return {"status": "written", "key": key, "namespace": namespace}


async def _memory_search(args: dict, ctx: ToolContext) -> dict:
    """Search agent memory — Qdrant hybrid semantic (Tier 2) with Redis K-V fallback (Tier 1).

    Day 12: Qdrant semantic search first → Redis substring fallback.
    Day 18: search_semantic() is now hybrid (dense + BM42 sparse + RRF).
    Day 20: Added asyncio.wait_for timeout (2.0s) — prevents blocking tool loop
            if Qdrant is slow. Falls through to Redis on timeout.
    """
    query = args.get("query", "").strip()
    limit = min(int(args.get("limit", 5)), 20)

    if not query:
        raise ToolExecutionError("'query' is required")

    # Tier 2: Qdrant hybrid semantic search (dense + BM42 sparse + RRF)
    try:
        from services.vector_memory import search_semantic
        semantic_hits = await asyncio.wait_for(
            search_semantic(ctx.agent_id, query, top_k=limit),
            timeout=2.0,
        )
        if semantic_hits:
            logger.info(
                "tool.memory_search.qdrant",
                query=query,
                matches=len(semantic_hits),
                top_score=semantic_hits[0].get("_retrieval_score", 0) if semantic_hits else 0,
            )
            return {
                "results": [
                    {
                        "user_message": r.get("user_message", ""),
                        "assistant_message": r.get("assistant_message", ""),
                        "session_id": r.get("session_id"),
                        "turn_index": r.get("turn_index"),
                        "timestamp": r.get("timestamp"),
                        "score": r.get("_retrieval_score"),
                    }
                    for r in semantic_hits
                ],
                "query": query,
                "source": "qdrant_hybrid",
            }
    except asyncio.TimeoutError:
        logger.warning("tool.memory_search.qdrant_timeout", query=query, timeout_s=2.0)
    except Exception as exc:
        logger.warning("tool.memory_search.qdrant_error", error=str(exc))

    # Tier 1 fallback: Redis K-V substring search
    all_memories = await memory_list(ctx.tenant_id, ctx.agent_id, limit=100)
    query_lower = query.lower()
    matches = [
        {"key": k, "value": v}
        for k, v in all_memories.items()
        if query_lower in k.lower() or query_lower in v.lower()
    ]
    logger.info("tool.memory_search.redis", query=query, matches=len(matches))
    return {
        "results": matches[:limit],
        "query": query,
        "total_in_memory": len(all_memories),
        "source": "redis_kv",
    }


async def _python_repl(args: dict, ctx: ToolContext) -> dict:
    """Execute Python code via subprocess — real process isolation.

    subprocess gives a genuine sandbox boundary vs exec() which is trivially
    escaped via __subclasses__() or __import__. Output capped at 2000 chars.

    Day 11: Added import blacklist validation (defense-in-depth).
    """
    code = args.get("code", "").strip()
    timeout = min(int(args.get("timeout", 30)), 30)

    if not code:
        raise ToolExecutionError("'code' is required")

    # Policy layer: block dangerous imports
    try:
        validate_python_code(code)
    except PolicyViolation as exc:
        logger.warning("tool.python_repl.policy_violation", reason=exc.reason, agent=ctx.agent_id)
        raise ToolExecutionError(f"Security policy violation: {exc.reason}") from exc

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                subprocess.run,
                ["python", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
            ),
            timeout=float(timeout) + 2,
        )

        stdout = (result.stdout or "")[:2000]
        stderr = (result.stderr or "")[:500]

        logger.info("tool.python_repl", rc=result.returncode, agent=ctx.agent_id)
        return {
            "output": stdout,
            "error": stderr if stderr else None,
            "return_code": result.returncode,
            "success": result.returncode == 0,
        }

    except asyncio.TimeoutError:
        return {"output": "", "error": f"Timed out after {timeout}s", "success": False, "return_code": -1}
    except FileNotFoundError:
        return {"output": "", "error": "Python interpreter not found", "success": False, "return_code": -1}
    except Exception as exc:
        return {"output": "", "error": str(exc), "success": False, "return_code": -1}


async def _text_to_speech(args: dict, ctx: ToolContext) -> dict:
    """Convert text to speech via ElevenLabs TTS API (Day 27).

    Returns base64-encoded mp3 audio (capped at 2MB) plus metadata.
    Uses `eleven_flash_v2_5` model — ~75ms TTFB, free-tier compatible.
    Free tier limit: 10,000 chars/month per ElevenLabs account.

    Args:
        text: text to synthesize (required, max 2500 chars per call)
        voice_id: optional ElevenLabs voice ID (default Rachel)
        model_id: optional model override (default eleven_flash_v2_5)
    """
    import base64

    text = (args.get("text") or "").strip()
    if not text:
        raise ToolExecutionError("'text' is required and cannot be empty")
    if len(text) > TTS_MAX_CHARS:
        raise ToolExecutionError(
            f"Text too long ({len(text)} chars > {TTS_MAX_CHARS} cap). "
            f"Split into smaller chunks."
        )

    if not settings.ELEVENLABS_KEY:
        raise ToolExecutionError(
            "ElevenLabs not configured. Set ELEVENLABS_KEY env var (free tier: "
            "https://elevenlabs.io)."
        )

    voice_id = args.get("voice_id") or settings.ELEVENLABS_VOICE_ID
    model_id = args.get("model_id") or settings.ELEVENLABS_MODEL

    url = f"{ELEVENLABS_TTS_ENDPOINT}/{voice_id}"
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }
    headers = {
        "xi-api-key": settings.ELEVENLABS_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    logger.info(
        "tool.text_to_speech.start",
        chars=len(text),
        voice_id=voice_id,
        model_id=model_id,
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 401:
            raise ToolExecutionError("ElevenLabs auth failed (check ELEVENLABS_KEY)")
        if resp.status_code == 429:
            raise ToolExecutionError(
                "ElevenLabs quota exceeded. Free tier: 10k chars/month. "
                "Upgrade or wait for monthly reset."
            )
        if resp.status_code != 200:
            raise ToolExecutionError(
                f"ElevenLabs error HTTP {resp.status_code}: {resp.text[:200]}"
            )
    except httpx.TimeoutException:
        raise ToolExecutionError("ElevenLabs TTS request timed out (30s)")
    except httpx.HTTPError as exc:
        raise ToolExecutionError(f"ElevenLabs HTTP error: {exc}")

    audio_bytes = resp.content
    if len(audio_bytes) > TTS_MAX_AUDIO_BYTES:
        raise ToolExecutionError(
            f"Audio response too large ({len(audio_bytes)} > {TTS_MAX_AUDIO_BYTES} bytes)."
        )

    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

    logger.info(
        "tool.text_to_speech.done",
        chars=len(text),
        audio_bytes=len(audio_bytes),
    )

    return {
        "format": "mp3",
        "encoding": "base64",
        "audio_base64": audio_b64,
        "size_bytes": len(audio_bytes),
        "chars_synthesized": len(text),
        "voice_id": voice_id,
        "model_id": model_id,
        "hint": (
            "Decode with: base64 -d > out.mp3, then play. "
            f"~{len(text)} chars used from free tier quota."
        ),
    }


async def _generate_image(args: dict, ctx: ToolContext) -> dict:
    """Generate an image via fal.ai FLUX schnell.

    Day 24: fal.ai REST API — sync endpoint, ~3-8s per image.
    Model: fal-ai/flux/schnell — 4 inference steps, fast, cheap (~$0.003/image).
    Requires FAL_KEY environment variable.

    Returns image URL (hosted on fal.media CDN, persistent).
    """
    prompt = args.get("prompt", "").strip()
    if not prompt:
        raise ToolExecutionError("'prompt' is required")

    image_size = args.get("image_size", "landscape_4_3").strip()
    if image_size not in FAL_VALID_SIZES:
        image_size = "landscape_4_3"

    num_images = max(1, min(int(args.get("num_images", 1)), 4))

    fal_key = settings.FAL_KEY
    if not fal_key:
        raise ToolExecutionError(
            "Image generation is not configured (FAL_KEY missing). "
            "Contact admin to enable this tool."
        )

    payload = {
        "prompt": prompt,
        "image_size": image_size,
        "num_inference_steps": 4,
        "num_images": num_images,
        "enable_safety_checker": True,
    }

    logger.info("tool.generate_image.start", prompt=prompt[:80], size=image_size, n=num_images)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            resp = await client.post(
                FAL_FLUX_ENDPOINT,
                json=payload,
                headers={
                    "Authorization": f"Key {fal_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        raise ToolExecutionError("Image generation timed out (60s). Try again.")
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:200]
        raise ToolExecutionError(f"fal.ai API error {exc.response.status_code}: {body}") from exc
    except Exception as exc:
        raise ToolExecutionError(f"Image generation failed: {exc}") from exc

    images = data.get("images", [])
    if not images:
        raise ToolExecutionError("fal.ai returned no images. Try a different prompt.")

    result_images = [
        {
            "url": img.get("url", ""),
            "width": img.get("width"),
            "height": img.get("height"),
        }
        for img in images
    ]

    inference_time = data.get("timings", {}).get("inference")
    seed = data.get("seed")

    logger.info(
        "tool.generate_image.done",
        images=len(result_images),
        url=result_images[0]["url"][:60] if result_images else "",
        inference_s=inference_time,
    )

    return {
        "images": result_images,
        "prompt": prompt,
        "model": "fal-ai/flux/schnell",
        "seed": seed,
        "inference_time_s": round(inference_time, 2) if inference_time else None,
        # Convenience shortcut for single-image requests
        "url": result_images[0]["url"] if result_images else None,
    }


# ---------------------------------------------------------------------------
# Day 38 — Vision: analyze_image via Gemini 2.5 Flash (cheap multimodal)
#
# Pricing (May 2026, official): $0.30/M input · $0.075/M output
# 1024x1024 image ≈ 258 tokens → ~$0.00008/image input. Very cheap.
# Bilingual ID+EN supported natively. Latency 1.5-2.5s typical.
#
# Fallback chain on Gemini 5xx/timeout: try Claude Sonnet 4.5 vision (60x cost
# but reliable). If both fail, return clean error.
# ---------------------------------------------------------------------------

import base64

GEMINI_VISION_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)
ANTHROPIC_MESSAGES_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANALYZE_MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB cap (Gemini accepts up to 20MB but we cap for safety)


async def _fetch_image_bytes(image_url: str) -> tuple[bytes, str]:
    """Download an image URL and return (bytes, mime_type). Raises on too-large or non-image.

    Sends a real browser User-Agent because some hosts (Wikipedia, CDN, etc.)
    return 403 to default Python clients to discourage scraping.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 MiganCore-Vision/1.0"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        try:
            resp = await client.get(image_url, follow_redirects=True, headers=headers)
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise ToolExecutionError(f"Timeout fetching image from {image_url[:80]}")
        except httpx.HTTPStatusError as exc:
            raise ToolExecutionError(
                f"Cannot fetch image (HTTP {exc.response.status_code}): {image_url[:80]}"
            ) from exc
    content = resp.content
    if len(content) > ANALYZE_MAX_IMAGE_BYTES:
        raise ToolExecutionError(
            f"Image too large: {len(content)} bytes > {ANALYZE_MAX_IMAGE_BYTES} cap"
        )
    mime = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
    if not mime.startswith("image/"):
        raise ToolExecutionError(f"URL does not return an image (got {mime})")
    return content, mime


async def _analyze_via_gemini(image_b64: str, mime: str, question: str, lang: str) -> str:
    """Call Gemini 2.5 Flash with inline image. Returns text answer or raises."""
    key = settings.GEMINI_API_KEY
    if not key:
        raise ToolExecutionError("GEMINI_API_KEY not set")
    lang_label = "Bahasa Indonesia natural" if lang == "id" else "English"
    sys = (
        f"You are a vision assistant. Answer the user's question about the image "
        f"in {lang_label}. Be specific, factual, concise. If text appears in the image, "
        f"transcribe it. If you can't see something asked, say so."
    )
    payload = {
        "systemInstruction": {"parts": [{"text": sys}]},
        "contents": [{
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": mime, "data": image_b64}},
                {"text": question},
            ],
        }],
        "generationConfig": {"maxOutputTokens": 600, "temperature": 0.3, "topP": 0.95},
        "safetySettings": [
            {"category": c, "threshold": "BLOCK_NONE"}
            for c in [
                "HARM_CATEGORY_HARASSMENT",
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_DANGEROUS_CONTENT",
            ]
        ],
    }
    url = GEMINI_VISION_ENDPOINT.format(model="gemini-2.5-flash", key=key)
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise ToolExecutionError(f"Gemini Vision HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
    cands = data.get("candidates", [])
    if not cands:
        raise ToolExecutionError(f"Gemini returned no candidates: {data}")
    parts = cands[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        finish = cands[0].get("finishReason", "")
        raise ToolExecutionError(f"Gemini empty response, finishReason={finish}")
    return text


async def _analyze_via_claude(image_b64: str, mime: str, question: str, lang: str) -> str:
    """Fallback: Claude Sonnet 4.5 vision. Cost ~$0.005/image. Use only if Gemini fails."""
    key = settings.ANTHROPIC_API_KEY
    if not key:
        raise ToolExecutionError("ANTHROPIC_API_KEY not set (Claude vision fallback unavailable)")
    lang_label = "Bahasa Indonesia natural" if lang == "id" else "English"
    payload = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 600,
        "system": (
            f"You are a vision assistant. Answer in {lang_label}. "
            f"Be specific, factual, concise. Transcribe any visible text."
        ),
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": image_b64}},
                {"type": "text", "text": question},
            ],
        }],
    }
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        resp = await client.post(ANTHROPIC_MESSAGES_ENDPOINT, json=payload, headers=headers)
        if resp.status_code != 200:
            raise ToolExecutionError(f"Claude Vision HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
    blocks = data.get("content", [])
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
    if not text:
        raise ToolExecutionError("Claude vision returned empty content")
    return text


async def _analyze_image(args: dict, ctx: ToolContext) -> dict:
    """Analyze an image via Gemini 2.5 Flash (primary) -> Claude Sonnet 4.5 (fallback).

    Args:
      image_url: HTTPS URL to image (jpg/png/webp). Required if image_base64 absent.
      image_base64: base64-encoded image bytes. Either this OR image_url required.
      question: What to ask about the image. Default: "Describe this image in detail."
      lang: 'id' (default) or 'en' for response language.

    Returns:
      {"answer": "...", "model": "gemini-2.5-flash"|"claude-sonnet-4-5", "lang": "id"|"en"}
    """
    image_url = (args.get("image_url") or "").strip()
    image_b64_in = (args.get("image_base64") or "").strip()
    question = (args.get("question") or "Describe this image in detail. List notable elements and any visible text.").strip()
    lang = (args.get("lang") or "id").lower().strip()
    if lang not in ("id", "en"):
        lang = "id"

    if not image_url and not image_b64_in:
        raise ToolExecutionError("Provide either 'image_url' or 'image_base64'")

    # Resolve image to (bytes, mime)
    if image_url:
        if not image_url.startswith(("http://", "https://")):
            raise ToolExecutionError("image_url must be http(s)://")
        content, mime = await _fetch_image_bytes(image_url)
        image_b64 = base64.b64encode(content).decode("ascii")
    else:
        # User-supplied base64; cap size
        if len(image_b64_in) > ANALYZE_MAX_IMAGE_BYTES * 2:  # base64 = ~33% larger than raw
            raise ToolExecutionError("image_base64 too large (>16MB encoded)")
        image_b64 = image_b64_in
        mime = (args.get("mime_type") or "image/jpeg").strip()
        if not mime.startswith("image/"):
            mime = "image/jpeg"

    logger.info("tool.analyze_image.start", lang=lang, q_preview=question[:80], src="url" if image_url else "b64")

    # Try Gemini first (cheap), fallback Claude (reliable)
    try:
        answer = await _analyze_via_gemini(image_b64, mime, question, lang)
        model_used = "gemini-2.5-flash"
    except ToolExecutionError as gem_err:
        logger.warning("tool.analyze_image.gemini_failed", error=str(gem_err)[:200])
        try:
            answer = await _analyze_via_claude(image_b64, mime, question, lang)
            model_used = "claude-sonnet-4-5"
        except ToolExecutionError as claude_err:
            logger.warning("tool.analyze_image.both_failed", claude_err=str(claude_err)[:200])
            raise ToolExecutionError(
                f"Image analysis failed on both backends. Gemini: {str(gem_err)[:150]}. "
                f"Claude: {str(claude_err)[:150]}"
            )

    logger.info("tool.analyze_image.done", model=model_used, answer_len=len(answer), lang=lang)
    return {
        "answer": answer,
        "model": model_used,
        "lang": lang,
        "question": question,
    }


# ---------------------------------------------------------------------------
# Day 42 — HYPERX Browser integration (user-built Node.js anonymous browser)
#
# Mounted RO at /app/hyperx from /opt/sidix/tools/hyperx-browser via docker-compose.
# 3 capabilities exposed: hyperx_get (fetch+parse), hyperx_search (7 engines),
# hyperx_scrape (regex extract).
#
# Strategy Day 42: subprocess.run per call (~80-200ms node startup overhead OK
# for occasional use). Day 43+ refactor to persistent stdio MCP client (mcp SDK)
# for sub-100ms latency at scale.
#
# ADO alignment: user-owned tool = first-class citizen, modular brain principle.
# ---------------------------------------------------------------------------
HYPERX_DIR = "/app/hyperx"
HYPERX_BIN = f"{HYPERX_DIR}/bin/hyperx.js"
HYPERX_TIMEOUT_S = 30


def _hyperx_available() -> bool:
    """Check if HYPERX is mounted + node binary available."""
    return os.path.isfile(HYPERX_BIN) and Path("/usr/bin/node").exists()


async def _hyperx_run(args: list[str], timeout: int = HYPERX_TIMEOUT_S) -> dict:
    """Run hyperx.js with --json + --no-history flags, return parsed JSON.

    --no-history is critical: HYPERX source mount is read-only, so writing
    history.json fails (EROFS). Also a privacy win for ADO ethos.

    cwd=/tmp because HYPERX may want to write working files; /tmp is always
    writable in our container (no bind mount). HYPERX_HOME unset uses pwd.
    """
    import subprocess
    if not _hyperx_available():
        raise ToolExecutionError(
            f"HYPERX not available — expected mount at {HYPERX_DIR}. "
            "Check docker-compose volumes."
        )
    cmd = ["node", HYPERX_BIN, "--json", "--no-history", *args]
    try:
        proc = await asyncio.to_thread(
            subprocess.run, cmd,
            capture_output=True, text=True, timeout=timeout, cwd="/tmp",
        )
    except subprocess.TimeoutExpired:
        raise ToolExecutionError(f"HYPERX timed out ({timeout}s) for args {args[:3]}")
    if proc.returncode != 0:
        raise ToolExecutionError(
            f"HYPERX failed (rc={proc.returncode}): {proc.stderr[:300]}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ToolExecutionError(
            f"HYPERX JSON parse error: {exc}. Raw: {proc.stdout[:200]}"
        )


async def _hyperx_get(args: dict, ctx: ToolContext) -> dict:
    """Fetch a URL anonymously via HYPERX browser.

    Returns parsed text + links + images + meta + status.
    Use this for richer extraction than web_read (which only returns markdown).
    """
    url = (args.get("url") or "").strip()
    if not url:
        raise ToolExecutionError("'url' is required")
    if not url.startswith(("http://", "https://")):
        raise ToolExecutionError("URL must start with http(s)://")
    raw = bool(args.get("raw", False))

    cli_args = [url]
    if raw:
        cli_args.append("--raw")

    logger.info("tool.hyperx_get.start", url=url[:120], raw=raw)
    data = await _hyperx_run(cli_args)
    logger.info(
        "tool.hyperx_get.done",
        url=url[:120],
        status=data.get("status"),
        text_len=len(data.get("text") or ""),
        links=len(data.get("links") or []),
        elapsed=data.get("elapsed"),
    )
    # Trim text/html for LLM consumption (cap 30K chars)
    text = (data.get("text") or "")[:30_000]
    return {
        "url": data.get("url"),
        "final_url": data.get("finalUrl"),
        "status": data.get("status"),
        "title": data.get("meta", {}).get("title"),
        "text": text,
        "links": (data.get("links") or [])[:50],
        "images": (data.get("images") or [])[:30],
        "elapsed_ms": data.get("elapsed"),
        "source": "hyperx",
    }


async def _hyperx_search(args: dict, ctx: ToolContext) -> dict:
    """Web search via HYPERX (7 engines: google, ddg, brave, bing, startpage, yandex, ecosia).

    Returns structured results with title, URL, snippet.
    """
    query = (args.get("query") or "").strip()
    if not query:
        raise ToolExecutionError("'query' is required")
    engine = (args.get("engine") or "ddg").lower()
    valid_engines = {"google", "ddg", "brave", "bing", "startpage", "yandex", "ecosia"}
    if engine not in valid_engines:
        engine = "ddg"
    limit = max(1, min(int(args.get("limit", 10)), 30))

    cli_args = [query, f"--engine={engine}", f"--limit={limit}"]
    logger.info("tool.hyperx_search.start", q=query[:80], engine=engine, limit=limit)
    data = await _hyperx_run(cli_args)
    results = data.get("results") or []
    logger.info(
        "tool.hyperx_search.done",
        q=query[:80],
        engine=engine,
        results=len(results),
        elapsed=data.get("elapsed"),
    )
    return {
        "query": query,
        "engine": engine,
        "results": [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "snippet": (r.get("snippet") or "")[:300],
            }
            for r in results[:limit]
        ],
        "count": len(results),
        "elapsed_ms": data.get("elapsed"),
        "source": "hyperx",
    }


async def _hyperx_scrape(args: dict, ctx: ToolContext) -> dict:
    """Scrape a URL with regex selectors via HYPERX.

    Args:
      url: target URL
      selectors: dict of {field_name: regex_pattern} to extract from HTML
    Returns:
      {extracted: {...}, url, status}
    """
    url = (args.get("url") or "").strip()
    if not url or not url.startswith(("http://", "https://")):
        raise ToolExecutionError("Valid 'url' (http/https) is required")
    selectors = args.get("selectors") or {}
    if not isinstance(selectors, dict) or not selectors:
        raise ToolExecutionError("'selectors' dict required: {field: regex}")

    # HYPERX scrape API: pass selectors as JSON via --selectors flag (or fall back to fetch + regex)
    # Since hyperx.js CLI may not have direct --selectors, use --raw HTML then regex client-side
    cli_args = [url, "--raw"]
    logger.info("tool.hyperx_scrape.start", url=url[:120], fields=list(selectors.keys()))
    data = await _hyperx_run(cli_args)
    html = data.get("html") or ""
    if not html:
        raise ToolExecutionError(f"HYPERX returned no HTML for {url[:80]}")

    # Apply each regex
    import re
    extracted = {}
    for field, pattern in selectors.items():
        try:
            m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            extracted[field] = m.group(1) if (m and m.groups()) else (m.group(0) if m else None)
        except re.error as exc:
            extracted[field] = f"[regex error: {exc}]"

    logger.info(
        "tool.hyperx_scrape.done",
        url=url[:120],
        extracted_fields=sum(1 for v in extracted.values() if v),
        total_fields=len(selectors),
    )
    return {
        "url": url,
        "status": data.get("status"),
        "extracted": extracted,
        "source": "hyperx",
    }


# ---------------------------------------------------------------------------
# Day 41 — Web Read via Jina Reader (URL → clean markdown for LLM consumption)
#
# Why: existing http_get returns raw HTML (kotor: scripts, ads, nav noise).
# Jina Reader (https://jina.ai/reader, free tier 1M token/bln) returns
# LLM-friendly markdown — no auth needed for public URLs.
#
# Endpoint: https://r.jina.ai/<URL>
# Headers: "Accept: text/markdown" (default). Optional "X-No-Cache: true".
# ---------------------------------------------------------------------------
JINA_READER_BASE = "https://r.jina.ai/"
WEB_READ_MAX_CHARS = 30_000  # cap response — LLM context safety


async def _web_read(args: dict, ctx: ToolContext) -> dict:
    """Fetch a URL and return clean markdown via Jina Reader.

    Args:
      url: HTTPS URL to read.
      no_cache: bool (default False) — bypass Jina's CDN cache.
      max_chars: int (default 30000) — cap returned markdown length.

    Returns:
      {markdown, url, title?, source: "jina_reader", chars}
    """
    url = (args.get("url") or "").strip()
    if not url:
        raise ToolExecutionError("'url' is required")
    if not url.startswith(("http://", "https://")):
        raise ToolExecutionError("URL must start with http:// or https://")

    no_cache = bool(args.get("no_cache", False))
    max_chars = int(args.get("max_chars", WEB_READ_MAX_CHARS))
    max_chars = max(1000, min(max_chars, WEB_READ_MAX_CHARS))

    jina_url = JINA_READER_BASE + url
    headers = {
        "Accept": "text/markdown",
        "User-Agent": "MiganCore-WebRead/1.0 (https://migancore.com)",
    }
    if no_cache:
        headers["X-No-Cache"] = "true"

    logger.info("tool.web_read.start", url=url[:120], no_cache=no_cache)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.get(jina_url, headers=headers, follow_redirects=True)
    except httpx.TimeoutException:
        raise ToolExecutionError(f"web_read timed out (30s) for {url[:80]}")
    except httpx.HTTPError as exc:
        raise ToolExecutionError(f"web_read transport error: {exc}")

    if resp.status_code != 200:
        raise ToolExecutionError(
            f"Jina Reader HTTP {resp.status_code} for {url[:80]}: {resp.text[:200]}"
        )

    md = resp.text or ""
    truncated = False
    if len(md) > max_chars:
        md = md[:max_chars] + f"\n\n…[TRUNCATED at {max_chars} chars]"
        truncated = True

    # Try to pluck title from leading "Title:" line (Jina convention)
    title = None
    for line in md.splitlines()[:5]:
        if line.lower().startswith("title:"):
            title = line[6:].strip()
            break

    logger.info(
        "tool.web_read.done",
        url=url[:120],
        chars=len(md),
        truncated=truncated,
        title=title[:80] if title else None,
    )

    return {
        "markdown": md,
        "url": url,
        "title": title,
        "source": "jina_reader",
        "chars": len(md),
        "truncated": truncated,
    }


# ---------------------------------------------------------------------------
# Day 41 — Markdown → PDF via WeasyPrint (pure-Python, no Chromium)
#
# Why: user wants downloadable PDF output (research, reports). WeasyPrint
# v62 (Jan 2026) is mature pure-Python; no Puppeteer dependency.
# Returns base64 PDF inline (cap 5MB) so frontend can offer Download button.
# ---------------------------------------------------------------------------
EXPORT_PDF_MAX_BYTES = 5 * 1024 * 1024  # 5 MB cap


async def _export_pdf(args: dict, ctx: ToolContext) -> dict:
    """Render markdown to PDF (WeasyPrint).

    Args:
      markdown: required, the source markdown
      title: optional document title (set as <title> in HTML)
      page_size: "A4" (default) | "Letter"

    Returns:
      {pdf_base64, mime: "application/pdf", bytes, title}
    """
    markdown = (args.get("markdown") or "").strip()
    if not markdown:
        raise ToolExecutionError("'markdown' is required")
    title = (args.get("title") or "MiganCore Document").strip()[:200]
    page_size = (args.get("page_size") or "A4").upper()
    if page_size not in ("A4", "LETTER"):
        page_size = "A4"

    try:
        # Lazy import — WeasyPrint pulls heavy deps (cairo, pango, gdk-pixbuf)
        from weasyprint import HTML, CSS  # type: ignore
    except ImportError as exc:
        raise ToolExecutionError(
            "WeasyPrint not installed. Add 'weasyprint>=62' to requirements.txt and rebuild API container."
        ) from exc

    # Lightweight markdown → HTML conversion (use stdlib markdown if present)
    try:
        import markdown as md_lib  # type: ignore
        body_html = md_lib.markdown(
            markdown,
            extensions=["fenced_code", "tables", "toc", "nl2br"],
        )
    except ImportError:
        # Minimal fallback — wrap in <pre>
        body_html = f"<pre>{markdown}</pre>"

    # Use a sane default stylesheet
    css = CSS(string=f"""
      @page {{ size: {page_size}; margin: 2cm; }}
      body {{ font-family: -apple-system, "Segoe UI", Roboto, Inter, Arial, sans-serif; font-size: 11pt; line-height: 1.55; color: #1a1a1a; }}
      h1, h2, h3, h4 {{ color: #0d4c2e; margin-top: 1.2em; }}
      h1 {{ font-size: 22pt; border-bottom: 2px solid #2fe39a; padding-bottom: 4px; }}
      h2 {{ font-size: 17pt; }}
      h3 {{ font-size: 14pt; }}
      code, pre {{ font-family: "JetBrains Mono", Consolas, monospace; background: #f5f7f6; }}
      pre {{ padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 9.5pt; }}
      code {{ padding: 1px 4px; border-radius: 3px; font-size: 10pt; }}
      table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
      th, td {{ border: 1px solid #d4d4d4; padding: 6px 10px; text-align: left; }}
      th {{ background: #f0f4f1; }}
      blockquote {{ border-left: 3px solid #ff8a24; padding-left: 12px; color: #555; margin: 12px 0; }}
      a {{ color: #0066cc; text-decoration: none; }}
    """)

    full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body>{body_html}</body></html>"""

    logger.info("tool.export_pdf.start", title=title, md_chars=len(markdown), page=page_size)

    try:
        pdf_bytes = HTML(string=full_html).write_pdf(stylesheets=[css])
    except Exception as exc:
        raise ToolExecutionError(f"WeasyPrint render failed: {exc}") from exc

    if len(pdf_bytes) > EXPORT_PDF_MAX_BYTES:
        raise ToolExecutionError(
            f"PDF too large ({len(pdf_bytes)} bytes > {EXPORT_PDF_MAX_BYTES} cap). "
            "Trim the markdown or split into multiple documents."
        )

    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    logger.info("tool.export_pdf.done", title=title, bytes=len(pdf_bytes))

    return {
        "pdf_base64": pdf_b64,
        "mime": "application/pdf",
        "bytes": len(pdf_bytes),
        "title": title,
        "page_size": page_size,
        # Convenience for frontend download anchor
        "data_url": f"data:application/pdf;base64,{pdf_b64}",
    }


# ---------------------------------------------------------------------------
# Day 41 — Markdown → Slides via Marp CLI (PPTX/PDF/HTML)
#
# Why: user wants slide-deck output. Marp CLI v4.x (Feb 2026) accepts
# Markdown with `---` separator → renders to PPTX/PDF/HTML.
# Requires `marp-cli` installed in container; falls back to error if not.
# ---------------------------------------------------------------------------
EXPORT_SLIDES_MAX_BYTES = 8 * 1024 * 1024  # 8 MB cap (PPTX heavier than PDF)


async def _export_slides(args: dict, ctx: ToolContext) -> dict:
    """Render Marp-style markdown to PPTX or PDF slides.

    Args:
      markdown: required, slides separated by `---` lines (Marp syntax)
      format: "pptx" (default) | "pdf" | "html"
      theme: "default" (default) | "gaia" | "uncover"

    Returns:
      {file_base64, mime, bytes, format, slide_count, data_url}
    """
    import shutil
    import tempfile
    import subprocess

    markdown = (args.get("markdown") or "").strip()
    if not markdown:
        raise ToolExecutionError("'markdown' is required")
    fmt = (args.get("format") or "pptx").lower()
    if fmt not in ("pptx", "pdf", "html"):
        fmt = "pptx"
    theme = (args.get("theme") or "default").lower()
    if theme not in ("default", "gaia", "uncover"):
        theme = "default"

    marp_bin = shutil.which("marp") or shutil.which("marp-cli")
    if not marp_bin:
        raise ToolExecutionError(
            "marp-cli not installed in API container. Install via "
            "'npm install -g @marp-team/marp-cli' in the Dockerfile."
        )

    # Marp expects --- frontmatter for theme; prepend if absent
    if not markdown.startswith("---"):
        front = f"---\nmarp: true\ntheme: {theme}\n---\n\n"
        markdown = front + markdown

    # Count slide separators (simple heuristic)
    slide_count = max(1, markdown.count("\n---\n") + (1 if markdown.startswith("---") else 0))

    mime_map = {
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf":  "application/pdf",
        "html": "text/html",
    }

    logger.info("tool.export_slides.start", format=fmt, theme=theme, slides=slide_count, md_chars=len(markdown))

    with tempfile.TemporaryDirectory(prefix="marp_") as tmpdir:
        in_path = Path(tmpdir) / "deck.md"
        out_path = Path(tmpdir) / f"deck.{fmt}"
        in_path.write_text(markdown, encoding="utf-8")
        cmd = [marp_bin, str(in_path), "--allow-local-files", f"--{fmt}"]
        if fmt == "pptx":
            cmd.append("--pptx")
        try:
            proc = await asyncio.to_thread(
                subprocess.run, cmd,
                capture_output=True, text=True, timeout=60,
            )
        except subprocess.TimeoutExpired:
            raise ToolExecutionError("Marp render timed out (60s)")
        except Exception as exc:
            raise ToolExecutionError(f"Marp subprocess error: {exc}") from exc

        if proc.returncode != 0:
            raise ToolExecutionError(
                f"Marp render failed (rc={proc.returncode}): {proc.stderr[:300]}"
            )
        if not out_path.exists():
            raise ToolExecutionError(f"Marp produced no output file at {out_path}")
        file_bytes = out_path.read_bytes()

    if len(file_bytes) > EXPORT_SLIDES_MAX_BYTES:
        raise ToolExecutionError(
            f"Slides file too large ({len(file_bytes)} bytes > {EXPORT_SLIDES_MAX_BYTES} cap)"
        )

    file_b64 = base64.b64encode(file_bytes).decode("ascii")
    mime = mime_map[fmt]

    logger.info("tool.export_slides.done", format=fmt, bytes=len(file_bytes), slides=slide_count)

    return {
        "file_base64": file_b64,
        "mime": mime,
        "bytes": len(file_bytes),
        "format": fmt,
        "theme": theme,
        "slide_count": slide_count,
        "data_url": f"data:{mime};base64,{file_b64}",
    }


def _resolve_workspace_path(user_path: str) -> Path:
    """Resolve a user-supplied path relative to WORKSPACE_DIR.

    Prevents path traversal attacks by ensuring the resolved path stays
    within WORKSPACE_DIR. Raises ToolExecutionError for invalid paths.
    """
    workspace = Path(settings.WORKSPACE_DIR).resolve()
    # Strip leading slashes/dots to force relative interpretation
    clean = user_path.lstrip("/").lstrip(".")
    if not clean:
        raise ToolExecutionError("'path' must not be empty or root")

    target = (workspace / clean).resolve()

    # Strict containment check
    try:
        target.relative_to(workspace)
    except ValueError:
        raise ToolExecutionError(
            f"Path traversal blocked: '{user_path}' is outside workspace"
        )

    return target


async def _read_file(args: dict, ctx: ToolContext) -> dict:
    """Read a file from the agent's sandboxed workspace (/app/workspace/).

    Day 24: File system access for coding/agentic workflows.
    All paths are relative to WORKSPACE_DIR — no escaping the sandbox.
    Max file size: 50KB (larger files truncated with a notice).
    """
    user_path = args.get("path", "").strip()
    if not user_path:
        raise ToolExecutionError("'path' is required")

    try:
        target = _resolve_workspace_path(user_path)
    except ToolExecutionError:
        raise
    except Exception as exc:
        raise ToolExecutionError(f"Invalid path: {exc}") from exc

    if not target.exists():
        raise ToolExecutionError(f"File not found: {user_path}")
    if target.is_dir():
        # List directory contents instead
        entries = sorted(str(p.relative_to(target.parent)) for p in target.iterdir())
        return {
            "type": "directory",
            "path": user_path,
            "entries": entries[:100],
        }

    MAX_BYTES = 50_000
    try:
        raw = target.read_bytes()
        truncated = len(raw) > MAX_BYTES
        content = raw[:MAX_BYTES].decode("utf-8", errors="replace")

        logger.info("tool.read_file", path=user_path, size=len(raw), agent=ctx.agent_id)
        return {
            "content": content,
            "path": user_path,
            "size_bytes": len(raw),
            "truncated": truncated,
            "truncated_at": MAX_BYTES if truncated else None,
        }
    except Exception as exc:
        raise ToolExecutionError(f"Cannot read file: {exc}") from exc


async def _write_file(args: dict, ctx: ToolContext) -> dict:
    """Write content to a file in the agent's sandboxed workspace (/app/workspace/).

    Day 24: File system write for coding/agentic workflows.
    Creates parent directories automatically. Max content: 200KB.
    """
    user_path = args.get("path", "").strip()
    content = args.get("content", "")

    if not user_path:
        raise ToolExecutionError("'path' is required")
    if content is None:
        raise ToolExecutionError("'content' is required")

    MAX_CONTENT = 200_000
    if len(content) > MAX_CONTENT:
        raise ToolExecutionError(
            f"Content too large ({len(content)} chars). Max: {MAX_CONTENT} chars."
        )

    try:
        target = _resolve_workspace_path(user_path)
    except ToolExecutionError:
        raise
    except Exception as exc:
        raise ToolExecutionError(f"Invalid path: {exc}") from exc

    try:
        # Ensure workspace and parent dirs exist
        workspace = Path(settings.WORKSPACE_DIR)
        workspace.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(content, encoding="utf-8")
        logger.info("tool.write_file", path=user_path, size=len(content), agent=ctx.agent_id)

        return {
            "status": "written",
            "path": user_path,
            "size_bytes": len(content.encode("utf-8")),
        }
    except ToolExecutionError:
        raise
    except Exception as exc:
        raise ToolExecutionError(f"Cannot write file: {exc}") from exc


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

HandlerFn = Callable[[dict, ToolContext], Coroutine[Any, Any, dict]]

TOOL_REGISTRY: dict[str, HandlerFn] = {
    "web_search": _web_search,
    "memory_write": _memory_write,
    "memory_search": _memory_search,
    "python_repl": _python_repl,
    # Day 24 — Tool Expansion
    "generate_image": _generate_image,
    "read_file": _read_file,
    "write_file": _write_file,
    # Day 27 — TTS
    "text_to_speech": _text_to_speech,
    # Day 38 — Vision (multimodal)
    "analyze_image": _analyze_image,
    # Day 41 — Web read (Jina) + output (PDF, Slides)
    "web_read": _web_read,
    "export_pdf": _export_pdf,
    "export_slides": _export_slides,
    # Day 42 — HYPERX browser (user-built Node.js, anonymous, 7 search engines)
    "hyperx_get": _hyperx_get,
    "hyperx_search": _hyperx_search,
    "hyperx_scrape": _hyperx_scrape,
}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class ToolExecutor:
    """Dispatches tool calls to handlers. All errors are caught and returned.

    Day 11: Added policy enforcement layer before handler dispatch.
    """

    def __init__(self, ctx: ToolContext):
        self.ctx = ctx
        self._checker: ToolPolicyChecker | None = None
        if ctx.tool_policies is not None:
            self._checker = ToolPolicyChecker(
                tenant_plan=ctx.tenant_plan,
                tenant_id=ctx.tenant_id,
                tool_policies=ctx.tool_policies,
            )

    async def execute(self, skill_id: str, arguments: dict) -> dict:
        """Execute a tool and return {"result": ..., "error": ..., "success": bool}."""
        handler = TOOL_REGISTRY.get(skill_id)
        if not handler:
            logger.warning("tool.unknown", skill=skill_id)
            return {
                "result": None,
                "error": f"Unknown tool '{skill_id}'. Available: {list(TOOL_REGISTRY)}",
                "success": False,
            }

        # Day 11: Policy enforcement
        if self._checker is not None:
            try:
                await self._checker.check(skill_id)
            except PolicyViolation as exc:
                logger.warning(
                    "tool.policy_blocked",
                    skill=skill_id,
                    violation=exc.violation_type,
                    reason=exc.reason,
                    tenant=self.ctx.tenant_id,
                )
                return {
                    "result": None,
                    "error": f"Policy blocked: {exc.reason}",
                    "success": False,
                    "policy_violation": exc.violation_type,
                }

        try:
            result = await handler(arguments, self.ctx)
            return {"result": result, "error": None, "success": True}
        except ToolExecutionError as exc:
            logger.warning("tool.validation_error", skill=skill_id, error=str(exc))
            return {"result": None, "error": str(exc), "success": False}
        except Exception as exc:
            logger.error("tool.unexpected", skill=skill_id, error=str(exc))
            return {"result": None, "error": f"Unexpected error: {exc}", "success": False}


def build_ollama_tools_spec(skill_ids: list[str]) -> list[dict]:
    """Convert skill IDs to Ollama tool spec format (OpenAI-compatible).

    Reads schemas from skills.json. Skips unknown or non-MCP skills.
    """
    skills_cfg = load_skills_config()
    skill_map = {s["id"]: s for s in skills_cfg.get("skills", [])}

    tools = []
    for sid in skill_ids:
        skill = skill_map.get(sid)
        if not skill:
            continue
        if not skill.get("mcp_compatible", False):
            continue
        tools.append({
            "type": "function",
            "function": {
                "name": skill["id"],
                "description": skill["description"],
                "parameters": skill.get("schema", {"type": "object", "properties": {}}),
            },
        })
    return tools
