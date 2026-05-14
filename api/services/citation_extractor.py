"""
Citation Extractor — Sprint 2 Day 75

Adaptive source citation untuk chat response.
PER FAHMI ADAPTIVE DOCTRINE: chips muncul HANYA saat earn their weight.

Hide for: casual greeting, emotional, creative response, opinion
Show for: factual KB recall, search result, memory recall, PDF read

Tool taxonomy:
- KNOWLEDGE tools (cite): onamix_search, web_read, memory_search, read_pdf
- ARTIFACT tools (skip — punya tool chip sendiri): image_gen, run_python,
  generate_chart, generate_image, calculate, write_file, etc

Output: list[dict] with {icon, label, detail, url, bucket} — max 3, deduped.
"""
from __future__ import annotations

import time
from typing import Optional

import structlog

logger = structlog.get_logger()

# Minimum response length to bother surfacing sources (adaptive trigger)
MIN_RESPONSE_CHARS_FOR_CITATION = 80
MAX_SOURCES_DISPLAYED = 3

# Tool taxonomy
CITE_WORTHY_TOOLS = {
    "onamix_search", "onamix_get", "onamix_multi",
    "web_read", "research_deep",
    "memory_search",
    "read_pdf",
}
ARTIFACT_TOOLS_SKIP = {
    # These produce inline output (image/code/chart), not citation
    "generate_image", "run_python", "python", "generate_chart",
    "calculate", "write_file", "read_file", "text_to_speech",
    "analyze_image", "export_pdf", "export_slides",
    "memory_write",  # writes are not cites
    "onamix_post", "onamix_history", "onamix_links", "onamix_config",
    "onamix_crawl",
}


def _format_recall_time(timestamp: Optional[int]) -> str:
    """Convert unix timestamp to friendly Indonesian relative time."""
    if not timestamp:
        return "obrolan sebelumnya"
    elapsed = time.time() - timestamp
    if elapsed < 3600:
        mins = int(elapsed / 60)
        return f"obrolan {mins} menit lalu"
    if elapsed < 86400:
        hrs = int(elapsed / 3600)
        return f"obrolan {hrs} jam lalu"
    if elapsed < 30 * 86400:
        days = int(elapsed / 86400)
        return f"obrolan {days} hari lalu"
    return "obrolan lama"


def _onamix_search_sources(result: dict) -> list[dict]:
    """Extract top hits from onamix_search/onamix_get/onamix_multi result."""
    sources = []
    items = result.get("results") or []
    engine = result.get("engine", "search")
    for it in items[:2]:
        url = it.get("url", "")
        title = (it.get("title", "") or url)[:60]
        if url:
            sources.append({
                "icon": "🌐",
                "label": title,
                "detail": f"{engine}: {url}",
                "url": url,
                "bucket": None,
            })
    # Wikipedia special case: result has answer_content + source_url
    if not sources and result.get("source_url"):
        sources.append({
            "icon": "📖",
            "label": (result.get("source_title", "") or "wikipedia")[:60],
            "detail": result["source_url"],
            "url": result["source_url"],
            "bucket": None,
        })
    return sources


def _web_read_sources(arguments: dict, result: dict) -> list[dict]:
    """Extract URL from web_read."""
    url = arguments.get("url") or result.get("url", "")
    if not url:
        return []
    title = (result.get("title") or url)[:60]
    return [{
        "icon": "🌐",
        "label": title,
        "detail": url,
        "url": url,
        "bucket": None,
    }]


def _memory_search_sources(result: dict) -> list[dict]:
    """Extract from memory_search — distinguish knowledge vs recall."""
    sources = []
    hits = result.get("results") or []
    for h in hits[:2]:
        if h.get("is_knowledge"):
            # SIDIX inherited knowledge — show bucket + source path
            bucket = h.get("bucket", "memory")
            src_path = h.get("source_path") or h.get("chunk_text", "")[:40]
            sources.append({
                "icon": "📂",
                "label": f"{bucket}: {src_path[:50]}",
                "detail": f"score={h.get('score', 0):.2f}",
                "url": None,
                "bucket": bucket,
            })
        else:
            # Recalled past conversation — friendly time label
            ts = h.get("timestamp")
            sources.append({
                "icon": "💭",
                "label": _format_recall_time(ts),
                "detail": (h.get("user_message", "") or "")[:80],
                "url": None,
                "bucket": "conversation",
            })
    return sources


def _read_pdf_sources(arguments: dict, result: dict) -> list[dict]:
    """Extract PDF source."""
    fname = arguments.get("filename") or arguments.get("path") or "PDF"
    return [{
        "icon": "📖",
        "label": fname[:60],
        "detail": f"PDF ({result.get('pages', '?')} halaman)" if result else "PDF",
        "url": None,
        "bucket": None,
    }]


def _dedupe(sources: list[dict]) -> list[dict]:
    """Dedupe by url OR label (avoid same source repeated)."""
    seen = set()
    out = []
    for s in sources:
        key = s.get("url") or s.get("label")
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def extract_sources(
    tool_calls: list[dict],
    response_text: str,
) -> list[dict]:
    """Main entry — return adaptive list of source citations.

    Empty list = no citation (casual response or no knowledge tools used).

    Args:
        tool_calls: list of {skill_id, arguments, result, iteration}
                    from director run.
        response_text: brain's final response (for length-based adaptive trigger).

    Returns:
        list of source dicts (max MAX_SOURCES_DISPLAYED), or [] if not applicable.
    """
    # Adaptive trigger: skip for short casual responses
    if len(response_text or "") < MIN_RESPONSE_CHARS_FOR_CITATION:
        return []
    if not tool_calls:
        return []

    candidates: list[dict] = []
    for tc in tool_calls:
        skill = tc.get("skill_id", "")
        if skill in ARTIFACT_TOOLS_SKIP:
            continue
        if skill not in CITE_WORTHY_TOOLS:
            continue
        result_wrap = tc.get("result") or {}
        if not result_wrap.get("success", False):
            continue
        result = result_wrap.get("result") or {}
        args = tc.get("arguments") or {}

        if skill in ("onamix_search", "onamix_get", "onamix_multi", "research_deep"):
            candidates.extend(_onamix_search_sources(result))
        elif skill == "web_read":
            candidates.extend(_web_read_sources(args, result))
        elif skill == "memory_search":
            candidates.extend(_memory_search_sources(result))
        elif skill == "read_pdf":
            candidates.extend(_read_pdf_sources(args, result))

    deduped = _dedupe(candidates)
    if not deduped:
        return []

    logger.info(
        "citation.extracted",
        candidates=len(candidates),
        deduped=len(deduped),
        response_len=len(response_text),
    )
    return deduped[:MAX_SOURCES_DISPLAYED]
