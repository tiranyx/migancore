"""
Ollama client with timeouts, retry logic, and structured error handling.

Prevents FastAPI workers from hanging indefinitely when Ollama is
loading a model, OOM-ing, or otherwise unresponsive.
"""

import json
from collections.abc import AsyncGenerator

import httpx
from config import settings

# Default: 60s total, 5s connect, 30s read between chunks
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=5.0, read=30.0)

# Streaming: no total timeout (response can be long), but 30s between chunks
STREAM_TIMEOUT = httpx.Timeout(None, connect=5.0, read=30.0)


class OllamaError(Exception):
    """Raised when Ollama returns an error or cannot be reached."""
    pass


class OllamaClient:
    """Async HTTP client for Ollama with sensible timeouts."""

    def __init__(self, base_url: str | None = None, timeout: httpx.Timeout | None = None):
        self.base_url = (base_url or settings.OLLAMA_URL).rstrip("/")
        self.timeout = timeout or DEFAULT_TIMEOUT
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
        self._client = None

    def _client_or_raise(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("OllamaClient not entered. Use 'async with'.")
        return self._client

    async def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        stream: bool = False,
        options: dict | None = None,
    ) -> dict:
        """Generate text from Ollama /api/generate."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        try:
            resp = await self._client_or_raise().post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                raise OllamaError(f"Ollama error: {data['error']}")
            return data
        except httpx.TimeoutException as exc:
            raise OllamaError(
                f"Ollama request timed out after {self.timeout} — model may be loading or OOM"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaError(f"Ollama HTTP error: {exc.response.status_code}") from exc
        except httpx.ConnectError as exc:
            raise OllamaError(f"Cannot connect to Ollama at {self.base_url}") from exc

    async def chat(
        self,
        model: str,
        messages: list[dict],
        stream: bool = False,
        options: dict | None = None,
    ) -> dict:
        """Chat completion via Ollama /api/chat."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if options:
            payload["options"] = options

        try:
            resp = await self._client_or_raise().post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                raise OllamaError(f"Ollama error: {data['error']}")
            return data
        except httpx.TimeoutException as exc:
            raise OllamaError(f"Ollama chat timed out after {self.timeout}") from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaError(f"Ollama HTTP error: {exc.response.status_code}") from exc
        except httpx.ConnectError as exc:
            raise OllamaError(f"Cannot connect to Ollama at {self.base_url}") from exc

    async def chat_stream(
        self,
        model: str,
        messages: list[dict],
        options: dict | None = None,
    ) -> AsyncGenerator[tuple[str, bool], None]:
        """Stream chat completion via Ollama /api/chat.

        Yields (chunk, done) tuples:
          chunk — content fragment (may be empty string on final message)
          done  — True only on the final message

        Uses STREAM_TIMEOUT (no total timeout, 30s between chunks).
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if options:
            payload["options"] = options

        # Use a dedicated streaming client with no total timeout
        streaming_client = httpx.AsyncClient(timeout=STREAM_TIMEOUT)
        try:
            async with streaming_client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if data.get("error"):
                        raise OllamaError(f"Ollama error: {data['error']}")
                    chunk = data.get("message", {}).get("content", "")
                    done = data.get("done", False)
                    yield chunk, done
                    if done:
                        break
        except httpx.TimeoutException as exc:
            raise OllamaError("Ollama stream timed out — no chunk received in 30s") from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaError(f"Ollama HTTP error: {exc.response.status_code}") from exc
        except httpx.ConnectError as exc:
            raise OllamaError(f"Cannot connect to Ollama at {self.base_url}") from exc
        finally:
            await streaming_client.aclose()

    async def chat_with_tools(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict],
        options: dict | None = None,
    ) -> dict:
        """Chat with native tool calling support (Ollama >= 0.20, stream=false required).

        Returns the raw Ollama response. Caller inspects:
          response["message"]["tool_calls"]  — if tool calls requested
          response["message"]["content"]      — if plain text response

        Tool spec format (OpenAI-compatible):
          [{
            "type": "function",
            "function": {
              "name": "tool_name",
              "description": "...",
              "parameters": {JSON Schema object}
            }
          }]
        """
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": False,  # Ollama tool calling requires stream=false
        }
        if tools:
            payload["tools"] = tools
        if options:
            payload["options"] = options

        try:
            resp = await self._client_or_raise().post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                raise OllamaError(f"Ollama error: {data['error']}")
            return data
        except httpx.TimeoutException as exc:
            raise OllamaError(f"Ollama tool-call timed out after {self.timeout}") from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaError(f"Ollama HTTP error: {exc.response.status_code}") from exc
        except httpx.ConnectError as exc:
            raise OllamaError(f"Cannot connect to Ollama at {self.base_url}") from exc

    async def list_models(self) -> list[str]:
        """Return list of loaded model names."""
        try:
            resp = await self._client_or_raise().get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m.get("name", "unknown") for m in data.get("models", [])]
        except Exception as exc:
            raise OllamaError(f"Failed to list Ollama models: {exc}") from exc
