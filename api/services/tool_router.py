"""
Day 73 — Lazy Tool Router
==========================
Selects a small, relevant subset of tools per message instead of sending
all 42 schemas to Ollama every chat.

Problem: 42 tools × full JSON schemas ≈ 6,000+ tokens of prompt overhead per
request → slow TTFT on CPU 7B inference.

Solution: Two-pass selection:
  Pass 1 — keyword match (O(n) string scan, zero async, <1 ms): if message
            contains obvious tool-intent keywords, return that focused set.
  Pass 2 — semantic embedding (fastembed cosine, ~50 ms): fallback when no
            keywords fire; delegates to services.tool_relevance.

CORE_TOOLS are always included regardless of match.
"""

from __future__ import annotations

import re
from typing import Optional

import structlog

logger = structlog.get_logger()

# Always-on tools — proactive use regardless of query content
CORE_TOOLS: set[str] = {
    "memory_write",
    "memory_search",
}

# How many semantic-match tools to add on top of CORE_TOOLS when no keyword fires
_SEMANTIC_TOP_K = 6

# ---------------------------------------------------------------------------
# Keyword → tool mapping
# Each entry: ([keyword, ...], [tool_name, ...])
# First keyword match per entry wins; multiple rules can fire.
# ---------------------------------------------------------------------------
_RULES: list[tuple[list[str], list[str]]] = [
    # Charts / data visualization
    (
        ["grafik", "chart", "plot", "diagram", "visualisasi", "buat grafik", "bar chart",
         "pie chart", "line chart", "scatter"],
        ["generate_chart", "data_analyze"],
    ),
    # Data analysis / tabular
    (
        ["csv", "excel", "dataframe", "analisis data", "data analysis", "statistik",
         "mean ", "median ", "distribusi data"],
        ["data_analyze", "generate_chart", "run_python"],
    ),
    # PDF reading
    (
        ["pdf", "baca dokumen", "read pdf", "extract pdf", "isi pdf", "halaman pdf"],
        ["read_pdf"],
    ),
    # Translation
    (
        ["terjemah", "translate", "terjemahkan", "bahasa inggris", "bahasa indonesia",
         "bahasa melayu", "alih bahasa", "language"],
        ["translate_text"],
    ),
    # Deep research / synthesis
    (
        ["riset mendalam", "deep research", "synthesis", "multi source", "research deep",
         "komprehensif", "bandingkan sumber"],
        ["research_deep", "onamix_search", "web_read"],
    ),
    # URL health check
    (
        ["cek url", "check url", "link mati", "broken link", "status website",
         "dead link", "cek link"],
        ["check_urls"],
    ),
    # Text summarization
    (
        ["ringkas", "summarize", "summary", "rangkum", "singkat", "tl;dr", "tldr",
         "simpulkan", "resume teks"],
        ["summarize_text"],
    ),
    # Image generation
    (
        ["gambar", "generate image", "buat gambar", "image gen", "ilustrasi",
         "visualize", "create image", "foto ai"],
        ["generate_image"],
    ),
    # Web search / news / lookup
    (
        ["cari", "search", "berita", "informasi terbaru", "google", "bing",
         "wikipedia", "lookup", "cari di web"],
        ["onamix_search", "onamix_get"],
    ),
    # Web content reading
    (
        ["baca url", "baca website", "fetch url", "ambil konten", "isi halaman",
         "open url", "read url", "scrape"],
        ["web_read", "onamix_get"],
    ),
    # Python / code execution
    (
        ["jalankan kode", "run python", "execute code", "python script", "python repl",
         "hitung dengan kode", "compute"],
        ["run_python"],
    ),
    # Calculator / math
    (
        ["hitung ", "calculate ", "kalkulasi", "rumus", "formula", "berapa hasil",
         "matematik", "math"],
        ["calculate"],
    ),
    # Text to speech
    (
        ["suara", "tts", "ucapkan", "text to speech", "baca keras", "audio output"],
        ["text_to_speech"],
    ),
    # File write
    (
        ["simpan file", "write file", "buat file", "save file", "tulis ke file"],
        ["write_file"],
    ),
    # File read
    (
        ["baca file", "read file", "open file", "isi file", "lihat file"],
        ["read_file"],
    ),
    # Onamix multi-query
    (
        ["cari beberapa", "multi search", "beberapa sumber", "onamix multi"],
        ["onamix_multi", "onamix_search"],
    ),
    # Export PDF / slides
    (
        ["export pdf", "export slide", "buat presentasi", "jadikan pdf",
         "download pdf", "generate pdf"],
        ["export_pdf", "export_slides"],
    ),
    # Image analysis
    (
        ["analisis gambar", "describe image", "apa isi gambar", "identify image",
         "vision", "analyze image"],
        ["analyze_image"],
    ),
]


