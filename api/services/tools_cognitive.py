#!/usr/bin/env python3
"""
tools_cognitive.py — Cognitive & Essential AI Agent Tools
Day 67 | Migancore ADO

New tools added to ADO brain:
  tavily_search   — Real-time search via Tavily API (cleaner than ONAMIX for facts)
  serper_search   — Google search via Serper API (backup)
  think           — Structured chain-of-thought reasoning via teacher
  synthesize      — Multi-source synthesis: search -> extract -> synthesize via teacher
  teacher_ask     — Direct access to any teacher (Claude/Kimi/GPT/Gemini)
  multi_teacher   — Ask 2+ teachers, get diverse perspectives
  calculate       — Safe math evaluation (no external API)
  run_python      — Sandboxed Python execution (timeout 5s, no IO)
  extract_insights — Extract key insights/facts from text via teacher
  knowledge_discover — Autonomous: pick topic -> research -> synthesize -> save to KB

All tools follow the same signature:
  async def _tool_name(args: dict, ctx: ToolContext) -> str
"""

from __future__ import annotations

import ast
import asyncio
import json
import math
import os
import subprocess
import sys
import textwrap
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# A. TAVILY SEARCH — Real-time factual search
# ---------------------------------------------------------------------------

async def _tavily_search(args: dict, ctx) -> str:
    """Real-time web search via Tavily API. Faster + cleaner than ONAMIX for facts."""
    from config import settings
    query = args.get("query", "").strip()
    if not query:
        return "ERROR: query wajib diisi"
    max_results = int(args.get("max_results", 5))
    search_depth = args.get("search_depth", "basic")  # basic | advanced

    api_key = getattr(settings, "TAVILY_API_KEY", None) or os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return "ERROR: TAVILY_API_KEY tidak tersedia. Gunakan onamix_search sebagai fallback."

    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
        "include_answer": True,
        "include_raw_content": False,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://api.tavily.com/search", json=payload)
            resp.raise_for_status()
            data = resp.json()

        answer = data.get("answer", "")
        results = data.get("results", [])

        lines = []
        if answer:
            lines.append(f"**Jawaban Langsung:** {answer}\n")
        lines.append(f"**Hasil Pencarian ({len(results)} sumber):**")
        for i, r in enumerate(results[:max_results], 1):
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")[:300]
            lines.append(f"\n{i}. **{title}**")
            lines.append(f"   URL: {url}")
            lines.append(f"   {content}...")

        logger.info("tavily_search.ok", query=query, results=len(results))
        return "\n".join(lines)

    except httpx.HTTPStatusError as e:
        logger.error("tavily_search.http_error", status=e.response.status_code)
        return f"ERROR: Tavily API error {e.response.status_code}"
    except Exception as e:
        logger.error("tavily_search.error", error=str(e))
        return f"ERROR: {e}"


# ---------------------------------------------------------------------------
# B. SERPER SEARCH — Google search via Serper.dev
# ---------------------------------------------------------------------------

