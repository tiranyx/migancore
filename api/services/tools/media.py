"""Media organ — image generation, image analysis, text-to-speech."""

import base64
import json
from typing import Any

import httpx
import structlog

from config import settings
from .base import ToolContext, ToolExecutionError

logger = structlog.get_logger()

FAL_FLUX_ENDPOINT = "https://fal.run/fal-ai/flux/schnell"
ELEVENLABS_TTS_ENDPOINT = "https://api.elevenlabs.io/v1/text-to-speech"
TTS_MAX_CHARS = 2500
TTS_MAX_AUDIO_BYTES = 2_000_000
FAL_VALID_SIZES = {
    "square_hd", "square", "portrait_4_3", "portrait_16_9",
    "landscape_4_3", "landscape_16_9",
}


async def _text_to_speech(args: dict, ctx: ToolContext) -> dict:
    """ElevenLabs TTS — returns base64 mp3 (capped at 2MB)."""
    text = args.get("text", "").strip()
    voice_id = args.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
    model_id = args.get("model_id", "eleven_flash_v2_5")

    if not text:
        raise ToolExecutionError("'text' is required")
    if len(text) > TTS_MAX_CHARS:
        text = text[:TTS_MAX_CHARS]

    api_key = settings.ELEVENLABS_KEY
    if not api_key:
        raise ToolExecutionError("ELEVENLABS_KEY not configured")

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.post(
                f"{ELEVENLABS_TTS_ENDPOINT}/{voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={"text": text, "model_id": model_id, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
            )
            resp.raise_for_status()
            audio_bytes = resp.content
    except Exception as exc:
        raise ToolExecutionError(f"TTS failed: {exc}") from exc

    if len(audio_bytes) > TTS_MAX_AUDIO_BYTES:
        raise ToolExecutionError(f"Audio too large: {len(audio_bytes)} bytes (max {TTS_MAX_AUDIO_BYTES})")

    b64 = base64.b64encode(audio_bytes).decode("ascii")
    logger.info("tool.tts", chars=len(text), audio_bytes=len(audio_bytes))
    return {"audio_base64": b64, "format": "mp3", "text_length": len(text), "voice_id": voice_id}


async def _generate_image(args: dict, ctx: ToolContext) -> dict:
    """fal.ai FLUX schnell image generation."""
    prompt = args.get("prompt", "").strip()
    size = args.get("size", "square_hd")
    if size not in FAL_VALID_SIZES:
        size = "square_hd"

    if not prompt:
        raise ToolExecutionError("'prompt' is required")

    api_key = settings.FAL_KEY
    if not api_key:
        raise ToolExecutionError("FAL_KEY not configured")

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            resp = await client.post(
                FAL_FLUX_ENDPOINT,
                headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"},
                json={"prompt": prompt, "image_size": size, "num_inference_steps": 4, "seed": args.get("seed")},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        raise ToolExecutionError(f"Image generation failed: {exc}") from exc

    images = data.get("images", [])
    if not images:
        raise ToolExecutionError("No image returned from fal.ai")

    url = images[0].get("url", "")
    logger.info("tool.generate_image", prompt=prompt[:60], size=size)
    return {"url": url, "prompt": prompt, "size": size, "width": images[0].get("width"), "height": images[0].get("height")}


async def _analyze_image(args: dict, ctx: ToolContext) -> dict:
    """Analyze an image via Gemini or Claude vision API."""
    image_url = args.get("image_url", "").strip()
    question = args.get("question", "Describe this image.").strip()

    if not image_url:
        raise ToolExecutionError("'image_url' is required")

    # Try Gemini first, fallback to Claude
    try:
        return await _analyze_via_gemini(image_url, question)
    except Exception:
        try:
            return await _analyze_via_claude(image_url, question)
        except Exception as exc:
            raise ToolExecutionError(f"Image analysis failed: {exc}") from exc


async def _analyze_via_gemini(image_url: str, question: str) -> dict:
    """Gemini Pro Vision analysis."""
    import asyncio
    key = settings.GEMINI_API_KEY
    if not key:
        raise ToolExecutionError("GEMINI_API_KEY not configured")

    # Fetch image bytes
    async with httpx.AsyncClient() as client:
        r = await client.get(image_url)
        r.raise_for_status()
        b64 = base64.b64encode(r.content).decode("ascii")
        mime = r.headers.get("content-type", "image/jpeg")

    payload = {
        "contents": [{
            "parts": [
                {"text": question},
                {"inline_data": {"mime_type": mime, "data": b64}}
            ]
        }]
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return {"analysis": text, "model": "gemini-1.5-flash", "question": question}


async def _analyze_via_claude(image_url: str, question: str) -> dict:
    """Claude vision analysis."""
    key = settings.ANTHROPIC_API_KEY
    if not key:
        raise ToolExecutionError("ANTHROPIC_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        r = await client.get(image_url)
        r.raise_for_status()
        b64 = base64.b64encode(r.content).decode("ascii")
        mime = r.headers.get("content-type", "image/jpeg")

    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}}
            ]
        }]
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    text = data["content"][0]["text"]
    return {"analysis": text, "model": "claude-3-haiku", "question": question}


HANDLERS: dict[str, Any] = {
    "text_to_speech": _text_to_speech,
    "generate_image": _generate_image,
    "analyze_image": _analyze_image,
}
