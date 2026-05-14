"""
Teacher API wrappers — Day 28 distillation pipeline.

Unified async interface to 4 LLM providers used as "teachers" for MiganCore-7B
distillation. Each wrapper exposes the same `complete(prompt, system, max_tokens)`
signature returning (text, input_tokens, output_tokens, est_cost_usd).

Providers:
  - Anthropic Claude (sonnet 4.5) — best quality, used as JUDGE primarily
  - Moonshot Kimi K2 — cheapest bilingual ID/EN, primary TEACHER
  - OpenAI GPT-4o — alternative teacher
  - Google Gemini 2.5 Flash — cheapest, alternative teacher

Pricing (May 2026, official pages, $/1M tokens):
  Claude Sonnet 4.5  : $3 in / $15 out
  GPT-4o             : $2.50 in / $10 out
  Kimi K2            : $0.60 in / $2.50 out  (cheapest bilingual)
  Gemini 2.5 Flash   : $0.075 in / $0.30 out (cheapest overall)

All wrappers:
  - httpx.AsyncClient with 60s timeout
  - Retry x3 with exponential backoff on 429/5xx
  - Return est_cost_usd for budget tracking
  - Raise TeacherError on hard failures
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class TeacherError(Exception):
    """Raised when a teacher API call fails after retries."""


class TeacherHealthMonitor:
    """Circuit-breaker style health monitor for teacher APIs.

    Tracks consecutive failures per teacher. After threshold failures,
    the teacher is banned for a cooldown period. Success resets the counter.
    """

    def __init__(self, failure_threshold: int = 3, cooldown_minutes: int = 30):
        self.failures: dict[str, int] = {}
        self.banned_until: dict[str, datetime] = {}
        self.threshold = failure_threshold
        self.cooldown = timedelta(minutes=cooldown_minutes)

    def record_failure(self, teacher: str) -> None:
        self.failures[teacher] = self.failures.get(teacher, 0) + 1
        if self.failures[teacher] >= self.threshold:
            self.banned_until[teacher] = datetime.utcnow() + self.cooldown
            self.failures[teacher] = 0
            logger.warning("teacher.banned", teacher=teacher, cooldown_minutes=30)

    def record_success(self, teacher: str) -> None:
        if self.failures.get(teacher):
            self.failures[teacher] = 0

    def is_healthy(self, teacher: str) -> bool:
        until = self.banned_until.get(teacher)
        if until and datetime.utcnow() < until:
            return False
        if until and datetime.utcnow() >= until:
            del self.banned_until[teacher]
        return True


# Global singleton — shared across all callers
health_monitor = TeacherHealthMonitor()


@dataclass
class TeacherResponse:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    provider: str
    model: str


# Pricing table ($/1M tokens) — single source of truth
PRICING = {
    "anthropic/claude-sonnet-4-5": {"in": 3.00, "out": 15.00},
    "anthropic/claude-haiku-4-5":  {"in": 1.00, "out": 5.00},
    "openai/gpt-4o":               {"in": 2.50, "out": 10.00},
    "openai/gpt-4o-mini":          {"in": 0.15, "out": 0.60},
    # Moonshot Kimi pricing (May 2026, official): K2 series ~$0.60/$2.50 per M tokens
    "moonshot/kimi-k2.6":          {"in": 0.60, "out": 2.50},
    "moonshot/kimi-k2.5":          {"in": 0.60, "out": 2.50},
    "moonshot/moonshot-v1-8k":     {"in": 0.30, "out": 1.20},
    "moonshot/moonshot-v1-32k":    {"in": 0.40, "out": 1.60},
    "moonshot/moonshot-v1-128k":   {"in": 0.60, "out": 2.50},
    "google/gemini-2.5-flash":     {"in": 0.075, "out": 0.30},
}


def _cost(model_key: str, in_tok: int, out_tok: int) -> float:
    p = PRICING.get(model_key)
    if not p:
        return 0.0
    return (in_tok / 1_000_000) * p["in"] + (out_tok / 1_000_000) * p["out"]


# ---------------------------------------------------------------------------
# Anthropic Claude
# ---------------------------------------------------------------------------
async def call_claude(
    prompt: str,
    system: str = "",
    max_tokens: int = 600,
    model: str = "claude-sonnet-4-5",
) -> TeacherResponse:
    if not settings.ANTHROPIC_API_KEY:
        raise TeacherError("ANTHROPIC_API_KEY not set")

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system

    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(3):
            try:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    json=payload, headers=headers,
                )
                if resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code != 200:
                    raise TeacherError(f"Claude HTTP {resp.status_code}: {resp.text[:200]}")
                data = resp.json()
                text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
                in_tok = data["usage"]["input_tokens"]
                out_tok = data["usage"]["output_tokens"]
                return TeacherResponse(
                    text=text,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cost_usd=_cost(f"anthropic/{model}", in_tok, out_tok),
                    provider="anthropic",
                    model=model,
                )
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise TeacherError(f"Claude failed after 3 retries: {exc}")
                await asyncio.sleep(2 ** attempt)
    raise TeacherError("Claude unreachable")


# ---------------------------------------------------------------------------
# Moonshot Kimi K2 (OpenAI-compatible API)
# ---------------------------------------------------------------------------
async def call_kimi(
    prompt: str,
    system: str = "",
    max_tokens: int = 600,
    model: str = "kimi-k2.6",  # latest stable K2 series; alternatives: kimi-k2.5, moonshot-v1-32k
) -> TeacherResponse:
    if not settings.KIMI_API_KEY:
        raise TeacherError("KIMI_API_KEY not set")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # Kimi K2 series quirks (per platform.kimi.ai/docs):
    # - With thinking ENABLED (default): temperature must be 1.0
    # - With thinking DISABLED: temperature must be 0.6 (back to standard mode)
    # - Output split: reasoning_content (chain-of-thought) + content (final answer)
    # For distillation we disable thinking: cheaper, faster, content-only response
    is_k2 = model.startswith("kimi-k2")
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.6}
    if is_k2:
        payload["thinking"] = {"type": "disabled"}
    headers = {
        "Authorization": f"Bearer {settings.KIMI_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(3):
            try:
                resp = await client.post(
                    "https://api.moonshot.ai/v1/chat/completions",
                    json=payload, headers=headers,
                )
                if resp.status_code == 429:
                    # Lesson #186: 429 can mean "insufficient balance" — fatal, not retryable
                    body = resp.text.lower()
                    if "insufficient balance" in body or "credit" in body or "suspended" in body:
                        raise TeacherError(f"Kimi suspended (insufficient balance): {resp.text[:200]}")
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code != 200:
                    raise TeacherError(f"Kimi HTTP {resp.status_code}: {resp.text[:200]}")
                data = resp.json()
                msg = data["choices"][0]["message"]
                # K2 thinking models split: content (final) + reasoning_content (chain-of-thought)
                # If thinking is enabled and max_tokens too low, content may be empty.
                text = (msg.get("content") or "").strip()
                if not text:
                    text = (msg.get("reasoning_content") or "").strip()
                in_tok = data["usage"]["prompt_tokens"]
                out_tok = data["usage"]["completion_tokens"]
                return TeacherResponse(
                    text=text,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cost_usd=_cost(f"moonshot/{model}", in_tok, out_tok),
                    provider="moonshot",
                    model=model,
                )
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise TeacherError(f"Kimi failed after 3 retries: {exc}")
                await asyncio.sleep(2 ** attempt)
    raise TeacherError("Kimi unreachable")


# ---------------------------------------------------------------------------
# OpenAI GPT-4o
# ---------------------------------------------------------------------------
async def call_gpt(
    prompt: str,
    system: str = "",
    max_tokens: int = 600,
    model: str = "gpt-4o",
) -> TeacherResponse:
    if not settings.OPENAI_API_KEY:
        raise TeacherError("OPENAI_API_KEY not set")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.6}
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(3):
            try:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload, headers=headers,
                )
                if resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code != 200:
                    raise TeacherError(f"OpenAI HTTP {resp.status_code}: {resp.text[:200]}")
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                in_tok = data["usage"]["prompt_tokens"]
                out_tok = data["usage"]["completion_tokens"]
                return TeacherResponse(
                    text=text,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cost_usd=_cost(f"openai/{model}", in_tok, out_tok),
                    provider="openai",
                    model=model,
                )
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise TeacherError(f"OpenAI failed after 3 retries: {exc}")
                await asyncio.sleep(2 ** attempt)
    raise TeacherError("OpenAI unreachable")


# ---------------------------------------------------------------------------
# Google Gemini 2.5 Flash
# ---------------------------------------------------------------------------
async def call_gemini(
    prompt: str,
    system: str = "",
    max_tokens: int = 600,
    model: str = "gemini-2.5-flash",
) -> TeacherResponse:
    if not settings.GEMINI_API_KEY:
        raise TeacherError("GEMINI_API_KEY not set")

    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    payload = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max(256, max_tokens),  # Gemini 2.5 Flash truncates if too low
            "temperature": 0.6,
            "topP": 0.95,
        },
        # Disable safety filters that might block legit responses
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
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    gemini_headers = {"x-goog-api-key": settings.GEMINI_API_KEY}

    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(3):
            try:
                resp = await client.post(url, json=payload, headers=gemini_headers)
                if resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code != 200:
                    raise TeacherError(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")
                data = resp.json()
                cands = data.get("candidates", [])
                if not cands:
                    raise TeacherError(f"Gemini no candidates: {data}")
                cand0 = cands[0]
                # Gemini 2.5 sometimes returns finishReason without content (safety / MAX_TOKENS)
                finish = cand0.get("finishReason", "")
                parts = cand0.get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                if not text and finish:
                    raise TeacherError(f"Gemini empty response, finishReason={finish}")
                usage = data.get("usageMetadata", {})
                in_tok = usage.get("promptTokenCount", 0)
                out_tok = usage.get("candidatesTokenCount", 0)
                return TeacherResponse(
                    text=text,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cost_usd=_cost(f"google/{model}", in_tok, out_tok),
                    provider="google",
                    model=model,
                )
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise TeacherError(f"Gemini failed after 3 retries: {exc}")
                await asyncio.sleep(2 ** attempt)
    raise TeacherError("Gemini unreachable")


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------
TEACHER_REGISTRY = {
    "claude": call_claude,
    "kimi": call_kimi,
    "gpt": call_gpt,
    "gemini": call_gemini,
}


async def call_teacher(
    teacher: str, prompt: str, system: str = "", max_tokens: int = 600
) -> TeacherResponse:
    """Generic dispatch: call_teacher('kimi', prompt, system, 600)

    M1.4: Health-check gate — skips teachers that are circuit-broken.
    """
    if not health_monitor.is_healthy(teacher):
        raise TeacherError(f"Teacher {teacher} is temporarily unhealthy (circuit open)")
    fn = TEACHER_REGISTRY.get(teacher)
    if not fn:
        raise TeacherError(f"Unknown teacher: {teacher}. Available: {list(TEACHER_REGISTRY)}")
    try:
        resp = await fn(prompt, system, max_tokens)
        health_monitor.record_success(teacher)
        return resp
    except TeacherError:
        health_monitor.record_failure(teacher)
        raise


def is_teacher_available(teacher: str) -> bool:
    """Quick check: is API key configured for this teacher?"""
    keys = {
        "claude": settings.ANTHROPIC_API_KEY,
        "kimi": settings.KIMI_API_KEY if settings.KIMI_ENABLED else None,
        "gpt": settings.OPENAI_API_KEY,
        "gemini": settings.GEMINI_API_KEY,
    }
    return bool(keys.get(teacher))


def list_available_teachers() -> list[str]:
    """Return teachers that have API keys configured AND are healthy."""
    return [
        t for t in TEACHER_REGISTRY
        if is_teacher_available(t) and health_monitor.is_healthy(t)
    ]
# =============================================================================
# OpenRouter — Day 73 Sprint 1.5: multi-source teacher diversity (Tabayyun)
# =============================================================================
# Free models via OpenRouter (no payment needed):
#   meta-llama/llama-3.3-70b-instruct:free   — strong open-source
#   meta-llama/llama-3.1-70b-instruct:free   — older variant
#   google/gemma-2-9b-it:free                — fast Google model
#   mistralai/mistral-7b-instruct:free       — efficient EU model
#   qwen/qwen-2.5-7b-instruct:free           — Chinese/Indonesian friendly
#
# Tabayyun principle (multi-source verify): rotate teachers per distillation
# round → broader consensus, less bias from any single perspective.

OPENROUTER_FREE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.1-70b-instruct:free",
    "google/gemma-2-9b-it:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
]


async def call_openrouter(
    prompt: str,
    system: str = "",
    max_tokens: int = 600,
    model: str = "meta-llama/llama-3.3-70b-instruct:free",
) -> TeacherResponse:
    """OpenRouter unified API — access to 50+ models including free tier."""
    api_key = getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise TeacherError("OPENROUTER_API_KEY not set")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://api.migancore.com",
        "X-Title": "MiganCore Distillation",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.6,
    }

    url = "https://openrouter.ai/api/v1/chat/completions"
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(3):
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code != 200:
                    raise TeacherError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:200]}")
                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise TeacherError(f"OpenRouter no choices: {data}")
                text = choices[0].get("message", {}).get("content", "")
                if not text:
                    finish = choices[0].get("finish_reason", "")
                    raise TeacherError(f"OpenRouter empty response, finish={finish}")
                usage = data.get("usage", {})
                in_tok = usage.get("prompt_tokens", 0)
                out_tok = usage.get("completion_tokens", 0)
                model_label = model.split('/')[-1].replace(':free', '')
                return TeacherResponse(
                    text=text,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    est_cost_usd=0.0,
                    teacher=f"openrouter:{model_label}",
                )
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise TeacherError(f"OpenRouter network: {exc}")
                await asyncio.sleep(2 ** attempt)
    raise TeacherError("OpenRouter: exhausted retries")


# Convenience shortcuts per free model
async def call_llama33(prompt: str, system: str = "", max_tokens: int = 600) -> TeacherResponse:
    return await call_openrouter(prompt, system, max_tokens,
                                 model="meta-llama/llama-3.3-70b-instruct:free")


async def call_gemma2(prompt: str, system: str = "", max_tokens: int = 600) -> TeacherResponse:
    return await call_openrouter(prompt, system, max_tokens,
                                 model="google/gemma-2-9b-it:free")


async def call_qwen25(prompt: str, system: str = "", max_tokens: int = 600) -> TeacherResponse:
    return await call_openrouter(prompt, system, max_tokens,
                                 model="qwen/qwen-2.5-7b-instruct:free")


async def call_mistral7b(prompt: str, system: str = "", max_tokens: int = 600) -> TeacherResponse:
    return await call_openrouter(prompt, system, max_tokens,
                                 model="mistralai/mistral-7b-instruct:free")


TEACHER_REGISTRY.update({
    "llama33":   call_llama33,
    "gemma2":    call_gemma2,
    "qwen25":    call_qwen25,
    "mistral7b": call_mistral7b,
})


_original_is_teacher_available = is_teacher_available


def is_teacher_available(teacher: str) -> bool:  # noqa: F811
    """Extended availability check — OpenRouter teachers share one API key."""
    if teacher in ("llama33", "gemma2", "qwen25", "mistral7b"):
        api_key = getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY", "")
        return bool(api_key)
    return _original_is_teacher_available(teacher)