async def _serper_search(args: dict, ctx) -> str:
    """Google search via Serper API. Use when Tavily unavailable or need Google-specific results."""
    from config import settings
    query = args.get("query", "").strip()
    if not query:
        return "ERROR: query wajib diisi"
    num = int(args.get("num", 5))

    api_key = getattr(settings, "SERPER_API_KEY", None) or os.getenv("SERPER_API_KEY", "")
    if not api_key:
        return "ERROR: SERPER_API_KEY tidak tersedia."

    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": num, "gl": "id", "hl": "id"}

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post("https://google.serper.dev/search", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        lines = []
        organic = data.get("organic", [])
        answer_box = data.get("answerBox", {})

        if answer_box:
            lines.append(f"**Jawaban:** {answer_box.get('answer', answer_box.get('snippet',''))}\n")

        lines.append(f"**Google Search: {query}** ({len(organic)} hasil)")
        for i, r in enumerate(organic[:num], 1):
            lines.append(f"\n{i}. **{r.get('title','')}**")
            lines.append(f"   {r.get('link','')}")
            lines.append(f"   {r.get('snippet','')[:250]}")

        logger.info("serper_search.ok", query=query, results=len(organic))
        return "\n".join(lines)

    except Exception as e:
        logger.error("serper_search.error", error=str(e))
        return f"ERROR: {e}"


# ---------------------------------------------------------------------------
# C. THINK — Structured Chain-of-Thought Reasoning
# ---------------------------------------------------------------------------

async def _think(args: dict, ctx) -> str:
    """
    Structured reasoning tool. ADO berpikir step-by-step sebelum menjawab.
    Gunakan untuk: analisis kompleks, keputusan multi-faktor, debugging logika.
    Internally calls cheapest teacher (Gemini) or Ollama think mode.
    """
    from services.teacher_api import call_teacher, is_teacher_available
    from config import settings

    problem = args.get("problem", "").strip()
    mode = args.get("mode", "analyze")  # analyze | decide | debug | plan | critique

    if not problem:
        return "ERROR: problem wajib diisi"

    mode_prompts = {
        "analyze": "Analisis masalah ini secara mendalam. Identifikasi komponen kunci, hubungan antar komponen, dan implikasi.",
        "decide": "Evaluasi opsi-opsi yang ada. Buat pro/con matrix. Rekomendasikan keputusan terbaik dengan alasan.",
        "debug": "Debug masalah ini secara sistematis. Identifikasi root cause, bukan gejala.",
        "plan": "Buat rencana terstruktur. Breakdown ke langkah konkret yang dapat dieksekusi.",
        "critique": "Kritik argumen atau solusi ini. Cari kelemahan, asumsi tersembunyi, dan blind spots.",
    }

    system = f"""Kamu adalah reasoning engine untuk ADO (AI Decision Organizer).
Mode: {mode.upper()}
{mode_prompts.get(mode, mode_prompts['analyze'])}

Format output:
## Pemahaman Masalah
[Reformulasi singkat masalah dalam kata-katamu sendiri]

## Analisis
[Step-by-step reasoning, numbered]

## Temuan Kunci
[3-5 bullet points insight utama]

## Kesimpulan
[Jawaban/rekomendasi konkret]"""

    prompt = f"Problem: {problem}"

    # Try Gemini first (cheapest), fallback ke Ollama
    teacher = "gemini"
    if not is_teacher_available(teacher):
        teacher = "claude"
    if not is_teacher_available(teacher):
        teacher = "kimi"

    try:
        resp = await call_teacher(teacher, prompt=prompt, system=system, max_tokens=1200)
        logger.info("think.ok", mode=mode, teacher=teacher, tokens=resp.output_tokens)
        return f"**[THINK — {mode.upper()} via {teacher}]**\n\n{resp.text}"
    except Exception as e:
        logger.error("think.error", error=str(e))
        return f"ERROR think: {e}"


# ---------------------------------------------------------------------------
# D. SYNTHESIZE — Multi-source synthesis
# ---------------------------------------------------------------------------

async def _synthesize(args: dict, ctx) -> str:
    """
    Synthesis tool: gather from multiple sources -> synthesize via teacher.
    Pola: search(topic) + search(angle2) -> combine -> synthesize insight.
    Ideal untuk research mendalam + menemukan pola tersembunyi.
    """
    from services.teacher_api import call_teacher, is_teacher_available

    topic = args.get("topic", "").strip()
    sources = args.get("sources", [])  # list of text snippets to synthesize
    goal = args.get("goal", "Temukan insight kunci dan pola yang tidak obvious")
    output_format = args.get("output_format", "insight")  # insight | summary | comparison | report

    if not topic and not sources:
        return "ERROR: topic atau sources wajib diisi"

    # If no sources provided, auto-search via Tavily
    if not sources and topic:
        search_result = await _tavily_search({"query": topic, "max_results": 3, "search_depth": "basic"}, ctx)
        sources = [search_result]

        # Second angle search for richer synthesis
        if len(topic.split()) > 2:
            angle2 = topic + " Indonesia 2026"
            search2 = await _tavily_search({"query": angle2, "max_results": 3}, ctx)
            sources.append(search2)

    format_instructions = {
        "insight": "Temukan 5 insight paling tidak-obvious dari sumber-sumber ini. Prioritaskan koneksi antar domain.",
        "summary": "Buat ringkasan komprehensif yang menangkap semua informasi penting.",
        "comparison": "Bandingkan perspektif yang berbeda. Identifikasi konsensus dan kontradiksi.",
        "report": "Buat laporan terstruktur dengan Executive Summary, Temuan, dan Rekomendasi.",
    }

    combined = "\n\n---\n\n".join(str(s) for s in sources)
    system = f"""Kamu adalah synthesis engine untuk ADO.
Topik: {topic}
Goal: {goal}
Format: {format_instructions.get(output_format, format_instructions['insight'])}

Aturan:
- Jangan hanya merangkum. SINTESIS = temukan pola, koneksi, dan implikasi yang tidak langsung terlihat
- Jadilah spesifik. Angka, nama, tanggal jika tersedia
- Tandai tingkat kepercayaan: [TINGGI/SEDANG/RENDAH]
- Akhiri dengan "Pertanyaan lanjutan:" — 2-3 pertanyaan yang layak dieksplorasi"""

    prompt = f"Sintesis dari sumber-sumber berikut:\n\n{combined[:4000]}"

    teacher = "gemini"
    if not is_teacher_available(teacher):
        teacher = "claude"

    try:
        resp = await call_teacher(teacher, prompt=prompt, system=system, max_tokens=1500)
        logger.info("synthesize.ok", topic=topic, sources=len(sources), teacher=teacher)
        return f"**[SYNTHESIS — {topic or 'multi-source'} via {teacher}]**\n\n{resp.text}"
    except Exception as e:
        logger.error("synthesize.error", error=str(e))
        return f"ERROR synthesize: {e}"


# ---------------------------------------------------------------------------
# E. TEACHER ASK — Direct access to any teacher
# ---------------------------------------------------------------------------

async def _teacher_ask(args: dict, ctx) -> str:
    """
    Langsung tanya salah satu teacher AI.
    Teacher: claude | kimi | gpt | gemini
    Gunakan untuk: second opinion, validasi, expert consultation.
    """
    from services.teacher_api import call_teacher, is_teacher_available, list_available_teachers

    teacher = args.get("teacher", "gemini").lower()
    prompt = args.get("prompt", "").strip()
    system = args.get("system", "Kamu adalah asisten AI yang helpful, harmless, dan honest. Jawab dalam bahasa Indonesia.")
    max_tokens = int(args.get("max_tokens", 800))

    if not prompt:
        return "ERROR: prompt wajib diisi"

    available = list_available_teachers()
    if teacher not in available:
        return f"ERROR: Teacher '{teacher}' tidak tersedia. Tersedia: {available}"

    try:
        resp = await call_teacher(teacher, prompt=prompt, system=system, max_tokens=max_tokens)
        cost_str = f"${resp.cost_usd:.5f}" if resp.cost_usd else ""
        logger.info("teacher_ask.ok", teacher=teacher, tokens=resp.output_tokens)
        return f"**[{teacher.upper()} — {resp.model}]** {cost_str}\n\n{resp.text}"
    except Exception as e:
        logger.error("teacher_ask.error", teacher=teacher, error=str(e))
        return f"ERROR teacher_ask ({teacher}): {e}"


# ---------------------------------------------------------------------------
# F. MULTI TEACHER — Ask multiple teachers, get diverse perspectives
# ---------------------------------------------------------------------------

async def _multi_teacher(args: dict, ctx) -> str:
    """
    Tanya 2-4 teacher sekaligus. Bandingkan jawaban.
    Gunakan untuk: validasi, menemukan blind spots, mendapat perspektif beragam.
    """
    from services.teacher_api import call_teacher, list_available_teachers

    prompt = args.get("prompt", "").strip()
    teachers = args.get("teachers", ["gemini", "claude"])
    system = args.get("system", "Jawab singkat dan to-the-point dalam bahasa Indonesia.")
    max_tokens = int(args.get("max_tokens", 500))

    if not prompt:
        return "ERROR: prompt wajib diisi"

    available = list_available_teachers()
    teachers = [t for t in teachers if t in available][:4]

    if not teachers:
        return f"ERROR: Tidak ada teacher yang tersedia. Tersedia: {available}"

    async def ask_one(t):
        try:
            resp = await call_teacher(t, prompt=prompt, system=system, max_tokens=max_tokens)
            return t, resp.text, None
        except Exception as e:
            return t, None, str(e)

    results = await asyncio.gather(*[ask_one(t) for t in teachers])

    lines = [f"**[MULTI-TEACHER — {len(teachers)} perspektif]**\n\nPertanyaan: {prompt[:200]}\n"]
    for teacher_name, text, err in results:
        lines.append(f"\n---\n**{teacher_name.upper()}:**")
        if err:
            lines.append(f"ERROR: {err}")
        else:
            lines.append(text or "(kosong)")

    logger.info("multi_teacher.ok", teachers=teachers)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# G. CALCULATE — Safe math evaluation
# ---------------------------------------------------------------------------

async def _calculate(args: dict, ctx) -> str:
    """
    Hitung ekspresi matematika dengan aman. Mendukung: +,-,*,/,**,%, sqrt, sin, cos, log, dll.
    TIDAK bisa: akses file, network, atau kode arbitrary.
    """
    expression = args.get("expression", "").strip()
    if not expression:
        return "ERROR: expression wajib diisi"

    # Safe math namespace
    safe_globals = {
        "__builtins__": {},
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "len": len, "int": int, "float": float,
        "sqrt": math.sqrt, "pow": math.pow, "log": math.log,
        "log2": math.log2, "log10": math.log10,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan,
        "pi": math.pi, "e": math.e, "inf": math.inf,
        "floor": math.floor, "ceil": math.ceil,
        "factorial": math.factorial,
    }

    try:
        # Parse dulu untuk safety check
        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if hasattr(node.func, "id") and node.func.id not in safe_globals:
                    return f"ERROR: Fungsi '{node.func.id}' tidak diizinkan"
            if isinstance(node, ast.Attribute):
                return "ERROR: Akses attribute tidak diizinkan"

        result = eval(compile(tree, "<calc>", "eval"), safe_globals, {})
        logger.info("calculate.ok", expression=expression, result=result)
        return f"**Hasil:** `{expression}` = **{result}**"
    except ZeroDivisionError:
        return "ERROR: Division by zero"
    except SyntaxError as e:
        return f"ERROR: Syntax salah — {e}"
    except Exception as e:
        return f"ERROR: {e}"


# ---------------------------------------------------------------------------
# H. RUN PYTHON — Sandboxed Python execution
# ---------------------------------------------------------------------------

async def _run_python(args: dict, ctx) -> str:
    """
    Jalankan kode Python dalam sandbox (subprocess, timeout 8s).
    Bisa: loop, list comprehension, pandas/numpy (jika tersedia), string processing.
    TIDAK bisa: import os/sys, file I/O, network request, subprocess.
    """
    code = args.get("code", "").strip()
    timeout = min(int(args.get("timeout", 8)), 15)  # max 15 detik

    if not code:
        return "ERROR: code wajib diisi"

    # Block dangerous imports
    blocked = ["import os", "import sys", "import subprocess", "import socket",
               "import requests", "import httpx", "open(", "__import__",
               "exec(", "eval(", "compile(", "globals(", "locals("]
    for b in blocked:
        if b in code:
            return f"ERROR: '{b}' tidak diizinkan dalam sandbox"

    # Wrap code to capture stdout
    wrapped = f"""
import io, sys, math, json, re, collections, itertools, functools, datetime
from math import *
_stdout = io.StringIO()
sys.stdout = _stdout
try:
{chr(10).join("    " + line for line in code.split(chr(10)))}
except Exception as _e:
    print(f"RUNTIME ERROR: {{_e}}")
sys.stdout = sys.__stdout__
_result = _stdout.getvalue()
print(_result, end="")
"""

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", wrapped,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return f"ERROR: Timeout setelah {timeout} detik"

        output = stdout.decode("utf-8", errors="replace").strip()
        err_out = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0 and err_out:
            return f"ERROR (exit {proc.returncode}): {err_out[:500]}"

        logger.info("run_python.ok", lines=len(code.splitlines()), output_len=len(output))
        if not output:
            return "(kode berjalan, tidak ada output)"
        return f"**Output:**\n```\n{output[:2000]}\n```"

    except Exception as e:
        logger.error("run_python.error", error=str(e))
        return f"ERROR: {e}"


# ---------------------------------------------------------------------------
# I. EXTRACT INSIGHTS — Extract key insights from text
# ---------------------------------------------------------------------------

async def _extract_insights(args: dict, ctx) -> str:
    """
    Ekstrak insight, fakta kunci, dan pattern dari teks panjang.
    Ideal sebagai post-processing setelah web_read atau onamix_get.
    """
    from services.teacher_api import call_teacher, is_teacher_available

    text = args.get("text", "").strip()
    focus = args.get("focus", "")  # optional: topik yang mau difokuskan
    n_insights = int(args.get("n_insights", 7))

    if not text:
        return "ERROR: text wajib diisi"

    focus_str = f"Fokus pada: {focus}" if focus else ""
    system = f"""Kamu adalah insight extractor.
{focus_str}
Ekstrak {n_insights} insight paling valuable dari teks.
Format tiap insight: **[INSIGHT N]** Pernyataan singkat. (Implikasi: apa artinya ini)
Akhiri dengan: **Pola:** [1 kalimat tentang pola besar yang terlihat]"""

    prompt = f"Ekstrak insight dari:\n\n{text[:5000]}"

    teacher = "gemini" if is_teacher_available("gemini") else "kimi"
    try:
        resp = await call_teacher(teacher, prompt=prompt, system=system, max_tokens=800)
        logger.info("extract_insights.ok", text_len=len(text), teacher=teacher)
        return resp.text
    except Exception as e:
        return f"ERROR extract_insights: {e}"


# ---------------------------------------------------------------------------
# J. KNOWLEDGE DISCOVER — Autonomous self-education
# ---------------------------------------------------------------------------

async def _knowledge_discover(args: dict, ctx) -> str:
    """
    Autonomous self-education: pick topic -> research -> synthesize -> save to KB.
    ADO belajar sendiri tanpa input user.
    Gunakan untuk: expand KB, discover new patterns, self-improvement.
    """
    from services.teacher_api import call_teacher, is_teacher_available
    import httpx as _httpx

    topic = args.get("topic", "").strip()
    save_to_kb = args.get("save_to_kb", False)
    depth = args.get("depth", "standard")  # quick | standard | deep

    if not topic:
        return "ERROR: topic wajib diisi"

    steps_log = [f"**[KNOWLEDGE DISCOVER: {topic}]**\n"]

    # Step 1: Search multiple angles
    steps_log.append("**Step 1:** Searching multiple angles...")
    queries = [topic]
    if depth in ("standard", "deep"):
        queries.append(f"{topic} tren 2026")
        queries.append(f"{topic} Indonesia konteks")
    if depth == "deep":
        queries.append(f"{topic} studi kasus")
        queries.append(f"{topic} penelitian terbaru")

    search_results = []
    for q in queries[:3]:
        result = await _tavily_search({"query": q, "max_results": 3}, ctx)
        search_results.append(result)

    # Step 2: Synthesize
    steps_log.append("**Step 2:** Synthesizing findings...")
    synth = await _synthesize({
        "topic": topic,
        "sources": search_results,
        "goal": "Buat knowledge card yang komprehensif untuk ditambahkan ke knowledge base ADO",
        "output_format": "report"
    }, ctx)

    steps_log.append(synth)

    # Step 3: Save to KB (if enabled)
    if save_to_kb:
        steps_log.append("\n**Step 3:** Saving to Knowledge Base...")
        try:
            kb_path = "/opt/ado/data/kb/auto_discovered.md"
            os.makedirs(os.path.dirname(kb_path), exist_ok=True)
            import datetime as _dt
            entry = f"\n\n## {topic} (Auto-discovered {_dt.datetime.utcnow().strftime('%Y-%m-%d')})"
            entry += f"\n\n{synth}"
            with open(kb_path, "a", encoding="utf-8") as f:
                f.write(entry)
            steps_log.append(f"Tersimpan ke: {kb_path}")
        except Exception as e:
            steps_log.append(f"Gagal simpan ke KB: {e}")
    else:
        steps_log.append("\n*(Set save_to_kb=true untuk menyimpan ke Knowledge Base)*")

    logger.info("knowledge_discover.ok", topic=topic, depth=depth, saved=save_to_kb)
    return "\n".join(steps_log)


# ---------------------------------------------------------------------------
# M1.7 Coding Tools — code_analyze, code_debug, code_review, propose_improvement
# ---------------------------------------------------------------------------

async def _code_analyze(args: dict, ctx) -> str:
    from services.teacher_api import call_teacher, is_teacher_available
    code = args.get("code", "").strip()
    language = args.get("language", "auto")
    focus = args.get("focus", "all")
    if not code:
        return "ERROR: code wajib diisi"
    system = (
        f"Kamu adalah senior code reviewer. Analisis kode "
        f"{'ini' if language == 'auto' else language} berikut.\n"
        f"Focus: {focus}. Output format:\n"
        "**ISSUES DITEMUKAN:**\n"
        "- [CRITICAL/HIGH/MEDIUM/LOW] Deskripsi issue dan lokasi\n"
        "**REKOMENDASI:**\n"
        "- Fix konkret per issue\n"
        "**SUMMARY:** Satu kalimat penilaian keseluruhan."
    )
    teacher = "gemini" if is_teacher_available("gemini") else "claude"
    try:
        return await call_teacher(teacher, prompt=f"```\n{code[:4000]}\n```", system=system, max_tokens=1000)
    except Exception as e:
        return f"ERROR code_analyze: {e}"


async def _code_debug(args: dict, ctx) -> str:
    from services.teacher_api import call_teacher, is_teacher_available
    code = args.get("code", "").strip()
    error = args.get("error", "").strip()
    context = args.get("context", "")
    if not code or not error:
        return "ERROR: code dan error wajib diisi"
    system = (
        "Kamu adalah expert debugger. Analisis bug ini.\n"
        "Output:\n"
        "**ROOT CAUSE:** Penjelasan teknis penyebab error\n"
        "**TRACE:** Step-by-step kenapa error terjadi\n"
        "**FIX:** Kode yang sudah diperbaiki (full function/class)\n"
        "**PREVENTION:** Cara hindari di masa depan"
    )
    prompt = f"Code:\n```\n{code[:3000]}\n```\n\nError:\n{error[:500]}\n\nContext: {context[:500]}"
    teacher = "gemini" if is_teacher_available("gemini") else "claude"
    try:
        return await call_teacher(teacher, prompt=prompt, system=system, max_tokens=1200)
    except Exception as e:
        return f"ERROR code_debug: {e}"


async def _code_review(args: dict, ctx) -> str:
    from services.teacher_api import call_teacher, is_teacher_available
    code = args.get("code", "").strip()
    context = args.get("context", "")
    style = args.get("style", "standard")
    if not code:
        return "ERROR: code wajib diisi"
    depth = {"quick": 500, "standard": 1000, "thorough": 1500}.get(style, 1000)
    system = (
        f"Kamu adalah senior engineer melakukan code review "
        f"{'singkat' if style == 'quick' else 'menyeluruh'}.\n"
        f"Context: {context or 'General code review'}\n"
        "Output:\n"
        "**VERDICT:** LGTM ✅ / Request Changes ⚠️ / Block 🚫\n"
        "**HIGHLIGHTS:** Apa yang bagus dari kode ini\n"
        "**ISSUES:** Issues dengan inline reference (baris/fungsi)\n"
        "**SUGGESTIONS:** Perbaikan konkret dengan contoh kode"
    )
    teacher = "gemini" if is_teacher_available("gemini") else "claude"
    try:
        return await call_teacher(teacher, prompt=f"```\n{code[:4000]}\n```", system=system, max_tokens=depth)
    except Exception as e:
        return f"ERROR code_review: {e}"


async def _propose_improvement(args: dict, ctx) -> str:
    import httpx
    from config import settings
    title = args.get("title", "").strip()
    problem = args.get("problem", "").strip()
    if not title or not problem:
        return "ERROR: title dan problem wajib diisi"
    payload = {
        "title": title,
        "problem": problem,
        "hypothesis": args.get("hypothesis", ""),
        "touched_paths": args.get("touched_paths", []),
        "rollback_plan": args.get("rollback_plan", "revert ke commit sebelumnya"),
        "source": args.get("source", "auto"),
        "created_by": getattr(ctx, "agent_id", None) or "core_brain",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "http://localhost:8000/v1/sandbox/proposals",
                json=payload,
                headers={"X-Admin-Key": settings.ADMIN_SECRET_KEY or ""},
            )
        if resp.status_code == 201:
            data = resp.json()
            return (
                f"✅ Proposal berhasil dibuat!\n"
                f"ID: {data['id']}\n"
                f"Risk: {data['risk_level']}\n"
                f"Stage: {data['stage']}\n"
                f"Cek di Playground: https://app.migancore.com/sandbox.html"
            )
        return f"ERROR: API returned {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return f"ERROR propose_improvement: {e}"


# ---------------------------------------------------------------------------
# Registry export — imported by tool_executor.py
# ---------------------------------------------------------------------------

COGNITIVE_TOOLS = {
    "tavily_search":       _tavily_search,
    "serper_search":       _serper_search,
    "think":               _think,
    "synthesize":          _synthesize,
    "teacher_ask":         _teacher_ask,
    "multi_teacher":       _multi_teacher,
    "calculate":           _calculate,
    "run_python":          _run_python,
    "extract_insights":    _extract_insights,
    "knowledge_discover":  _knowledge_discover,
    "code_analyze":        _code_analyze,
    "code_debug":          _code_debug,
    "code_review":         _code_review,
    "propose_improvement": _propose_improvement,
}
