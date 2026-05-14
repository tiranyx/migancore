"""
Voice Tone Analysis — Sprint 2 Day 75

Migan "merasakan" emosi Fahmi dari audio input.
After STT transcript, send to Gemini for sentiment+energy classification.
Save inferred emotion to `qalb` bucket (heart/emotional resonance).

Vision tags:
- qalb (heart, emotional resonance)
- INDERA active (sensory perception)
- Adaptive Design (NOT every audio analyze — only meaningful)

API:
  POST /v1/voice/analyze  — given transcript (or audio + STT first), return emotion read

Hook: chat.html mic input → POST /v1/speech-to-text → POST /v1/voice/analyze
"""
from __future__ import annotations

import time
from typing import Optional

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config import settings
from deps.auth import get_current_user
from models.user import User

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/voice", tags=["voice-tone"])

# Adaptive trigger: skip analysis if too short (per Adaptive Doctrine — no blanket)
MIN_TRANSCRIPT_CHARS = 12  # below this = casual one-word, skip


class VoiceAnalyzeRequest(BaseModel):
    transcript: str = Field(..., min_length=1, max_length=4000)
    save_to_qalb: bool = True
    context_hint: Optional[str] = Field(None, max_length=200,
        description="Optional context (e.g. 'chat onboarding', 'feedback')")


class VoiceAnalyzeResponse(BaseModel):
    skipped: bool = False
    reason: Optional[str] = None
    sentiment: Optional[str] = None  # positive | neutral | negative | mixed
    energy: Optional[str] = None     # low | medium | high
    emotion: Optional[str] = None    # 1-3 emotion labels: senang/marah/lelah/excited/etc
    intent_hint: Optional[str] = None  # casual | task | question | venting | celebration
    qalb_saved: bool = False
    qalb_key: Optional[str] = None


SYSTEM_PROMPT = """Kamu analyzer emosi dari teks transkrip suara. Output STRICT JSON:
{
  "sentiment": "positive" | "neutral" | "negative" | "mixed",
  "energy": "low" | "medium" | "high",
  "emotion": "1-3 emotion labels comma-sep (senang, lelah, frustrasi, excited, marah, tenang, bingung, sedih, antusias)",
  "intent_hint": "casual" | "task" | "question" | "venting" | "celebration"
}

JANGAN tambah komentar/markdown. Hanya JSON valid.
Pertimbangkan: word choice, exclamation, capitalization, repetition, sentence rhythm."""


async def call_gemini_sentiment(transcript: str) -> dict:
    """Call Gemini for fast sentiment classification (cheap)."""
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not set")

    payload = {
        "contents": [{"role": "user", "parts": [{"text": transcript}]}],
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 512,  # Day 75: raised from 200 — Gemini 2.5 Flash truncates mid-JSON at low cap
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},  # disable thinking to avoid token drain (Lesson #99)
        },
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
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"x-goog-api-key": settings.GEMINI_API_KEY}

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            logger.warning("voice.gemini_http", status=r.status_code, body=r.text[:200])
            raise HTTPException(status_code=502, detail=f"Gemini HTTP {r.status_code}")
        data = r.json()
        cands = data.get("candidates", [])
        if not cands:
            raise HTTPException(status_code=502, detail="Gemini returned no candidates")
        text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []))
        if not text:
            raise HTTPException(status_code=502, detail="Gemini empty response")

        import json as _json
        try:
            parsed = _json.loads(text)
            return parsed
        except Exception:
            pass
        # Strip markdown fence
        cleaned = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return _json.loads(cleaned)
        except Exception:
            pass
        # Last-resort regex extract first valid JSON object
        import re
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            try:
                return _json.loads(match.group(0))
            except Exception:
                pass
        logger.warning("voice.json_parse_fail", raw=text[:300])
        # Heuristic fallback — return neutral if all parsing failed
        return {"sentiment": "neutral", "energy": "medium", "emotion": "unclear",
                "intent_hint": "casual"}


@router.post("/analyze", response_model=VoiceAnalyzeResponse)
async def analyze_tone(
    body: VoiceAnalyzeRequest,
    current_user: User = Depends(get_current_user),
):
    """Analyze emotional tone from voice transcript. Adaptive: skip if too trivial."""
    transcript = body.transcript.strip()

    # Adaptive trigger
    if len(transcript) < MIN_TRANSCRIPT_CHARS:
        return VoiceAnalyzeResponse(
            skipped=True,
            reason=f"transcript too short (<{MIN_TRANSCRIPT_CHARS} chars) — skip per adaptive doctrine",
        )

    started = time.time()
    try:
        result = await call_gemini_sentiment(transcript)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("voice.analyze_fail", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {exc}")

    elapsed_ms = int((time.time() - started) * 1000)

    sentiment = result.get("sentiment", "neutral")
    energy = result.get("energy", "medium")
    emotion = result.get("emotion", "")
    intent_hint = result.get("intent_hint", "casual")

    # Adaptive save to qalb bucket — only if user is creator OR sentiment is strong
    qalb_saved = False
    qalb_key = None
    is_creator = getattr(current_user, "is_creator", False)
    is_strong_signal = (sentiment in ("negative", "positive") and energy in ("low", "high"))

    if body.save_to_qalb and (is_creator or is_strong_signal):
        try:
            from services.memory import memory_write as kv_write
            qalb_key = f"voice_tone_{int(time.time())}"
            summary = (
                f"[Voice tone — {sentiment}/{energy}/{emotion}]\n"
                f"Intent: {intent_hint}\n"
                f"Transcript preview: {transcript[:200]}\n"
                f"Context: {body.context_hint or '(none)'}"
            )
            await kv_write(
                tenant_id=str(getattr(current_user, "tenant_id", "")),
                agent_id="cb3ebd3b-4c31-4af7-8470-25c2011c0974",  # core_brain
                key=qalb_key,
                value=summary,
                namespace="qalb",
                ttl_days=60,
            )
            qalb_saved = True
            logger.info("voice.qalb_saved", key=qalb_key, sentiment=sentiment, energy=energy)
        except Exception as exc:
            logger.warning("voice.qalb_save_fail", error=str(exc))

    logger.info(
        "voice.analyzed",
        sentiment=sentiment, energy=energy, emotion=emotion,
        intent=intent_hint, elapsed_ms=elapsed_ms,
        creator=is_creator, qalb_saved=qalb_saved,
    )

    return VoiceAnalyzeResponse(
        skipped=False,
        sentiment=sentiment,
        energy=energy,
        emotion=emotion,
        intent_hint=intent_hint,
        qalb_saved=qalb_saved,
        qalb_key=qalb_key,
    )


@router.get("/qalb/recent")
async def list_qalb_recent(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
):
    """Read recent qalb entries — Migan's emotional log of conversations with user."""
    from services.memory import memory_list

    entries = await memory_list(
        tenant_id=str(getattr(current_user, "tenant_id", "")),
        agent_id="cb3ebd3b-4c31-4af7-8470-25c2011c0974",
        namespace="qalb",
        limit=100,
    )
    items = []
    for k, v in entries.items():
        if k.startswith("voice_tone_"):
            try:
                ts = int(k.split("_")[2])
            except (IndexError, ValueError):
                continue
            items.append({"key": k, "timestamp": ts, "content": v})
    items.sort(key=lambda x: -x["timestamp"])
    return {"count": len(items), "items": items[:limit]}
