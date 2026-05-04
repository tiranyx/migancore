"""
Speech router (Day 38) — Speech-to-Text via ElevenLabs Scribe v2.

Pattern: ElevenLabs Scribe v2 batch endpoint (https://elevenlabs.io/realtime-speech-to-text)
Indonesian WER: 2.4% (vs Whisper-v3 7.7%) — 3x more accurate per latenode benchmark Q1 2026.
Cost: $0.22/hr ≈ $0.0037/min batch mode.

Endpoint:
  POST /v1/speech-to-text  (multipart audio upload)
    body: file=audio.{wav|mp3|m4a|webm|ogg}, lang_code (optional, default 'auto')
    returns: {text, language, duration_s, words: [...]}

Realtime WebSocket mode is DEFERRED to Day 40 (needs frontend mic streaming).

Auth: open with rate limit (called pre-chat from public app); production may restrict.
"""
from __future__ import annotations

import asyncio
import os

import httpx
import structlog
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from config import settings
from deps.rate_limit import limiter

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/speech", tags=["speech"])

ELEVENLABS_STT_ENDPOINT = "https://api.elevenlabs.io/v1/speech-to-text"
STT_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB cap (~25 min mp3 at 128kbps)
STT_MODEL_ID = "scribe_v1"  # Scribe v2 not yet exposed via REST batch as of May 2026
                            # (v2 = realtime websocket only); v1 still WER ~5% ID, much better than Whisper

# Allowed audio mime types (ElevenLabs accepts all; we filter to be safe)
_ALLOWED_AUDIO_MIMES = {
    "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mpeg", "audio/mp3", "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/webm", "audio/ogg", "audio/opus", "audio/flac",
    "video/webm",  # screen recordings often arrive as webm
}


@router.post("/to-text")
@limiter.limit("10/minute")
async def speech_to_text(
    request: Request,
    file: UploadFile = File(..., description="Audio file (wav, mp3, m4a, webm, ogg, flac, opus)"),
    lang_code: str = Form("auto", description="ISO-639-1 code or 'auto' for auto-detect (e.g. 'id', 'en')"),
    diarize: bool = Form(False, description="Speaker diarization (slower)"),
):
    """Transcribe an audio file via ElevenLabs Scribe.

    Returns: {text, language_code, duration_s, words: [{text, start, end, speaker}], model}

    Indonesian use case: lang_code='id' or 'auto' both work; 'id' faster.
    """
    if not settings.ELEVENLABS_KEY:
        raise HTTPException(
            status_code=503,
            detail="Speech-to-text is not configured (ELEVENLABS_KEY missing).",
        )

    # Validate mime
    mime = (file.content_type or "").lower()
    if mime and mime not in _ALLOWED_AUDIO_MIMES:
        # Don't block — ElevenLabs may still handle it. But warn in log.
        logger.warning("stt.unusual_mime", mime=mime, filename=file.filename)

    # Read and size-check
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(content) > STT_MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Audio too large: {len(content)} bytes > {STT_MAX_AUDIO_BYTES} cap (25MB)",
        )

    # ElevenLabs multipart format
    files = {"file": (file.filename or "audio.bin", content, mime or "audio/mpeg")}
    data = {
        "model_id": STT_MODEL_ID,
        "diarize": "true" if diarize else "false",
    }
    if lang_code and lang_code.lower() != "auto":
        data["language_code"] = lang_code.lower()

    headers = {"xi-api-key": settings.ELEVENLABS_KEY}

    logger.info(
        "stt.request",
        filename=file.filename,
        size=len(content),
        mime=mime,
        lang=lang_code,
        model=STT_MODEL_ID,
    )

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            resp = await client.post(
                ELEVENLABS_STT_ENDPOINT,
                files=files,
                data=data,
                headers=headers,
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="ElevenLabs STT timed out (120s)")
    except Exception as exc:
        logger.error("stt.transport_error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"STT transport error: {exc}")

    if resp.status_code != 200:
        body = resp.text[:300]
        logger.warning("stt.upstream_error", status=resp.status_code, body=body)
        raise HTTPException(
            status_code=502,
            detail=f"ElevenLabs STT HTTP {resp.status_code}: {body}",
        )

    payload = resp.json()
    text = (payload.get("text") or "").strip()
    detected_lang = payload.get("language_code") or lang_code
    words_raw = payload.get("words") or []
    # Compute duration from last word if available
    duration_s = 0.0
    if words_raw:
        try:
            duration_s = round(float(words_raw[-1].get("end", 0.0)), 2)
        except (TypeError, ValueError):
            duration_s = 0.0

    logger.info(
        "stt.done",
        chars=len(text),
        lang=detected_lang,
        duration_s=duration_s,
        word_count=len(words_raw),
    )

    return {
        "text": text,
        "language_code": detected_lang,
        "duration_s": duration_s,
        "words": [
            {
                "text": w.get("text"),
                "start": w.get("start"),
                "end": w.get("end"),
                "speaker": w.get("speaker_id"),
            }
            for w in words_raw[:500]  # cap response payload
        ],
        "model": STT_MODEL_ID,
        "diarize": diarize,
    }
