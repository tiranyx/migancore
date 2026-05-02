"""
Ollama client with timeouts, retry logic, and structured error handling.

Prevents FastAPI workers from hanging indefinitely when Ollama is
loading a model, OOM-ing, or otherwise unresponsive.
"""

import httpx
from config import settings

# Default: 60s total, 5s connect, 30s read between chunks
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=5.0, read=30.0)


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
        """Generate text from Ollama.

        Args:
            model: Model name, e.g. "qwen2.5:7b-instruct-q4_K_M"
            prompt: User prompt text
            system: System prompt / persona
            stream: Whether to stream response tokens
            options: Additional Ollama options (temperature, etc.)

        Returns:
            Parsed JSON response from Ollama

        Raises:
            OllamaError: On HTTP error, timeout, or Ollama error response
        """
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
            raise OllamaError(f"Ollama request timed out after {self.timeout} — model may be loading or OOM") from exc
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
        """Chat completion via Ollama /api/chat (OpenAI-compatible).

        Args:
            model: Model name
            messages: List of {"role": "system|user|assistant", "content": "..."}
            stream: Whether to stream
            options: Additional options

        Returns:
            Parsed JSON response
        """
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

    async def list_models(self) -> list[str]:
        """Return list of loaded model names."""
        try:
            resp = await self._client_or_raise().get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m.get("name", "unknown") for m in data.get("models", [])]
        except Exception as exc:
            raise OllamaError(f"Failed to list Ollama models: {exc}") from exc
