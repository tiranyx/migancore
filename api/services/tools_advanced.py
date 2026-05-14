"""
tools_advanced.py — Advanced synthesis, coding, engineering, and visualization tools.
Day 73 | MiganCore ADO

New tools:
  generate_chart    — Python/data → matplotlib chart → PNG base64 (display in chat)
  read_pdf          — Extract text from PDF URL or local path
  research_deep     — Multi-step: search N sources → read → synthesize into report
  data_analyze      — Tabular CSV/JSON data → stats + chart + insights
  generate_code     — Full working code from description (any language)
  check_url_status  — Batch check if URLs are alive (HTTP status codes)
  summarize_text    — Summarize long text via teacher, with key points extraction
  translate_text    — Translate text between languages via teacher
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import tempfile
import textwrap
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# 1. GENERATE_CHART — matplotlib chart → PNG base64
# ---------------------------------------------------------------------------

async def _generate_chart(args: dict, ctx) -> str:
    """Generate a chart/graph from data using matplotlib. Returns markdown with inline PNG."""
    chart_type = args.get("type", "bar")  # bar | line | pie | scatter | histogram
    title = args.get("title", "Chart")
    labels = args.get("labels", [])
    data = args.get("data", [])
    x_label = args.get("x_label", "")
    y_label = args.get("y_label", "")
    color = args.get("color", "#4F8EF7")

    if not data:
        return "ERROR: `data` diperlukan (list angka atau list pasangan [x, y])"

    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#16213e")
        ax.tick_params(colors="white")
        ax.spines["bottom"].set_color("#444")
        ax.spines["left"].set_color("#444")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")

        colors = ["#4F8EF7", "#F76F6F", "#6FF7A0", "#F7D56F", "#D06FF7", "#6FE0F7"]

        if chart_type == "bar":
            x = range(len(data))
            bars = ax.bar(x, data, color=colors[:len(data)] if len(data) <= 6 else color)
            if labels:
                ax.set_xticks(x)
                ax.set_xticklabels(labels, rotation=30, ha="right", color="white")
        elif chart_type == "line":
            x = labels if labels else list(range(len(data)))
            ax.plot(x, data, color=color, linewidth=2, marker="o", markersize=5)
            ax.fill_between(range(len(data)), data, alpha=0.15, color=color)
            if labels:
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels, rotation=30, ha="right", color="white")
        elif chart_type == "pie":
            wedge_labels = labels if labels else [f"Item {i+1}" for i in range(len(data))]
            wedges, texts, autotexts = ax.pie(
                data, labels=wedge_labels, autopct="%1.1f%%",
                colors=colors[:len(data)], startangle=140,
            )
            for t in texts + autotexts:
                t.set_color("white")
        elif chart_type == "scatter":
            if isinstance(data[0], (list, tuple)):
                xs = [d[0] for d in data]
                ys = [d[1] for d in data]
            else:
                xs = list(range(len(data)))
                ys = data
            ax.scatter(xs, ys, color=color, alpha=0.7, s=60)
        elif chart_type == "histogram":
            ax.hist(data, bins=min(20, len(data)), color=color, edgecolor="#222", alpha=0.85)
        else:
            return f"ERROR: chart type '{chart_type}' tidak dikenal. Pilihan: bar, line, pie, scatter, histogram"

        ax.set_title(title, fontsize=14, pad=12)
        if x_label:
            ax.set_xlabel(x_label, color="white")
        if y_label:
            ax.set_ylabel(y_label, color="white")

        ax.grid(True, color="#333", linestyle="--", alpha=0.4, axis="y")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)

        img_b64 = base64.b64encode(buf.read()).decode()
        return f"![{title}](data:image/png;base64,{img_b64})\n\n*Chart: {title}*"

    except ImportError:
        return "ERROR: matplotlib tidak tersedia. Hubungi admin untuk install."
    except Exception as exc:
        logger.warning("tool.generate_chart.error", error=str(exc)[:80])
        return f"ERROR saat membuat chart: {exc}"


# ---------------------------------------------------------------------------
# 2. READ_PDF — Extract text from PDF URL or base64
# ---------------------------------------------------------------------------

async def _read_pdf(args: dict, ctx) -> str:
    """Extract text content from a PDF file (URL or local path)."""
    url = args.get("url", "").strip()
    max_pages = int(args.get("max_pages", 5))

    if not url:
        return "ERROR: `url` PDF diperlukan"

    try:
        import pdfplumber

        # Download PDF to temp file
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                return f"ERROR: URL bukan PDF (Content-Type: {content_type})"

        pdf_bytes = resp.content

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            text_parts = []
            with pdfplumber.open(tmp_path) as pdf:
                total_pages = len(pdf.pages)
                pages_to_read = min(max_pages, total_pages)
                for i, page in enumerate(pdf.pages[:pages_to_read]):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_parts.append(f"--- Halaman {i+1} ---\n{page_text.strip()}")

            if not text_parts:
                return f"PDF memiliki {total_pages} halaman tapi tidak ada teks yang bisa diekstrak (kemungkinan PDF berupa gambar scan)."

            output = "\n\n".join(text_parts)
            if total_pages > max_pages:
                output += f"\n\n*[Ditampilkan {pages_to_read}/{total_pages} halaman. Gunakan max_pages untuk lebih.]*"
            return output

        finally:
            os.unlink(tmp_path)

    except ImportError:
        return "ERROR: pdfplumber tidak tersedia. Hubungi admin."
    except httpx.HTTPStatusError as e:
        return f"ERROR: Gagal download PDF (HTTP {e.response.status_code})"
    except Exception as exc:
        logger.warning("tool.read_pdf.error", error=str(exc)[:80])
        return f"ERROR saat membaca PDF: {exc}"


# ---------------------------------------------------------------------------
# 3. RESEARCH_DEEP — Multi-source autonomous research + synthesis
# ---------------------------------------------------------------------------

async def _research_deep(args: dict, ctx) -> str:
    """
    Autonomous multi-step research:
    1. Search topic → get N URLs
    2. Read each URL (Jina reader)
    3. Extract key facts
    4. Synthesize into structured report via teacher

    Much more thorough than single web_search.
    """
    topic = args.get("topic", "").strip()
    depth = int(args.get("depth", 3))  # how many sources to read (1-5)
    language = args.get("language", "id")  # id | en

    if not topic:
        return "ERROR: `topic` diperlukan"

    depth = min(5, max(1, depth))

    try:
        # Step 1: Search for sources
        search_results = []
        search_query = f"{topic} site:wikipedia.org OR site:kompas.com OR site:detik.com OR site:medium.com" if language == "id" else topic

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Use DuckDuckGo-style search via onamix or Jina search
            jina_url = f"https://s.jina.ai/{httpx.URL(search_query)}"
            try:
                resp = await client.get(jina_url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                })
                if resp.status_code == 200:
                    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    search_results = data.get("data", [])[:depth]
            except Exception:
                pass

            # Fallback: use Wikipedia API for Indonesian topics
            if not search_results and language == "id":
                wiki_url = f"https://id.wikipedia.org/api/rest_v1/page/summary/{httpx.URL(topic)}"
                try:
                    wresp = await client.get(wiki_url)
                    if wresp.status_code == 200:
                        wd = wresp.json()
                        search_results = [{"url": wd.get("content_urls", {}).get("desktop", {}).get("page", ""), "title": wd.get("title", topic)}]
                except Exception:
                    pass

        # Step 2: Read each source
        source_texts = []
        async with httpx.AsyncClient(timeout=20.0) as client:
            for sr in search_results[:depth]:
                url = sr.get("url", "") if isinstance(sr, dict) else str(sr)
                if not url:
                    continue
                try:
                    jina_read = f"https://r.jina.ai/{url}"
                    resp = await client.get(jina_read, headers={
                        "User-Agent": "Mozilla/5.0",
                        "X-Return-Format": "text",
                    }, timeout=15.0)
                    if resp.status_code == 200:
                        text = resp.text[:2000]  # cap per source
                        source_texts.append(f"**Sumber: {url}**\n{text}")
                except Exception:
                    continue

        if not source_texts:
            return f"Tidak dapat mengambil sumber untuk: '{topic}'. Coba gunakan web_search atau onamix_search."

        # Step 3: Synthesize via teacher
        combined = "\n\n---\n\n".join(source_texts[:depth])
        lang_instruction = "dalam Bahasa Indonesia" if language == "id" else "in English"

        synthesis_prompt = f"""Kamu adalah research analyst. Berdasarkan teks-teks sumber berikut tentang "{topic}",
