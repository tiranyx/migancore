"""
Day 53 — llama-server OpenAI-compatible client (speculative decoding).

Bridges the API container to a llama.cpp `llama-server` container running with
a small DRAFT model (Qwen 0.5B) speculating tokens for the larger TARGET model
(Qwen 7B-instruct-q4_K_M). When draft predictions are accepted, the target
model verifies them in parallel — net effect 1.5-2x sustained throughput on
8-vCPU machines per r/LocalLLaMA Q1 2026 benchmarks.

Vision compass (`docs/VISION_PRINCIPLES_LOCKED.md`):
  - Principle 1 ✅ Standing alone — 100% local, no third-party API in the path
  - Principle 2 ✅ Mentor not responder — N/A (Migan responds via own model)
  - Principle 3 ✅ Long-term own model — Qwen we own + llama.cpp open-source
  - Principle 4 ✅ Closed loop preserved — doesn't break DPO flywheel
  - Principle 5 ✅ Speed problem solved with BETTER LOCAL MODEL not wrapper

Why bypass Ollama:
  Ollama 0.22.1 + 0.23.1 have NO native speculative decoding (PR #8134 closed
  unmerged April 2025, issue #5800 open since Q2 2025). llama-server has had it
  since 2024 via `--spec-draft-model` + `--spec-draft-n-max`. Two-tier setup:
    - Ollama  = model lifecycle / registry / tool-calling
    - llama-server = inference engine for token-streaming hot path

Telemetry hook:
  llama-server's OpenAI-compat response embeds `timings.draft_n` and
  `timings.accepted_n` (when speculative is active). We surface these as
  observability fields so we can log acceptance rate per request and tune
  `--spec-draft-n-max` empirically (KPI ≥70% on real workload).
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from typing import Any

import httpx

# Default URL — points at the llama-server container on the ado_network.
# Override via env LLAMASERVER_URL=http://llamaserver:8080
LLAMASERVER_URL = os.environ.get("LLAMASERVER_URL", "http://llamaserver:8080")

# Same timeout philosophy as OllamaClient — 7B + speculation can take longer
# on a busy CPU even though throughput is higher per token.
DEFAULT_TIMEOUT = httpx.Timeout(180.0, connect=5.0, read=180.0)  # Day 71c: bumped 90->180 after enabling 29 tools (Lesson #179)
STREAM_TIMEOUT = httpx.Timeout(None, connect=5.0, read=60.0)


class LlamaServerError(Exception):
    """Raised when llama-server returns an error or cannot be reached."""
    pass


def _to_openai_messages(messages: list[dict]) -> list[dict]:
    """Strip Ollama-only message fields the OpenAI schema doesn't accept.

    Ollama allows `images=[...]` on user messages. llama-server's OpenAI
    endpoint handles vision via a different shape (`content=[{type:image_url}]`).
    For Day 53 scope (text only — tools still on Ollama), we strip extras.
    """
    cleaned: list[dict] = []
    for m in messages:
        c = {"role": m["role"]}
        # Content may be string or list-of-parts; pass through either way.
        if "content" in m and m["content"] is not None:
            c["content"] = m["content"]
        else:
            c["content"] = ""
        # Tool messages must include the tool's response content.
        if m.get("role") == "tool" and "name" in m:
            c["name"] = m["name"]
        cleaned.append(c)
    return cleaned


class LlamaServerClient:
    """Async HTTP client for llama.cpp's OpenAI-compatible endpoint."""

    def __init__(self, base_url: str | None = None, timeout: httpx.Timeout | None = None):
        self.base_url = (base_url or LLAMASERVER_URL).rstrip("/")
        self.timeout = timeout or DEFAULT_TIMEOUT
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "LlamaServerClient":
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
        self._client = None

    def _client_or_raise(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("LlamaServerClient not entered. Use 'async with'.")
        return self._client

    async def health(self) -> bool:
        """Cheap liveness probe — returns True if /health says ok."""
        try:
            r = await self._client_or_raise().get(f"{self.base_url}/health", timeout=2.0)
            return r.status_code == 200 and (r.json() or {}).get("status") == "ok"
        except Exception:
            return False

    async def chat(
        self,
        messages: list[dict],
        max_tokens: int = 512,
        temperature: float = 0.2,
        model: str = "qwen",  # llama-server ignores `model`; we set what we loaded
    ) -> dict:
        """Non-streaming chat completion — returns full OpenAI response dict."""
        payload = {
            "model": model,
            "messages": _to_openai_messages(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        try:
            resp = await self._client_or_raise().post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                raise LlamaServerError(f"llama-server error: {data['error']}")
            return data
        except httpx.TimeoutException as exc:
            raise LlamaServerError(
                f"llama-server timed out after {self.timeout}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LlamaServerError(
                f"llama-server HTTP error: {exc.response.status_code}"
            ) from exc
        except httpx.ConnectError as exc:
            raise LlamaServerError(
                f"Cannot connect to llama-server at {self.base_url}"
            ) from exc

    async def chat_stream(
        self,
        model: str,  # accepted for OllamaClient signature parity; llama-server uses loaded model
        messages: list[dict],
        options: dict | None = None,
    ) -> AsyncGenerator[tuple[str, bool], None]:
        """Stream chat completion — yields (chunk, done) like OllamaClient.chat_stream.

        Drop-in replacement signature so chat.py can swap clients without
        further changes. Uses OpenAI SSE format (`data: {...}\\n\\n` ending
        with `data: [DONE]`).

        `options` accepts a subset:
          - num_predict  -> max_tokens
          - temperature  -> temperature (default 0.7)
          - num_ctx      -> ignored (set at server boot via --ctx-size)
        """
        opts = options or {}
        payload = {
            "model": model or "qwen",
            "messages": _to_openai_messages(messages),
            "max_tokens": int(opts.get("num_predict", 512)),
            "temperature": float(opts.get("temperature", 0.7)),
            "stream": True,
        }

        streaming_client = httpx.AsyncClient(timeout=STREAM_TIMEOUT)
        try:
            async with streaming_client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    # OpenAI SSE format: "data: {json}" or "data: [DONE]"
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        # Signal terminal frame so chat.py knows we're finished.
                        yield "", True
                        break
                    try:
                        evt = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    choices = evt.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    chunk = delta.get("content") or ""
                    finish_reason = choices[0].get("finish_reason")
                    done = finish_reason is not None
                    if chunk or done:
                        yield chunk, done
                    if done:
                        break
        except httpx.TimeoutException as exc:
            raise LlamaServerError(
                "llama-server stream timed out — no chunk in 60s"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LlamaServerError(
                f"llama-server HTTP error: {exc.response.status_code}"
            ) from exc
        except httpx.ConnectError as exc:
            raise LlamaServerError(
                f"Cannot connect to llama-server at {self.base_url}"
            ) from exc
        finally:
            await streaming_client.aclose()


def select_inference_client(header_value: str | None, *, llamaserver_healthy: bool):
    """Pick which inference engine handles the FINAL stream phase.

    Day 53 empirical finding (DAY53_RETRO + Lesson #71):
      On the 8-vCPU shared-host VPS, running llama-server (mlock 7B+0.5B) and
      Ollama concurrently starves both. Speculative spec-dec measured 2.63 tok/s
      vs Ollama's ~7-15 tok/s historical baseline — a NET LOSS until either
      (a) Ollama is unloaded for chat traffic (only used for tool-calls), or
      (b) draft-n-max is tuned and acceptance rate measured per workload.

    Until that work lands, default behavior must NOT auto-degrade UX:
      - Header `speculative` -> force llama-server (raises if unhealthy). Opt-in.
      - Header `ollama`      -> force OllamaClient.
      - Header `auto` (default) or unset -> Ollama. SAFE default until benchmarks
                                              show speculative actually wins.

    Returns (engine_name, client_factory) where client_factory is a zero-arg
    callable returning an async-context-manager.
    """
    from services.ollama import OllamaClient  # late import — avoid circular

    requested = (header_value or "auto").strip().lower()

    if requested == "speculative":
        if not llamaserver_healthy:
            raise LlamaServerError(
                "Header X-Inference-Engine=speculative but llama-server unhealthy"
            )
        return "speculative", LlamaServerClient

    # ollama OR auto -> safe Ollama path (Day 53 empirical: no regression)
    return "ollama", OllamaClient