def _keyword_route(
    message: str,
    available: set[str],
) -> Optional[list[str]]:
    """Pass 1: keyword scan.

    Returns filtered tool list if any rule fires, else None (→ semantic fallback).
    Multiple rules can fire — their tool sets union together.
    """
    msg = message.lower()
    selected: set[str] = set(CORE_TOOLS) & available
    fired = False

    for keywords, tools in _RULES:
        for kw in keywords:
            if kw in msg:
                for t in tools:
                    if t in available:
                        selected.add(t)
                fired = True
                break  # next rule

    if not fired:
        return None  # no keywords matched

    result = [t for t in available if t in selected]
    return result if result else None


# Day 75 — concept/definition query patterns that need NO tool (adaptive doctrine)
# These match short conceptual questions where brain should answer from knowledge.
_CONCEPT_QUERY_PATTERNS = [
    "apa itu ", "apa arti ", "apa maksud ", "jelaskan ", "definisi ",
    "what is ", "what does ", "explain ", "define ", "meaning of ",
    "apa beda ", "apa perbedaan ", "what's the difference",
]

# Day 73 Codex audit — casual greeting / chit-chat patterns: brain answers from
# its own voice, no tool overhead. Default no-tools per Codex feedback:
# "default no-tools untuk chat biasa, tool routing hanya saat perlu".
_CASUAL_PATTERNS = [
    "halo", "hai", "hi ", "hello", "hey", "selamat pagi", "selamat siang",
    "selamat sore", "selamat malam", "good morning", "good night",
    "apa kabar", "how are you", "gimana kabar", "lagi apa",
    "makasih", "terima kasih", "thanks", "thank you", "thx", "ok ", "oke",
    "mantap", "keren", "wah", "wow", "lol", "haha", "hehe", "kok", "iya",
    "siap", "ya", "tidak", "ga ", "nggak", "enggak",
]


def _is_concept_query(message: str) -> bool:
    """Adaptive trigger: detect conceptual/definition queries that need no tool.

    Short query (<120 chars) starting/containing concept patterns → skip tools.
    Brain answers from knowledge (memory_search still available if it needs to recall).
    """
    msg_lower = message.lower().strip()
    if len(msg_lower) > 120:  # long query = likely needs tools
        return False
    for pat in _CONCEPT_QUERY_PATTERNS:
        if pat in msg_lower:
            return True
    return False


def _is_casual_chat(message: str) -> bool:
    """Adaptive trigger: detect casual/greeting messages that need no tool.

    Short query (<60 chars) starting with greeting/ack → skip tools.
    Brain responds with own voice (memory_write still in CORE for recall save).
    """
    msg_stripped = message.lower().strip()
    if len(msg_stripped) > 60:
        return False
    if len(msg_stripped) < 2:
        return True  # empty/tiny → no tool
    for pat in _CASUAL_PATTERNS:
        if msg_stripped == pat.strip() or msg_stripped.startswith(pat):
            return True
    return False


async def route_tools(
    message: str,
    available_tools: list[str],
    top_k: int = _SEMANTIC_TOP_K,
) -> list[str]:
    """Select relevant tools for this message.

    Args:
        message:         User's last message text.
        available_tools: All tool names the agent is configured to use.
        top_k:           Semantic top-K (used only when no keywords fire).

    Returns:
        Ordered list of tool names — subset of available_tools.
        Falls back to full list on any error.
    """
    if not available_tools:
        return []

    available_set = set(available_tools)

    # Day 73 Codex audit — Pass 0a: casual chat short-circuit
    # Greetings/acks ("halo", "makasih", "ok") don't need tools. Brain own voice.
    if _is_casual_chat(message):
        core_only = [t for t in available_tools if t in CORE_TOOLS]
        logger.info(
            "tool_router.casual_skip",
            query_len=len(message),
            available=len(available_tools),
            kept=len(core_only),
        )
        return core_only

    # Day 75 — Pass 0b: concept query short-circuit
    # Definition/explanation queries don't need tools (brain knows from KB + training).
    # Per Adaptive Doctrine: skip tool spec when not earned. Massive speed win on CPU.
    if _is_concept_query(message):
        core_only = [t for t in available_tools if t in CORE_TOOLS]
        logger.info(
            "tool_router.concept_skip",
            query_len=len(message),
            available=len(available_tools),
            kept=len(core_only),
        )
        return core_only  # only memory_write + memory_search

    # Pass 1: keyword fast path
    keyword_result = _keyword_route(message, available_set)
    if keyword_result is not None:
        logger.info(
            "tool_router.keyword_hit",
            query_len=len(message),
            selected=len(keyword_result),
            available=len(available_tools),
        )
        return keyword_result

    # Pass 2: semantic embedding
    try:
        from services.tool_relevance import select_relevant_tools
        result = await select_relevant_tools(message, available_tools, top_k=top_k)
        logger.info(
            "tool_router.semantic_hit",
            query_len=len(message),
            selected=len(result),
            available=len(available_tools),
        )
        return result
    except Exception as e:
        logger.warning("tool_router.semantic_fail", error=str(e))

    # Fallback: core tools + first top_k others
    core_present = [t for t in available_tools if t in CORE_TOOLS]
    others = [t for t in available_tools if t not in CORE_TOOLS][:top_k]
    return core_present + others