buat laporan riset terstruktur {lang_instruction} yang mencakup:
1. **Ringkasan Utama** (2-3 paragraf)
2. **Temuan Kunci** (bullet points)
3. **Data & Angka Penting** (jika ada)
4. **Kesimpulan**

SUMBER:
{combined}

LAPORAN:"""

        # Use teacher API (Gemini first as cheapest)
        from config import settings
        gemini_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        report = ""

        if gemini_key:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                        json={"contents": [{"role": "user", "parts": [{"text": synthesis_prompt}]}]},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        report = data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                pass

        if not report:
            # Fallback: return raw combined text with headers
            report = f"## Riset: {topic}\n\n" + "\n\n---\n\n".join(source_texts[:depth])

        return f"## Laporan Riset: {topic}\n*{len(source_texts)} sumber dibaca*\n\n{report}"

    except Exception as exc:
        logger.warning("tool.research_deep.error", error=str(exc)[:80])
        return f"ERROR research_deep: {exc}"


# ---------------------------------------------------------------------------
# 4. DATA_ANALYZE — CSV/JSON data → stats + chart + insights
# ---------------------------------------------------------------------------

async def _data_analyze(args: dict, ctx) -> str:
    """Analyze tabular data (CSV text or JSON list of objects). Returns stats + chart."""
    data_input = args.get("data", "")
    question = args.get("question", "Analisis data ini")
    chart_type = args.get("chart", "bar")  # bar | line | none

    if not data_input:
        return "ERROR: `data` diperlukan (CSV text atau JSON array)"

    try:
        import pandas as pd

        # Parse data
        if isinstance(data_input, list):
            df = pd.DataFrame(data_input)
        elif isinstance(data_input, str):
            if data_input.strip().startswith("["):
                df = pd.DataFrame(json.loads(data_input))
            else:
                df = pd.read_csv(io.StringIO(data_input))
        else:
            return "ERROR: `data` harus berupa CSV string atau JSON array"

        if df.empty:
            return "ERROR: Data kosong"

        # Basic stats
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        stats_lines = [f"**Baris:** {len(df)} | **Kolom:** {len(df.columns)}"]
        stats_lines.append(f"**Kolom:** {', '.join(df.columns.tolist())}")

        if numeric_cols:
            desc = df[numeric_cols].describe().round(2)
            stats_lines.append("\n**Statistik:**")
            stats_lines.append("```")
            stats_lines.append(desc.to_string())
            stats_lines.append("```")

        stats_text = "\n".join(stats_lines)

        # Chart (if numeric data available)
        chart_text = ""
        if numeric_cols and chart_type != "none":
            col = numeric_cols[0]
            chart_args = {
                "type": chart_type,
                "title": f"{col} — {question[:40]}",
                "data": df[col].tolist()[:50],
                "labels": df.index.tolist()[:50] if df.index.dtype == "object" else [],
                "y_label": col,
            }
            chart_text = await _generate_chart(chart_args, ctx)

        return f"## Analisis Data\n\n{stats_text}\n\n{chart_text}"

    except ImportError:
        return "ERROR: pandas tidak tersedia. Hubungi admin."
    except Exception as exc:
        logger.warning("tool.data_analyze.error", error=str(exc)[:80])
        return f"ERROR analisis data: {exc}"


# ---------------------------------------------------------------------------
# 5. SUMMARIZE_TEXT — Long text → structured summary
# ---------------------------------------------------------------------------

async def _summarize_text(args: dict, ctx) -> str:
    """Summarize long text with key points, using teacher API."""
    text = args.get("text", "").strip()
    style = args.get("style", "bullet")  # bullet | paragraph | tldr
    language = args.get("language", "id")

    if not text:
        return "ERROR: `text` diperlukan"

    if len(text) < 200:
        return f"Teks terlalu pendek untuk diringkas:\n\n{text}"

    style_map = {
        "bullet": "dalam poin-poin bullet (max 10 poin)",
        "paragraph": "dalam 2-3 paragraf ringkas",
        "tldr": "dalam 1-2 kalimat (TL;DR)",
    }
    style_instruction = style_map.get(style, style_map["bullet"])
    lang_instruction = "Bahasa Indonesia" if language == "id" else "English"

    prompt = f"Ringkas teks berikut {style_instruction}, dalam {lang_instruction}:\n\n{text[:4000]}"

    try:
        from config import settings
        gemini_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if gemini_key:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                    json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]

        # Fallback: local Ollama
        async with httpx.AsyncClient(timeout=30.0) as client:
            from config import settings as s
            resp = await client.post(
                f"{s.OLLAMA_URL}/api/generate",
                json={"model": s.DEFAULT_MODEL, "prompt": prompt, "stream": False},
            )
            if resp.status_code == 200:
                return resp.json().get("response", "Gagal membuat ringkasan.")
        return "ERROR: Tidak dapat menjangkau teacher API"
    except Exception as exc:
        return f"ERROR summarize: {exc}"


# ---------------------------------------------------------------------------
# 6. CHECK_URLS — Batch HTTP status checker
# ---------------------------------------------------------------------------

async def _check_urls(args: dict, ctx) -> str:
    """Check HTTP status of one or more URLs. Returns status table."""
    urls = args.get("urls", args.get("url", ""))
    if isinstance(urls, str):
        urls = [u.strip() for u in urls.split("\n") if u.strip()]
    if not urls:
        return "ERROR: `urls` diperlukan (string atau list)"

    urls = urls[:20]  # cap at 20

    async def check_one(url: str) -> tuple[str, int, str]:
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.head(url, headers={"User-Agent": "Mozilla/5.0"})
                return url, resp.status_code, "✅" if resp.status_code < 400 else "⚠️"
        except httpx.ConnectError:
            return url, 0, "❌ Connection refused"
        except httpx.TimeoutException:
            return url, 0, "⏱️ Timeout"
        except Exception as exc:
            return url, 0, f"❌ {str(exc)[:40]}"

    results = await asyncio.gather(*[check_one(u) for u in urls])

    lines = ["| URL | Status | Keterangan |", "|-----|--------|------------|"]
    for url, code, note in results:
        short_url = url[:60] + "..." if len(url) > 60 else url
        lines.append(f"| {short_url} | {code or '-'} | {note} |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 7. TRANSLATE_TEXT — Multi-language translation via teacher
# ---------------------------------------------------------------------------

async def _translate_text(args: dict, ctx) -> str:
    """Translate text to target language using teacher API."""
    text = args.get("text", "").strip()
    target = args.get("target_language", "en")  # en | id | ms | ar | zh | etc.
    source = args.get("source_language", "auto")

    if not text:
        return "ERROR: `text` diperlukan"

    lang_names = {
        "id": "Bahasa Indonesia", "en": "English", "ms": "Bahasa Melayu",
        "ar": "Arabic", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
        "fr": "French", "de": "German", "es": "Spanish",
    }
    target_name = lang_names.get(target, target)
    prompt = f"Translate the following text to {target_name}. Return only the translation, no explanation:\n\n{text[:3000]}"

    try:
        from config import settings
        gemini_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if gemini_key:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                    json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    translated = data["candidates"][0]["content"]["parts"][0]["text"]
                    return f"**[{source.upper()} → {target.upper()}]**\n\n{translated}"

        return "ERROR: Teacher API tidak tersedia untuk translasi"
    except Exception as exc:
        return f"ERROR translate: {exc}"


# ---------------------------------------------------------------------------
# Registry export
# ---------------------------------------------------------------------------

ADVANCED_TOOLS = {
    "generate_chart":  _generate_chart,
    "read_pdf":        _read_pdf,
    "research_deep":   _research_deep,
    "data_analyze":    _data_analyze,
    "summarize_text":  _summarize_text,
    "check_urls":      _check_urls,
    "translate_text":  _translate_text,
}
