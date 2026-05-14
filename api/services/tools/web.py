"""Web organ — search and fetch from the internet."""

import json
import urllib.parse
from typing import Any

import httpx
import structlog

from .base import ToolContext, ToolExecutionError

logger = structlog.get_logger()

DDG_ENDPOINT = "https://api.duckduckgo.com/"


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
                headers={"User-Agent": "MiganCore/0.7.0"},
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException as exc:
        raise ToolExecutionError("Web search timed out") from exc
    except Exception as exc:
        raise ToolExecutionError(f"Web search failed: {exc}") from exc

    results: list[dict] = []
    if data.get("Answer"):
        results.append({"title": "Jawaban Langsung", "snippet": data["Answer"], "url": "", "source": "DuckDuckGo"})
    if data.get("Abstract"):
        results.append({"title": data.get("Heading", query), "snippet": data["Abstract"], "url": data.get("AbstractURL", ""), "source": data.get("AbstractSource", "")})
    for topic in data.get("RelatedTopics", []):
        if len(results) >= limit:
            break
        if isinstance(topic, dict) and topic.get("Text"):
            results.append({"title": topic["Text"][:80], "snippet": topic["Text"], "url": topic.get("FirstURL", ""), "source": "DuckDuckGo"})

    logger.info("tool.web_search", query=query, results=len(results))
    return {"results": results[:limit], "query": query, "result_count": len(results)}


async def _web_read(args: dict, ctx: ToolContext) -> dict:
    """Fetch and extract readable text from a URL (jina.ai reader)."""
    url = args.get("url", "").strip()
    if not url:
        raise ToolExecutionError("'url' is required")

    reader_url = f"https://r.jina.ai/http://{url.replace('https://', '').replace('http://', '')}"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(25.0)) as client:
            resp = await client.get(reader_url, headers={"User-Agent": "MiganCore/0.7.0"})
            resp.raise_for_status()
            text = resp.text[:4000]
    except Exception as exc:
        raise ToolExecutionError(f"Failed to read URL: {exc}") from exc

    logger.info("tool.web_read", url=url, chars=len(text))
    return {"url": url, "text": text, "source": "jina.ai"}


HANDLERS: dict[str, Any] = {
    "web_search": _web_search,
    "web_read": _web_read,
}
