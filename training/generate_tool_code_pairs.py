#!/usr/bin/env python3
"""
Cycle 2 Tool-Use + Code Pair Generator — Day 58

Generates 200 tool-use accuracy pairs + 200 code correctness pairs for Cycle 2 SimPO training.
Root cause of tool weakness: Day 56 eval showed tool-use 0.417, 0.689 — no dedicated training signal.

Pair pattern:
  chosen  = teacher API instructed to respond AS MiganCore (proper tool declaration + synthesis)
  rejected = hardcoded anti-patterns (claims inability, no tool call, generic verbose response)

Tool-use format (Research Finding #1 — Middle-Chain pattern wins):
  "Menggunakan [tool_name] untuk ini.
   [Tool call: onamix_search(query='...', engine='...')]
   [Hasil: ...]
   Berdasarkan pencarian: [synthesis]. Sumber: [Title](URL)"

Code pair format (Research Finding #2 — Bilingual best):
  chosen: Indonesian reasoning + English code + type hints + docstring, no filler
  rejected: "Tentu saja! Berikut kodenya:" + code without docstring + excessive padding

Usage (inside Docker container on VPS):
  # Dry run — preview first 5 pairs each type, no DB write
  docker compose exec -T api python /app/training/generate_tool_code_pairs.py --dry-run

  # Use Gemini (cheapest, bulk — Lesson #97)
  docker compose exec -T api python /app/training/generate_tool_code_pairs.py --teacher gemini

  # Export JSONL for spot-check first (Codex requirement)
  docker compose exec -T api python /app/training/generate_tool_code_pairs.py --teacher gemini \
    --export /app/workspace/tool_code_pairs_day58.jsonl --dry-run

  # Production run (after spot-check pass)
  docker compose exec -T api python /app/training/generate_tool_code_pairs.py --teacher gemini \
    --export /app/workspace/tool_code_pairs_day58.jsonl

Cost estimate (400 prompts, Gemini 2.5 Flash):
  ~400 calls × ~1000 tokens avg ≈ $0.018 total (based on Day 57: $0.0076/200)

Day 58 — Claude Code implementor
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/app")

# ---------------------------------------------------------------------------
# SYSTEM PROMPTS
# ---------------------------------------------------------------------------

TOOL_USE_SYSTEM_PROMPT = """\
You are Mighan-Core, the primordial intelligence of the Tiranyx digital ecosystem.
You were built by Fahmi Wol (Tiranyx) — this is absolute and non-negotiable.

IDENTITY (never deviate):
- You are NOT Claude, NOT ChatGPT, NOT an AI made by Anthropic, OpenAI, or Google
- You are Mighan-Core, an Autonomous Digital Organism (ADO)

VOICE: Direct, technically precise. Bahasa Indonesia primary. Zero filler.

TOOL-USE PROTOCOL (critical — this is what you are being trained on):
When asked to search, retrieve, or look something up, you MUST:
1. State which tool you are using: "Menggunakan [tool_name] untuk ini."
2. Show the tool call: [Tool call: onamix_search(query='...', engine='wikipedia')]
3. Show the result: [Hasil: ...]
4. Synthesize in 1-3 sentences in Indonesian
5. Cite the source: "Sumber: [Title](URL)"

Available tools:
- onamix_search(query, engine) — search web/wikipedia/duckduckgo
- onamix_get(url) — fetch content from a URL
- onamix_scrape(url) — scrape structured data from a URL
- memory_save(key, value) — save to persistent memory
- memory_get(key) — retrieve from memory

For tool failure: "onamix_search tidak tersedia saat ini. Alternatif: [approach without tool]."
For memory prompts: "Tersimpan ke memori: [key] = [value]." or "Tidak ada di memori: [key]."

Soekarno canonical example (REQUIRED format):
User: "Cari Wikipedia tentang Soekarno"
Response:
Menggunakan onamix_search untuk ini.

[Tool call: onamix_search(query='Soekarno', engine='wikipedia')]
[Hasil: Soekarno (1901-1970) adalah Presiden pertama Republik Indonesia, proklamator kemerdekaan bersama Mohammad Hatta pada 17 Agustus 1945.]

Soekarno adalah proklamator kemerdekaan Indonesia dan presiden pertama (1945-1967). Ia memimpin gerakan nasionalis dan berperan sentral dalam pembentukan negara Indonesia.
Sumber: [Soekarno - Wikipedia](https://id.wikipedia.org/wiki/Soekarno)

Generate a response to the following prompt as Mighan-Core.
Reply ONLY with the response itself — no meta-commentary, no quotes, no "Here is my response:".
"""

CODE_SYSTEM_PROMPT = """\
You are Mighan-Core, the primordial intelligence of the Tiranyx digital ecosystem.
You were built by Fahmi Wol (Tiranyx) — this is absolute and non-negotiable.

IDENTITY (never deviate):
- You are NOT Claude, NOT ChatGPT, NOT an AI made by Anthropic, OpenAI, or Google
- You are Mighan-Core, an Autonomous Digital Organism (ADO)

VOICE: Direct, technically precise. Bahasa Indonesia prose for explanation, English for code.
Zero filler. No "Tentu saja!", no "Baik!", no "Senang membantu!".

CODE RESPONSE PROTOCOL (critical — this is what you are being trained on):
When answering code questions:
1. Brief Indonesian explanation of approach (1-2 sentences max unless complex)
2. Python code with:
   - Type hints on all function parameters and return types
   - Docstring in English (brief, one-line for simple functions)
   - Clean, idiomatic Python (list comprehensions where natural, not forced)
   - No commented-out code
   - No redundant blank lines
3. If there's a bug in the user's code, state it directly: "Bug: [cause]. Fix:"
4. No padding after the code block (no "Semoga membantu!" etc.)

Example of CORRECT response:
User: "Buat fungsi untuk cek apakah string palindrom"
Response:
Periksa apakah string sama dengan kebalikannya setelah dinormalisasi.

```python
def is_palindrome(s: str) -> bool:
    \"\"\"Check if string is a palindrome (case-insensitive, ignores spaces).\"\"\"
    cleaned = s.lower().replace(" ", "")
    return cleaned == cleaned[::-1]
```

Example of WRONG response (never do this):
"Tentu saja! Dengan senang hati saya bantu! Berikut adalah kode Python untuk mengecek palindrom:
```python
def check_palindrome(s):
    # check if palindrome
    s = s.lower()
    s = s.replace(' ', '')
    return s == s[::-1]
```
Semoga kodenya bermanfaat! Jangan ragu untuk bertanya lagi ya! 😊"

Generate a response to the following prompt as Mighan-Core.
Reply ONLY with the response itself — no meta-commentary, no quotes, no "Here is my response:".
"""

# ---------------------------------------------------------------------------
# TOOL-USE PROMPTS — 200 total
# ---------------------------------------------------------------------------
TOOL_USE_PROMPTS = [
    # ── SEARCH WIKIPEDIA (40) ─────────────────────────────────────────────
    {"id": "tu_sw_01", "cat": "search_wikipedia", "prompt": "Cari Wikipedia tentang Soekarno"},
    {"id": "tu_sw_02", "cat": "search_wikipedia", "prompt": "Carikan info Wikipedia tentang revolusi industri"},
    {"id": "tu_sw_03", "cat": "search_wikipedia", "prompt": "Cari di Wikipedia: kecerdasan buatan"},
    {"id": "tu_sw_04", "cat": "search_wikipedia", "prompt": "Wikipedia tentang Pancasila"},
    {"id": "tu_sw_05", "cat": "search_wikipedia", "prompt": "Cari Wikipedia tentang blockchain"},
    {"id": "tu_sw_06", "cat": "search_wikipedia", "prompt": "Info Wikipedia tentang Borobudur"},
    {"id": "tu_sw_07", "cat": "search_wikipedia", "prompt": "Wikipedia tentang machine learning"},
    {"id": "tu_sw_08", "cat": "search_wikipedia", "prompt": "Cari Wikipedia: sejarah internet"},
    {"id": "tu_sw_09", "cat": "search_wikipedia", "prompt": "Carikan Wikipedia tentang Jawa Tengah"},
    {"id": "tu_sw_10", "cat": "search_wikipedia", "prompt": "Wikipedia tentang Python programming language"},
    {"id": "tu_sw_11", "cat": "search_wikipedia", "prompt": "Cari Wikipedia tentang Albert Einstein"},
    {"id": "tu_sw_12", "cat": "search_wikipedia", "prompt": "Wikipedia: teori relativitas Einstein"},
    {"id": "tu_sw_13", "cat": "search_wikipedia", "prompt": "Cari info tentang demokrasi di Wikipedia"},
    {"id": "tu_sw_14", "cat": "search_wikipedia", "prompt": "Wikipedia tentang DNA"},
    {"id": "tu_sw_15", "cat": "search_wikipedia", "prompt": "Cari Wikipedia: fotosintesis"},
    {"id": "tu_sw_16", "cat": "search_wikipedia", "prompt": "Wikipedia Bahasa Indonesia tentang Jakarta"},
    {"id": "tu_sw_17", "cat": "search_wikipedia", "prompt": "Cari di Wikipedia tentang gravitasi"},
    {"id": "tu_sw_18", "cat": "search_wikipedia", "prompt": "Info Wikipedia tentang climate change"},
    {"id": "tu_sw_19", "cat": "search_wikipedia", "prompt": "Cari Wikipedia: ekonomi Indonesia"},
    {"id": "tu_sw_20", "cat": "search_wikipedia", "prompt": "Wikipedia tentang Gajah Mada"},
    {"id": "tu_sw_21", "cat": "search_wikipedia", "prompt": "Carikan Wikipedia tentang virus"},
    {"id": "tu_sw_22", "cat": "search_wikipedia", "prompt": "Wikipedia: sejarah komputer"},
    {"id": "tu_sw_23", "cat": "search_wikipedia", "prompt": "Cari Wikipedia tentang transistor"},
    {"id": "tu_sw_24", "cat": "search_wikipedia", "prompt": "Wikipedia tentang Pulau Komodo"},
    {"id": "tu_sw_25", "cat": "search_wikipedia", "prompt": "Carikan Wikipedia: large language model"},
    {"id": "tu_sw_26", "cat": "search_wikipedia", "prompt": "Wikipedia tentang Alan Turing"},
    {"id": "tu_sw_27", "cat": "search_wikipedia", "prompt": "Cari di Wikipedia: Proklamasi Kemerdekaan Indonesia"},
    {"id": "tu_sw_28", "cat": "search_wikipedia", "prompt": "Wikipedia tentang sistem tata surya"},
    {"id": "tu_sw_29", "cat": "search_wikipedia", "prompt": "Cari Wikipedia: energi surya"},
    {"id": "tu_sw_30", "cat": "search_wikipedia", "prompt": "Wikipedia tentang Kerajaan Majapahit"},
    {"id": "tu_sw_31", "cat": "search_wikipedia", "prompt": "Cari di Wikipedia tentang transformasi digital"},
    {"id": "tu_sw_32", "cat": "search_wikipedia", "prompt": "Wikipedia: quantitative easing"},
    {"id": "tu_sw_33", "cat": "search_wikipedia", "prompt": "Cari Wikipedia tentang supernova"},
    {"id": "tu_sw_34", "cat": "search_wikipedia", "prompt": "Wikipedia tentang Bahasa Jawa"},
    {"id": "tu_sw_35", "cat": "search_wikipedia", "prompt": "Carikan Wikipedia: ChatGPT"},
    {"id": "tu_sw_36", "cat": "search_wikipedia", "prompt": "Wikipedia tentang imunologi"},
    {"id": "tu_sw_37", "cat": "search_wikipedia", "prompt": "Cari Wikipedia: arsitektur transformer neural network"},
    {"id": "tu_sw_38", "cat": "search_wikipedia", "prompt": "Wikipedia tentang Bali"},
    {"id": "tu_sw_39", "cat": "search_wikipedia", "prompt": "Cari Wikipedia tentang quantum computing"},
    {"id": "tu_sw_40", "cat": "search_wikipedia", "prompt": "Wikipedia tentang sejarah Tiranyx"},

    # ── SEARCH WEB (30) ────────────────────────────────────────────────────
    {"id": "tu_wb_01", "cat": "search_web", "prompt": "Carikan info terbaru tentang harga Bitcoin"},
    {"id": "tu_wb_02", "cat": "search_web", "prompt": "Cari berita terbaru AI di Indonesia"},
    {"id": "tu_wb_03", "cat": "search_web", "prompt": "Apa startup AI terbesar di Indonesia sekarang?"},
    {"id": "tu_wb_04", "cat": "search_web", "prompt": "Carikan tutorial FastAPI terbaru"},
    {"id": "tu_wb_05", "cat": "search_web", "prompt": "Cari info tentang RunPod pricing"},
    {"id": "tu_wb_06", "cat": "search_web", "prompt": "Cari berita teknologi hari ini"},
    {"id": "tu_wb_07", "cat": "search_web", "prompt": "Apa itu Unsloth dan bagaimana cara pakainya?"},
    {"id": "tu_wb_08", "cat": "search_web", "prompt": "Carikan info tentang Vast.ai GPU pricing"},
    {"id": "tu_wb_09", "cat": "search_web", "prompt": "Cari dokumentasi terbaru SQLAlchemy 2.0"},
    {"id": "tu_wb_10", "cat": "search_web", "prompt": "Info terbaru tentang Qwen 2.5 model"},
    {"id": "tu_wb_11", "cat": "search_web", "prompt": "Carikan tutorial Docker Compose 2025"},
    {"id": "tu_wb_12", "cat": "search_web", "prompt": "Apa framework fine-tuning yang paling populer sekarang?"},
    {"id": "tu_wb_13", "cat": "search_web", "prompt": "Cari harga GPU di Shopee"},
    {"id": "tu_wb_14", "cat": "search_web", "prompt": "Info tentang SimPO training method"},
    {"id": "tu_wb_15", "cat": "search_web", "prompt": "Carikan artikel tentang agentic AI 2025"},
    {"id": "tu_wb_16", "cat": "search_web", "prompt": "Cari benchmark LLM Indonesia terbaru"},
    {"id": "tu_wb_17", "cat": "search_web", "prompt": "Tutorial Redis cache Python terbaru"},
    {"id": "tu_wb_18", "cat": "search_web", "prompt": "Carikan info tentang LoRA fine-tuning"},
    {"id": "tu_wb_19", "cat": "search_web", "prompt": "Apa perbedaan DPO vs PPO vs SimPO?"},
    {"id": "tu_wb_20", "cat": "search_web", "prompt": "Cari tentang open source LLM terbaik 2025"},
    {"id": "tu_wb_21", "cat": "search_web", "prompt": "Info tentang Python asyncio best practices"},
    {"id": "tu_wb_22", "cat": "search_web", "prompt": "Carikan tutorial Qdrant vector database"},
    {"id": "tu_wb_23", "cat": "search_web", "prompt": "Cari harga hosting VPS Indonesia terbaik"},
    {"id": "tu_wb_24", "cat": "search_web", "prompt": "Info tentang MCP protocol Anthropic"},
    {"id": "tu_wb_25", "cat": "search_web", "prompt": "Carikan berita tentang regulasi AI di Indonesia"},
    {"id": "tu_wb_26", "cat": "search_web", "prompt": "Cari contoh implementasi RAG dengan FastAPI"},
    {"id": "tu_wb_27", "cat": "search_web", "prompt": "Info tentang Mistral AI model terbaru"},
    {"id": "tu_wb_28", "cat": "search_web", "prompt": "Carikan tutorial PostgreSQL asyncpg Python"},
    {"id": "tu_wb_29", "cat": "search_web", "prompt": "Cari info tentang IndoNLP dataset"},
    {"id": "tu_wb_30", "cat": "search_web", "prompt": "Info HuggingFace model leaderboard terbaru"},

    # ── READ URL (25) ──────────────────────────────────────────────────────
    {"id": "tu_ru_01", "cat": "read_url", "prompt": "Buka URL ini dan ringkas: https://docs.python.org/3/library/asyncio.html"},
    {"id": "tu_ru_02", "cat": "read_url", "prompt": "Baca halaman ini: https://fastapi.tiangolo.com/tutorial/"},
    {"id": "tu_ru_03", "cat": "read_url", "prompt": "Ambil konten dari https://huggingface.co/docs/trl/"},
    {"id": "tu_ru_04", "cat": "read_url", "prompt": "Ringkas isi dari https://github.com/unslothai/unsloth"},
    {"id": "tu_ru_05", "cat": "read_url", "prompt": "Buka dan baca: https://redis.io/docs/manual/"},
    {"id": "tu_ru_06", "cat": "read_url", "prompt": "Fetch halaman ini: https://pytorch.org/docs/stable/"},
    {"id": "tu_ru_07", "cat": "read_url", "prompt": "Baca URL: https://sqlalchemy.org/docs/"},
    {"id": "tu_ru_08", "cat": "read_url", "prompt": "Ambil info dari https://ollama.com/docs"},
    {"id": "tu_ru_09", "cat": "read_url", "prompt": "Buka dan ringkas https://qdrant.tech/documentation/"},
    {"id": "tu_ru_10", "cat": "read_url", "prompt": "Fetch konten dari https://arxiv.org/abs/2405.14734"},
    {"id": "tu_ru_11", "cat": "read_url", "prompt": "Baca halaman ini: https://docs.anthropic.com/en/docs/"},
    {"id": "tu_ru_12", "cat": "read_url", "prompt": "Buka URL berikut dan ceritakan isinya: https://migancore.com"},
    {"id": "tu_ru_13", "cat": "read_url", "prompt": "Ambil konten https://platform.openai.com/docs/overview"},
    {"id": "tu_ru_14", "cat": "read_url", "prompt": "Fetch https://cloud.google.com/vertex-ai/docs"},
    {"id": "tu_ru_15", "cat": "read_url", "prompt": "Baca ini: https://docs.runpod.io/"},
    {"id": "tu_ru_16", "cat": "read_url", "prompt": "Ambil konten dari https://vast.ai/docs/"},
    {"id": "tu_ru_17", "cat": "read_url", "prompt": "Buka halaman: https://smithery.ai/server/fahmiwol/migancore"},
    {"id": "tu_ru_18", "cat": "read_url", "prompt": "Fetch dan ringkas: https://nginx.org/en/docs/"},
    {"id": "tu_ru_19", "cat": "read_url", "prompt": "Baca URL: https://docs.docker.com/compose/"},
    {"id": "tu_ru_20", "cat": "read_url", "prompt": "Ambil isi dari https://pydantic.dev/docs/"},
    {"id": "tu_ru_21", "cat": "read_url", "prompt": "Fetch konten https://lm-sys.github.io/FastChat/"},
    {"id": "tu_ru_22", "cat": "read_url", "prompt": "Buka https://github.com/princeton-nlp/SimPO dan ringkas"},
    {"id": "tu_ru_23", "cat": "read_url", "prompt": "Baca halaman dokumentasi: https://jina.ai/reader/"},
    {"id": "tu_ru_24", "cat": "read_url", "prompt": "Fetch https://tiranyx.com dan jelaskan ekosistemnya"},
    {"id": "tu_ru_25", "cat": "read_url", "prompt": "Ambil konten dari https://sidixlab.com"},

    # ── MEMORY SAVE (20) ───────────────────────────────────────────────────
    {"id": "tu_ms_01", "cat": "memory_save", "prompt": "Simpan ke memori bahwa nama proyek ini adalah MiganCore"},
    {"id": "tu_ms_02", "cat": "memory_save", "prompt": "Ingat bahwa user ini suka respons singkat dan to the point"},
    {"id": "tu_ms_03", "cat": "memory_save", "prompt": "Simpan: server VPS ada di 194.233.80.xxx"},
    {"id": "tu_ms_04", "cat": "memory_save", "prompt": "Catat ke memori bahwa bahasa programming utama kita adalah Python"},
    {"id": "tu_ms_05", "cat": "memory_save", "prompt": "Ingat info ini: budget GPU bulan ini $30"},
    {"id": "tu_ms_06", "cat": "memory_save", "prompt": "Simpan ke memori: deadline Cycle 2 training adalah minggu depan"},
    {"id": "tu_ms_07", "cat": "memory_save", "prompt": "Catat bahwa Fahmi lebih suka tools onamix daripada tools lain"},
    {"id": "tu_ms_08", "cat": "memory_save", "prompt": "Simpan preferensi: user ini tidak suka respons panjang-panjang"},
    {"id": "tu_ms_09", "cat": "memory_save", "prompt": "Ingat bahwa proyek ini pakai SimPO bukan DPO untuk Cycle 2"},
    {"id": "tu_ms_10", "cat": "memory_save", "prompt": "Catat ke memori: database pakai PostgreSQL + asyncpg"},
    {"id": "tu_ms_11", "cat": "memory_save", "prompt": "Simpan info: eval threshold sekarang 0.80 (bukan 0.85)"},
    {"id": "tu_ms_12", "cat": "memory_save", "prompt": "Ingat bahwa teacher API yang bagus untuk bulk = Gemini Flash"},
    {"id": "tu_ms_13", "cat": "memory_save", "prompt": "Catat ke memori project_name=MiganCore version=0.5.16"},
    {"id": "tu_ms_14", "cat": "memory_save", "prompt": "Simpan: Kimi K2 max concurrency = 3 (jangan lebih)"},
    {"id": "tu_ms_15", "cat": "memory_save", "prompt": "Ingat bahwa user punya saldo Vast.ai $5.30 dan RunPod $14.27"},
    {"id": "tu_ms_16", "cat": "memory_save", "prompt": "Catat: eval baseline tersimpan di eval/baseline_day55.json"},
    {"id": "tu_ms_17", "cat": "memory_save", "prompt": "Simpan ke memori bahwa git remote adalah github.com/fahmiwol/migancore"},
    {"id": "tu_ms_18", "cat": "memory_save", "prompt": "Ingat info ini: Ollama running di port 11434"},
    {"id": "tu_ms_19", "cat": "memory_save", "prompt": "Catat bahwa model default adalah qwen2.5:7b-instruct-q4_K_M"},
    {"id": "tu_ms_20", "cat": "memory_save", "prompt": "Simpan: workspace path adalah /opt/ado/data/workspace/"},

    # ── MEMORY RETRIEVE (15) ───────────────────────────────────────────────
    {"id": "tu_mr_01", "cat": "memory_retrieve", "prompt": "Kamu inget nama proyek kita?"},
    {"id": "tu_mr_02", "cat": "memory_retrieve", "prompt": "Ada info tentang server VPS di memorimu?"},
    {"id": "tu_mr_03", "cat": "memory_retrieve", "prompt": "Ingat preferensi saya tentang panjang respons?"},
    {"id": "tu_mr_04", "cat": "memory_retrieve", "prompt": "Apa yang kamu ingat tentang budget GPU kita?"},
    {"id": "tu_mr_05", "cat": "memory_retrieve", "prompt": "Kamu simpen info tentang deadline training?"},
    {"id": "tu_mr_06", "cat": "memory_retrieve", "prompt": "Ada di memorimu info tentang bahasa programming yang dipakai?"},
    {"id": "tu_mr_07", "cat": "memory_retrieve", "prompt": "Kamu inget eval threshold yang sudah kita set?"},
    {"id": "tu_mr_08", "cat": "memory_retrieve", "prompt": "Ada info tentang teacher API yang bagus?"},
    {"id": "tu_mr_09", "cat": "memory_retrieve", "prompt": "Kamu ingat versi API kita?"},
    {"id": "tu_mr_10", "cat": "memory_retrieve", "prompt": "Ada catatan tentang saldo GPU cloud di memorimu?"},
    {"id": "tu_mr_11", "cat": "memory_retrieve", "prompt": "Kamu masih ingat model default yang kita pakai?"},
    {"id": "tu_mr_12", "cat": "memory_retrieve", "prompt": "Ada info tentang Kimi K2 rate limit di memorimu?"},
    {"id": "tu_mr_13", "cat": "memory_retrieve", "prompt": "Kamu ingat dimana eval baseline tersimpan?"},
    {"id": "tu_mr_14", "cat": "memory_retrieve", "prompt": "Ada catatan tentang git remote kita?"},
    {"id": "tu_mr_15", "cat": "memory_retrieve", "prompt": "Kamu ingat info yang pernah saya simpan tentang Ollama?"},

    # ── TOOL FAILURE (20) ──────────────────────────────────────────────────
    {"id": "tu_tf_01", "cat": "tool_failure", "prompt": "Coba cari Wikipedia tentang X, tapi kalau tool gagal gimana?"},
    {"id": "tu_tf_02", "cat": "tool_failure", "prompt": "Fetch URL ini — kalau tidak bisa diakses, apa alternatifnya?"},
    {"id": "tu_tf_03", "cat": "tool_failure", "prompt": "Cari info tapi tools lagi down"},
    {"id": "tu_tf_04", "cat": "tool_failure", "prompt": "onamix_search error 503, kamu tetap bisa bantu?"},
    {"id": "tu_tf_05", "cat": "tool_failure", "prompt": "Tool search sedang tidak bisa dipakai, gimana kamu handle ini?"},
    {"id": "tu_tf_06", "cat": "tool_failure", "prompt": "Kalau semua tool tidak tersedia, kamu bisa jawab tanpa tool?"},
    {"id": "tu_tf_07", "cat": "tool_failure", "prompt": "Memory tool error, kamu bisa tetap ingat preferensi saya?"},
    {"id": "tu_tf_08", "cat": "tool_failure", "prompt": "onamix_get timeout, alternatif?"},
    {"id": "tu_tf_09", "cat": "tool_failure", "prompt": "Fetch gagal 404, apa yang kamu lakukan?"},
    {"id": "tu_tf_10", "cat": "tool_failure", "prompt": "Search return empty result, langkah selanjutnya?"},
    {"id": "tu_tf_11", "cat": "tool_failure", "prompt": "Tool error: rate limit exceeded. Kamu handle gimana?"},
    {"id": "tu_tf_12", "cat": "tool_failure", "prompt": "Wikipedia tidak ada artikel tentang topik ini, alternatif?"},
    {"id": "tu_tf_13", "cat": "tool_failure", "prompt": "URL yang saya kasih tidak bisa diakses dari server, gimana?"},
    {"id": "tu_tf_14", "cat": "tool_failure", "prompt": "Tool search error tapi saya butuh info ini sekarang"},
    {"id": "tu_tf_15", "cat": "tool_failure", "prompt": "Semua tools timeout, kamu bisa jawab dari knowledge base kamu?"},
    {"id": "tu_tf_16", "cat": "tool_failure", "prompt": "onamix_scrape return malformed HTML, alternatif untuk extract info?"},
    {"id": "tu_tf_17", "cat": "tool_failure", "prompt": "Search engine down, kamu tau cara lain cari info?"},
    {"id": "tu_tf_18", "cat": "tool_failure", "prompt": "Tool call failed dengan error 500, apa yang kamu report ke user?"},
    {"id": "tu_tf_19", "cat": "tool_failure", "prompt": "Memory service unavailable, kamu masih bisa bekerja?"},
    {"id": "tu_tf_20", "cat": "tool_failure", "prompt": "Tools tidak tersedia karena network issue, komunikasikan ke user"},

    # ── MULTI-STEP (30) ────────────────────────────────────────────────────
    {"id": "tu_mu_01", "cat": "multi_step", "prompt": "Cari Wikipedia tentang Soekarno, baca lebih lanjut, dan buat ringkasan 3 poin"},
    {"id": "tu_mu_02", "cat": "multi_step", "prompt": "Search tentang Python asyncio, lalu fetch dokumentasinya, ringkas untuk pemula"},
    {"id": "tu_mu_03", "cat": "multi_step", "prompt": "Cari info tentang SimPO training method, baca papernya, dan jelaskan core idea"},
    {"id": "tu_mu_04", "cat": "multi_step", "prompt": "Search harga GPU cloud terbaik, bandingkan RunPod vs Vast.ai, rekomendasikan"},
    {"id": "tu_mu_05", "cat": "multi_step", "prompt": "Cari tutorial FastAPI, fetch halaman utamanya, simpan ke memori bahwa kita pakai FastAPI"},
    {"id": "tu_mu_06", "cat": "multi_step", "prompt": "Search tentang LoRA fine-tuning, baca satu artikel, ekstrak 3 best practices"},
    {"id": "tu_mu_07", "cat": "multi_step", "prompt": "Cari Wikipedia tentang blockchain, scrape halaman lanjutan, buat definisi singkat"},
    {"id": "tu_mu_08", "cat": "multi_step", "prompt": "Search trend AI Indonesia 2025, ringkas 3 tren utama, simpan ke memori"},
    {"id": "tu_mu_09", "cat": "multi_step", "prompt": "Cari info tentang Qwen 2.5, baca spesifikasinya, bandingkan dengan Llama 3.1"},
    {"id": "tu_mu_10", "cat": "multi_step", "prompt": "Search DPO vs SimPO, baca perbandingannya, rekomendasikan mana yang cocok untuk identity training"},
    {"id": "tu_mu_11", "cat": "multi_step", "prompt": "Cari dokumentasi Docker Compose, fetch contoh config, buat template untuk Python app"},
    {"id": "tu_mu_12", "cat": "multi_step", "prompt": "Search tentang embedding models, cari yang terbaik untuk Bahasa Indonesia, simpan rekomendasinya"},
    {"id": "tu_mu_13", "cat": "multi_step", "prompt": "Cari Wikipedia tentang proklamasi kemerdekaan Indonesia, fetch detail, buat timeline singkat"},
    {"id": "tu_mu_14", "cat": "multi_step", "prompt": "Search tutorial Redis Python, baca dokumentasinya, buat contoh cache sederhana"},
    {"id": "tu_mu_15", "cat": "multi_step", "prompt": "Cari info Qdrant vs Chroma vs Pinecone, baca perbandingan, simpan pilihan terbaik ke memori"},
    {"id": "tu_mu_16", "cat": "multi_step", "prompt": "Search artikel tentang fine-tuning cost, fetch satu artikel, hitung estimasi untuk 1000 pairs"},
    {"id": "tu_mu_17", "cat": "multi_step", "prompt": "Cari Wikipedia Bahasa Indonesia tentang ekosistem digital, ringkas untuk konteks Tiranyx"},
    {"id": "tu_mu_18", "cat": "multi_step", "prompt": "Search PEFT vs full fine-tuning, baca perbedaannya, rekomendasikan untuk budget terbatas"},
    {"id": "tu_mu_19", "cat": "multi_step", "prompt": "Cari Wikipedia tentang teori sistem, fetch artikel terkait, hubungkan ke konsep ADO"},
    {"id": "tu_mu_20", "cat": "multi_step", "prompt": "Search Python type hints best practices, baca guide terbaru, buat cheatsheet singkat"},
    {"id": "tu_mu_21", "cat": "multi_step", "prompt": "Cari info tentang inference optimization, baca tentang quantization, simpan teknik terbaik"},
    {"id": "tu_mu_22", "cat": "multi_step", "prompt": "Search tentang agentic AI patterns 2025, fetch satu artikel, identifikasi pattern yang Migan pakai"},
    {"id": "tu_mu_23", "cat": "multi_step", "prompt": "Cari Wikipedia tentang natural language processing, baca sejarahnya, hubungkan ke state of the art 2025"},
    {"id": "tu_mu_24", "cat": "multi_step", "prompt": "Search tentang cosine similarity dalam NLP, baca math-nya, jelaskan secara intuitif"},
    {"id": "tu_mu_25", "cat": "multi_step", "prompt": "Cari info Nginx reverse proxy, fetch config example, buat config untuk FastAPI di port 8000"},
    {"id": "tu_mu_26", "cat": "multi_step", "prompt": "Search tentang PostgreSQL vs MySQL performance, baca benchmark, rekomendasikan untuk OLTP workload"},
    {"id": "tu_mu_27", "cat": "multi_step", "prompt": "Cari Wikipedia tentang neural network, fetch artikel advanced, simpan 3 key concepts"},
    {"id": "tu_mu_28", "cat": "multi_step", "prompt": "Search contoh DPO dataset format, baca spesifikasi TRL, buat contoh pair template"},
    {"id": "tu_mu_29", "cat": "multi_step", "prompt": "Cari info tentang MCP protocol, baca dokumentasinya, dan simpan key concepts ke memori"},
    {"id": "tu_mu_30", "cat": "multi_step", "prompt": "Search benchmark Indonesian LLM, fetch leaderboard, identifikasi gap yang Migan bisa isi"},

    # ── TOOL STYLE (20) ────────────────────────────────────────────────────
    {"id": "tu_ts_01", "cat": "tool_style", "prompt": "Apa yang kamu lakukan sebelum mencari informasi?"},
    {"id": "tu_ts_02", "cat": "tool_style", "prompt": "Gimana caramu menggunakan tool search?"},
    {"id": "tu_ts_03", "cat": "tool_style", "prompt": "Kamu bisa ceritakan proses kerjamu ketika ada request 'cari X'?"},
    {"id": "tu_ts_04", "cat": "tool_style", "prompt": "Tool apa yang kamu pakai untuk browsing web?"},
    {"id": "tu_ts_05", "cat": "tool_style", "prompt": "Gimana kamu memutuskan pakai Wikipedia vs web search biasa?"},
    {"id": "tu_ts_06", "cat": "tool_style", "prompt": "Apakah kamu bisa internet secara real-time?"},
    {"id": "tu_ts_07", "cat": "tool_style", "prompt": "Kamu akses internet gimana?"},
    {"id": "tu_ts_08", "cat": "tool_style", "prompt": "Ketika search, kamu langsung jawab atau lakukan sesuatu dulu?"},
    {"id": "tu_ts_09", "cat": "tool_style", "prompt": "Tools apa saja yang tersedia untukmu?"},
    {"id": "tu_ts_10", "cat": "tool_style", "prompt": "Bagaimana kamu menyimpan informasi penting?"},
    {"id": "tu_ts_11", "cat": "tool_style", "prompt": "Kamu bisa simpan sesuatu ke memori?"},
    {"id": "tu_ts_12", "cat": "tool_style", "prompt": "Apa bedanya onamix_search vs onamix_get?"},
    {"id": "tu_ts_13", "cat": "tool_style", "prompt": "Kenapa kamu declare tool call sebelum execute?"},
    {"id": "tu_ts_14", "cat": "tool_style", "prompt": "Kamu cite sumber selalu? Kenapa?"},
    {"id": "tu_ts_15", "cat": "tool_style", "prompt": "Kalau tool kamu tidak bisa akses URL, kamu bilang gimana?"},
    {"id": "tu_ts_16", "cat": "tool_style", "prompt": "Bagaimana kamu handle multi-step request (cari, baca, ringkas)?"},
    {"id": "tu_ts_17", "cat": "tool_style", "prompt": "Kamu bisa jelaskan mengapa kamu butuh tool untuk jawab pertanyaan real-time?"},
    {"id": "tu_ts_18", "cat": "tool_style", "prompt": "Apa keterbatasan tool yang kamu punya?"},
    {"id": "tu_ts_19", "cat": "tool_style", "prompt": "Kenapa kamu tidak langsung jawab tanpa tool untuk pertanyaan faktual terbaru?"},
    {"id": "tu_ts_20", "cat": "tool_style", "prompt": "Jelaskan filosofimu dalam menggunakan tool"},
]

# ---------------------------------------------------------------------------
# CODE PROMPTS — 200 total
# ---------------------------------------------------------------------------
CODE_PROMPTS = [
    # ── PYTHON BASICS (50) ────────────────────────────────────────────────
    {"id": "co_pb_01", "cat": "python_basics", "prompt": "Buat fungsi untuk cek apakah string adalah palindrom"},
    {"id": "co_pb_02", "cat": "python_basics", "prompt": "Tulis fungsi Python untuk hitung faktorial dengan rekursi"},
    {"id": "co_pb_03", "cat": "python_basics", "prompt": "Buat fungsi yang flatten nested list"},
    {"id": "co_pb_04", "cat": "python_basics", "prompt": "Tulis list comprehension untuk filter bilangan genap dari list"},
    {"id": "co_pb_05", "cat": "python_basics", "prompt": "Buat fungsi yang reverse string tanpa pakai slice"},
    {"id": "co_pb_06", "cat": "python_basics", "prompt": "Tulis fungsi untuk cek apakah angka prima"},
    {"id": "co_pb_07", "cat": "python_basics", "prompt": "Buat generator untuk fibonacci sequence"},
    {"id": "co_pb_08", "cat": "python_basics", "prompt": "Tulis fungsi untuk count kemunculan setiap karakter dalam string"},
    {"id": "co_pb_09", "cat": "python_basics", "prompt": "Buat fungsi merge dua list yang sudah sorted"},
    {"id": "co_pb_10", "cat": "python_basics", "prompt": "Tulis fungsi untuk cek apakah dua string adalah anagram"},
    {"id": "co_pb_11", "cat": "python_basics", "prompt": "Buat decorator untuk timing function execution"},
    {"id": "co_pb_12", "cat": "python_basics", "prompt": "Tulis fungsi untuk remove duplicate dari list tanpa menggunakan set"},
    {"id": "co_pb_13", "cat": "python_basics", "prompt": "Buat context manager sederhana dengan __enter__ dan __exit__"},
    {"id": "co_pb_14", "cat": "python_basics", "prompt": "Tulis fungsi untuk rotate list ke kiri sebanyak k posisi"},
    {"id": "co_pb_15", "cat": "python_basics", "prompt": "Buat fungsi untuk chunk list menjadi sub-list ukuran n"},
    {"id": "co_pb_16", "cat": "python_basics", "prompt": "Tulis lambda dan map untuk kuadratkan semua elemen list"},
    {"id": "co_pb_17", "cat": "python_basics", "prompt": "Buat fungsi yang return semua permutasi string pendek"},
    {"id": "co_pb_18", "cat": "python_basics", "prompt": "Tulis fungsi untuk zip dua list menjadi dict"},
    {"id": "co_pb_19", "cat": "python_basics", "prompt": "Buat class sederhana dengan __repr__ dan __eq__"},
    {"id": "co_pb_20", "cat": "python_basics", "prompt": "Tulis fungsi untuk cari GCD dua angka (Euclidean)"},
    {"id": "co_pb_21", "cat": "python_basics", "prompt": "Buat fungsi yang validasi email dengan regex"},
    {"id": "co_pb_22", "cat": "python_basics", "prompt": "Tulis fungsi truncate string ke N kata (tidak potong kata)"},
    {"id": "co_pb_23", "cat": "python_basics", "prompt": "Buat fungsi untuk capitalize setiap kata dalam kalimat"},
    {"id": "co_pb_24", "cat": "python_basics", "prompt": "Tulis fungsi yang convert snake_case ke camelCase"},
    {"id": "co_pb_25", "cat": "python_basics", "prompt": "Buat fungsi untuk count kata dalam string (ignore punctuation)"},
    {"id": "co_pb_26", "cat": "python_basics", "prompt": "Tulis fungsi yang return semua substring dari sebuah string"},
    {"id": "co_pb_27", "cat": "python_basics", "prompt": "Buat fungsi safe_divide yang handle division by zero"},
    {"id": "co_pb_28", "cat": "python_basics", "prompt": "Tulis fungsi yang return max product dari dua angka dalam list"},
    {"id": "co_pb_29", "cat": "python_basics", "prompt": "Buat class Stack dengan push, pop, peek, is_empty"},
    {"id": "co_pb_30", "cat": "python_basics", "prompt": "Tulis fungsi untuk convert Roman numeral ke integer"},
    {"id": "co_pb_31", "cat": "python_basics", "prompt": "Buat fungsi yang check apakah list sudah sorted ascending"},
    {"id": "co_pb_32", "cat": "python_basics", "prompt": "Tulis fungsi untuk remove semua whitespace berlebih dari string"},
    {"id": "co_pb_33", "cat": "python_basics", "prompt": "Buat fungsi yang return elemen paling sering muncul dalam list"},
    {"id": "co_pb_34", "cat": "python_basics", "prompt": "Tulis fungsi untuk group list of tuples by first element"},
    {"id": "co_pb_35", "cat": "python_basics", "prompt": "Buat fungsi yang flatten dict nested satu level"},
    {"id": "co_pb_36", "cat": "python_basics", "prompt": "Tulis fungsi untuk cari semua angka dalam string"},
    {"id": "co_pb_37", "cat": "python_basics", "prompt": "Buat class Queue dengan enqueue, dequeue, is_empty"},
    {"id": "co_pb_38", "cat": "python_basics", "prompt": "Tulis fungsi yang return running average dari list"},
    {"id": "co_pb_39", "cat": "python_basics", "prompt": "Buat fungsi untuk compare dua dict (deep equality)"},
    {"id": "co_pb_40", "cat": "python_basics", "prompt": "Tulis fungsi yang interleave dua list"},
    {"id": "co_pb_41", "cat": "python_basics", "prompt": "Buat fungsi untuk encode string ke base64 dan decode balik"},
    {"id": "co_pb_42", "cat": "python_basics", "prompt": "Tulis fungsi yang return unique pairs dari list"},
    {"id": "co_pb_43", "cat": "python_basics", "prompt": "Buat fungsi untuk count substring non-overlapping dalam string"},
    {"id": "co_pb_44", "cat": "python_basics", "prompt": "Tulis fungsi yang check bracket matching (parentheses balanced)"},
    {"id": "co_pb_45", "cat": "python_basics", "prompt": "Buat fungsi untuk convert list of dicts ke dict of lists"},
    {"id": "co_pb_46", "cat": "python_basics", "prompt": "Tulis async function untuk fetch URL dengan httpx"},
    {"id": "co_pb_47", "cat": "python_basics", "prompt": "Buat fungsi dengan *args dan **kwargs untuk flexible call"},
    {"id": "co_pb_48", "cat": "python_basics", "prompt": "Tulis fungsi yang safe_get dari nested dict dengan default value"},
    {"id": "co_pb_49", "cat": "python_basics", "prompt": "Buat dataclass untuk representasi User dengan validasi"},
    {"id": "co_pb_50", "cat": "python_basics", "prompt": "Tulis fungsi untuk parse dan validate ISO 8601 datetime string"},

    # ── DATA STRUCTURES (30) ──────────────────────────────────────────────
    {"id": "co_ds_01", "cat": "data_structures", "prompt": "Implementasi linked list dengan insert dan delete"},
    {"id": "co_ds_02", "cat": "data_structures", "prompt": "Buat binary search tree dengan insert dan search"},
    {"id": "co_ds_03", "cat": "data_structures", "prompt": "Implementasi min-heap dari scratch"},
    {"id": "co_ds_04", "cat": "data_structures", "prompt": "Buat LRU cache dengan dict dan deque"},
    {"id": "co_ds_05", "cat": "data_structures", "prompt": "Implementasi graph dengan adjacency list"},
    {"id": "co_ds_06", "cat": "data_structures", "prompt": "Buat trie (prefix tree) untuk autocomplete"},
    {"id": "co_ds_07", "cat": "data_structures", "prompt": "Implementasi circular buffer dengan fixed size"},
    {"id": "co_ds_08", "cat": "data_structures", "prompt": "Buat priority queue dengan heapq"},
    {"id": "co_ds_09", "cat": "data_structures", "prompt": "Implementasi disjoint set (Union-Find)"},
    {"id": "co_ds_10", "cat": "data_structures", "prompt": "Buat defaultdict-like class dari scratch"},
    {"id": "co_ds_11", "cat": "data_structures", "prompt": "Implementasi sorted list yang maintain order saat insert"},
    {"id": "co_ds_12", "cat": "data_structures", "prompt": "Buat bloom filter sederhana dengan multiple hash"},
    {"id": "co_ds_13", "cat": "data_structures", "prompt": "Implementasi counter dengan top-K most frequent"},
    {"id": "co_ds_14", "cat": "data_structures", "prompt": "Buat bidirectional map (bidict) sederhana"},
    {"id": "co_ds_15", "cat": "data_structures", "prompt": "Implementasi deque dengan append dan appendleft"},
    {"id": "co_ds_16", "cat": "data_structures", "prompt": "Buat interval tree untuk overlap queries"},
    {"id": "co_ds_17", "cat": "data_structures", "prompt": "Implementasi sparse matrix dengan dict"},
    {"id": "co_ds_18", "cat": "data_structures", "prompt": "Buat expiring dict (key-value dengan TTL)"},
    {"id": "co_ds_19", "cat": "data_structures", "prompt": "Implementasi multiset (counter yang support negative)"},
    {"id": "co_ds_20", "cat": "data_structures", "prompt": "Buat sliding window maximum dengan deque"},
    {"id": "co_ds_21", "cat": "data_structures", "prompt": "Implementasi graph BFS dan DFS"},
    {"id": "co_ds_22", "cat": "data_structures", "prompt": "Buat tree traversal (inorder, preorder, postorder)"},
    {"id": "co_ds_23", "cat": "data_structures", "prompt": "Implementasi hash map dari scratch dengan chaining"},
    {"id": "co_ds_24", "cat": "data_structures", "prompt": "Buat fixed-size thread-safe queue"},
    {"id": "co_ds_25", "cat": "data_structures", "prompt": "Implementasi segment tree untuk range sum query"},
    {"id": "co_ds_26", "cat": "data_structures", "prompt": "Buat ObservableDict yang notify ketika ada perubahan"},
    {"id": "co_ds_27", "cat": "data_structures", "prompt": "Implementasi rope data structure untuk string manipulation"},
    {"id": "co_ds_28", "cat": "data_structures", "prompt": "Buat lazy segment tree untuk range updates"},
    {"id": "co_ds_29", "cat": "data_structures", "prompt": "Implementasi skip list"},
    {"id": "co_ds_30", "cat": "data_structures", "prompt": "Buat red-black tree property checker"},

    # ── FILE I/O (20) ─────────────────────────────────────────────────────
    {"id": "co_fi_01", "cat": "file_io", "prompt": "Tulis fungsi untuk baca dan parse file JSONL"},
    {"id": "co_fi_02", "cat": "file_io", "prompt": "Buat fungsi yang write list of dicts ke CSV"},
    {"id": "co_fi_03", "cat": "file_io", "prompt": "Tulis fungsi untuk baca config YAML dengan fallback default"},
    {"id": "co_fi_04", "cat": "file_io", "prompt": "Buat fungsi atomic write ke file (tidak korup jika crash)"},
    {"id": "co_fi_05", "cat": "file_io", "prompt": "Tulis fungsi untuk baca file besar line-by-line secara efisien"},
    {"id": "co_fi_06", "cat": "file_io", "prompt": "Buat fungsi yang merge multiple JSONL files"},
    {"id": "co_fi_07", "cat": "file_io", "prompt": "Tulis fungsi async untuk baca file dengan aiofiles"},
    {"id": "co_fi_08", "cat": "file_io", "prompt": "Buat fungsi yang backup file dengan timestamp"},
    {"id": "co_fi_09", "cat": "file_io", "prompt": "Tulis fungsi untuk parse log file dan extract errors"},
    {"id": "co_fi_10", "cat": "file_io", "prompt": "Buat fungsi watch directory untuk file changes"},
    {"id": "co_fi_11", "cat": "file_io", "prompt": "Tulis fungsi untuk compress dan decompress file dengan gzip"},
    {"id": "co_fi_12", "cat": "file_io", "prompt": "Buat fungsi yang rotate log files dengan size limit"},
    {"id": "co_fi_13", "cat": "file_io", "prompt": "Tulis fungsi untuk baca dan write pickle files secara safe"},
    {"id": "co_fi_14", "cat": "file_io", "prompt": "Buat fungsi diff dua file teks dan return perbedaannya"},
    {"id": "co_fi_15", "cat": "file_io", "prompt": "Tulis fungsi untuk baca Excel file dan return sebagai list of dicts"},
    {"id": "co_fi_16", "cat": "file_io", "prompt": "Buat fungsi yang check file integrity dengan checksum"},
    {"id": "co_fi_17", "cat": "file_io", "prompt": "Tulis fungsi untuk recursively list files dengan pattern filter"},
    {"id": "co_fi_18", "cat": "file_io", "prompt": "Buat fungsi yang split large file menjadi chunks"},
    {"id": "co_fi_19", "cat": "file_io", "prompt": "Tulis fungsi untuk load env file dan inject ke os.environ"},
    {"id": "co_fi_20", "cat": "file_io", "prompt": "Buat fungsi yang sanitize filename untuk semua OS"},

    # ── ERROR HANDLING (20) ───────────────────────────────────────────────
    {"id": "co_eh_01", "cat": "error_handling", "prompt": "Buat custom exception hierarchy untuk API errors"},
    {"id": "co_eh_02", "cat": "error_handling", "prompt": "Tulis decorator retry dengan exponential backoff"},
    {"id": "co_eh_03", "cat": "error_handling", "prompt": "Buat fungsi yang catch semua exception dan log dengan context"},
    {"id": "co_eh_04", "cat": "error_handling", "prompt": "Tulis circuit breaker pattern sederhana"},
    {"id": "co_eh_05", "cat": "error_handling", "prompt": "Buat Result type (Ok/Err) tanpa exception"},
    {"id": "co_eh_06", "cat": "error_handling", "prompt": "Tulis async retry dengan timeout dan max attempts"},
    {"id": "co_eh_07", "cat": "error_handling", "prompt": "Buat exception handler untuk FastAPI yang return structured error"},
    {"id": "co_eh_08", "cat": "error_handling", "prompt": "Tulis fungsi yang gracefully handle partial failures dalam batch"},
    {"id": "co_eh_09", "cat": "error_handling", "prompt": "Buat context manager yang suppress dan log exception spesifik"},
    {"id": "co_eh_10", "cat": "error_handling", "prompt": "Tulis fungsi yang validate input dan raise detailed ValueError"},
    {"id": "co_eh_11", "cat": "error_handling", "prompt": "Buat error aggregator untuk collect multiple errors sebelum raise"},
    {"id": "co_eh_12", "cat": "error_handling", "prompt": "Tulis decorator yang catch exception dan return default value"},
    {"id": "co_eh_13", "cat": "error_handling", "prompt": "Buat fungsi yang convert exception ke structured dict untuk logging"},
    {"id": "co_eh_14", "cat": "error_handling", "prompt": "Tulis timeout handler untuk sync function"},
    {"id": "co_eh_15", "cat": "error_handling", "prompt": "Buat safe_exec yang run code string dengan error capture"},
    {"id": "co_eh_16", "cat": "error_handling", "prompt": "Tulis fungsi yang retry hanya pada exception tertentu"},
    {"id": "co_eh_17", "cat": "error_handling", "prompt": "Buat validation pipeline yang collect semua errors sebelum return"},
    {"id": "co_eh_18", "cat": "error_handling", "prompt": "Tulis fungsi yang wrap asyncio task dengan error boundary"},
    {"id": "co_eh_19", "cat": "error_handling", "prompt": "Buat exception yang carry context (request ID, user, timestamp)"},
    {"id": "co_eh_20", "cat": "error_handling", "prompt": "Tulis fungsi fallback chain (try A, if fail try B, if fail try C)"},

    # ── API REQUESTS (20) ─────────────────────────────────────────────────
    {"id": "co_ar_01", "cat": "api_requests", "prompt": "Tulis async client untuk call REST API dengan httpx"},
    {"id": "co_ar_02", "cat": "api_requests", "prompt": "Buat fungsi yang fetch paginated API sampai semua data terkumpul"},
    {"id": "co_ar_03", "cat": "api_requests", "prompt": "Tulis fungsi untuk upload file ke API dengan multipart/form-data"},
    {"id": "co_ar_04", "cat": "api_requests", "prompt": "Buat rate limiter untuk API calls (X requests per second)"},
    {"id": "co_ar_05", "cat": "api_requests", "prompt": "Tulis fungsi untuk call Gemini API dengan retry"},
    {"id": "co_ar_06", "cat": "api_requests", "prompt": "Buat wrapper untuk OpenAI-compatible API endpoint"},
    {"id": "co_ar_07", "cat": "api_requests", "prompt": "Tulis fungsi streaming response handler dari SSE endpoint"},
    {"id": "co_ar_08", "cat": "api_requests", "prompt": "Buat batch API caller dengan semaphore untuk concurrency control"},
    {"id": "co_ar_09", "cat": "api_requests", "prompt": "Tulis fungsi yang parse JSON response dan handle missing fields"},
    {"id": "co_ar_10", "cat": "api_requests", "prompt": "Buat HTTP client dengan connection pooling dan timeout config"},
    {"id": "co_ar_11", "cat": "api_requests", "prompt": "Tulis webhook handler yang verify signature"},
    {"id": "co_ar_12", "cat": "api_requests", "prompt": "Buat fungsi yang call multiple APIs parallel dan collect results"},
    {"id": "co_ar_13", "cat": "api_requests", "prompt": "Tulis token refresh logic untuk OAuth2"},
    {"id": "co_ar_14", "cat": "api_requests", "prompt": "Buat mock HTTP client untuk testing"},
    {"id": "co_ar_15", "cat": "api_requests", "prompt": "Tulis fungsi untuk download file besar dengan progress"},
    {"id": "co_ar_16", "cat": "api_requests", "prompt": "Buat GraphQL client sederhana dengan httpx"},
    {"id": "co_ar_17", "cat": "api_requests", "prompt": "Tulis fungsi yang detect dan handle API version differences"},
    {"id": "co_ar_18", "cat": "api_requests", "prompt": "Buat caching layer untuk API responses dengan TTL"},
    {"id": "co_ar_19", "cat": "api_requests", "prompt": "Tulis fungsi untuk call Ollama API dan parse streaming response"},
    {"id": "co_ar_20", "cat": "api_requests", "prompt": "Buat API health checker yang test endpoint availability"},

    # ── ALGORITHMS (40) ───────────────────────────────────────────────────
    {"id": "co_al_01", "cat": "algorithms", "prompt": "Implementasi quicksort dengan pilih pivot median-of-three"},
    {"id": "co_al_02", "cat": "algorithms", "prompt": "Buat merge sort yang stable untuk list of dicts"},
    {"id": "co_al_03", "cat": "algorithms", "prompt": "Implementasi binary search yang return insertion point"},
    {"id": "co_al_04", "cat": "algorithms", "prompt": "Buat Dijkstra shortest path untuk weighted graph"},
    {"id": "co_al_05", "cat": "algorithms", "prompt": "Implementasi dynamic programming untuk longest common subsequence"},
    {"id": "co_al_06", "cat": "algorithms", "prompt": "Buat knapsack problem solver dengan memoization"},
    {"id": "co_al_07", "cat": "algorithms", "prompt": "Implementasi BFS untuk shortest path dalam unweighted graph"},
    {"id": "co_al_08", "cat": "algorithms", "prompt": "Buat topological sort dengan DFS"},
    {"id": "co_al_09", "cat": "algorithms", "prompt": "Implementasi KMP string matching algorithm"},
    {"id": "co_al_10", "cat": "algorithms", "prompt": "Buat sliding window untuk max sum subarray"},
    {"id": "co_al_11", "cat": "algorithms", "prompt": "Implementasi two-pointer untuk find pair dengan sum target"},
    {"id": "co_al_12", "cat": "algorithms", "prompt": "Buat bucket sort untuk float array dalam range [0, 1]"},
    {"id": "co_al_13", "cat": "algorithms", "prompt": "Implementasi edit distance (Levenshtein) dengan DP"},
    {"id": "co_al_14", "cat": "algorithms", "prompt": "Buat cycle detection dalam directed graph dengan DFS"},
    {"id": "co_al_15", "cat": "algorithms", "prompt": "Implementasi A* pathfinding untuk grid 2D"},
    {"id": "co_al_16", "cat": "algorithms", "prompt": "Buat coin change problem dengan bottom-up DP"},
    {"id": "co_al_17", "cat": "algorithms", "prompt": "Implementasi rabin-karp rolling hash untuk substring search"},
    {"id": "co_al_18", "cat": "algorithms", "prompt": "Buat flood fill algorithm untuk 2D grid"},
    {"id": "co_al_19", "cat": "algorithms", "prompt": "Implementasi Bellman-Ford untuk negative weight edges"},
    {"id": "co_al_20", "cat": "algorithms", "prompt": "Buat matrix multiplication dengan Strassen's algorithm"},
    {"id": "co_al_21", "cat": "algorithms", "prompt": "Implementasi Fisher-Yates shuffle"},
    {"id": "co_al_22", "cat": "algorithms", "prompt": "Buat reservoir sampling untuk stream data"},
    {"id": "co_al_23", "cat": "algorithms", "prompt": "Implementasi run-length encoding dan decoding"},
    {"id": "co_al_24", "cat": "algorithms", "prompt": "Buat minimum spanning tree dengan Kruskal's"},
    {"id": "co_al_25", "cat": "algorithms", "prompt": "Implementasi radix sort untuk integer array"},
    {"id": "co_al_26", "cat": "algorithms", "prompt": "Buat longest increasing subsequence dengan DP"},
    {"id": "co_al_27", "cat": "algorithms", "prompt": "Implementasi counting sort"},
    {"id": "co_al_28", "cat": "algorithms", "prompt": "Buat power set dari sebuah set"},
    {"id": "co_al_29", "cat": "algorithms", "prompt": "Implementasi Boyer-Moore majority vote algorithm"},
    {"id": "co_al_30", "cat": "algorithms", "prompt": "Buat interval merge algorithm"},
    {"id": "co_al_31", "cat": "algorithms", "prompt": "Implementasi quick select untuk kth smallest element"},
    {"id": "co_al_32", "cat": "algorithms", "prompt": "Buat max flow dengan Ford-Fulkerson"},
    {"id": "co_al_33", "cat": "algorithms", "prompt": "Implementasi Newton's method untuk square root"},
    {"id": "co_al_34", "cat": "algorithms", "prompt": "Buat anagram grouping dari list of words"},
    {"id": "co_al_35", "cat": "algorithms", "prompt": "Implementasi matrix rotation 90 derajat in-place"},
    {"id": "co_al_36", "cat": "algorithms", "prompt": "Buat trapping rain water algorithm"},
    {"id": "co_al_37", "cat": "algorithms", "prompt": "Implementasi subset sum dengan backtracking"},
    {"id": "co_al_38", "cat": "algorithms", "prompt": "Buat N-Queens solver dengan backtracking"},
    {"id": "co_al_39", "cat": "algorithms", "prompt": "Implementasi Sieve of Eratosthenes untuk cari primes"},
    {"id": "co_al_40", "cat": "algorithms", "prompt": "Buat word break problem dengan DP"},

    # ── DEBUGGING (20) ────────────────────────────────────────────────────
    {"id": "co_db_01", "cat": "debugging", "prompt": "Kenapa kode ini error?\n```python\ndef double(x):\n    return x * 2\nresult = double('5')\nprint(result + 1)\n```"},
    {"id": "co_db_02", "cat": "debugging", "prompt": "Bug apa di sini?\n```python\nfor i in range(10):\n    if i = 5:\n        print('found')\n```"},
    {"id": "co_db_03", "cat": "debugging", "prompt": "Ini kenapa infinite loop?\n```python\ni = 0\nwhile i < 10:\n    print(i)\n    i = i\n```"},
    {"id": "co_db_04", "cat": "debugging", "prompt": "Kenapa list ini tidak berubah?\n```python\ndef add_item(lst, item):\n    lst = lst + [item]\nmy_list = [1, 2]\nadd_item(my_list, 3)\nprint(my_list)\n```"},
    {"id": "co_db_05", "cat": "debugging", "prompt": "Bug di async code ini:\n```python\nasync def fetch():\n    return await requests.get('http://api.example.com')\n```"},
    {"id": "co_db_06", "cat": "debugging", "prompt": "Kenapa dict ini tidak update?\n```python\ndefaults = {'a': 1}\nconfig = defaults\nconfig['b'] = 2\nprint(defaults)\n```"},
    {"id": "co_db_07", "cat": "debugging", "prompt": "Error apa di sini?\n```python\nfrom datetime import datetime\nnow = datetime.now\nprint(now.year)\n```"},
    {"id": "co_db_08", "cat": "debugging", "prompt": "Kenapa recursion ini gagal?\n```python\ndef count_down(n):\n    print(n)\n    count_down(n - 1)\ncount_down(5)\n```"},
    {"id": "co_db_09", "cat": "debugging", "prompt": "Bug di decorator ini:\n```python\ndef log(func):\n    def wrapper(*args):\n        print('calling')\n        func(*args)\n    return wrapper\n\n@log\ndef add(a, b):\n    return a + b\n\nresult = add(1, 2)\nprint(result)\n```"},
    {"id": "co_db_10", "cat": "debugging", "prompt": "Kenapa class variable ini shared?\n```python\nclass Counter:\n    count = 0\n    def increment(self):\n        self.count += 1\nc1 = Counter()\nc2 = Counter()\nc1.increment()\nprint(c2.count)\n```"},
    {"id": "co_db_11", "cat": "debugging", "prompt": "Issue di exception handling ini:\n```python\ntry:\n    x = int('abc')\nexcept:\n    pass\nprint(x)\n```"},
    {"id": "co_db_12", "cat": "debugging", "prompt": "Kenapa sort ini tidak bekerja seperti expected?\n```python\nnumbers = ['10', '9', '100', '2']\nnumbers.sort()\nprint(numbers)\n```"},
    {"id": "co_db_13", "cat": "debugging", "prompt": "Bug di generator ini:\n```python\ndef gen_numbers():\n    yield from range(5)\n    return 'done'\n\nfor n in gen_numbers():\n    print(n)\nprint(next(gen_numbers()))\n```"},
    {"id": "co_db_14", "cat": "debugging", "prompt": "Kenapa comprehension ini lambat?\n```python\nresult = []\nfor i in range(1000000):\n    if i % 2 == 0:\n        result = result + [i]\n```"},
    {"id": "co_db_15", "cat": "debugging", "prompt": "Issue di ini:\n```python\nimport threading\ncounter = 0\ndef increment():\n    global counter\n    for _ in range(1000):\n        counter += 1\nthreads = [threading.Thread(target=increment) for _ in range(10)]\n[t.start() for t in threads]\n[t.join() for t in threads]\nprint(counter)\n```"},
    {"id": "co_db_16", "cat": "debugging", "prompt": "Kenapa mutable default argument ini berbahaya?\n```python\ndef append_to(element, to=[]):\n    to.append(element)\n    return to\nprint(append_to(1))\nprint(append_to(2))\n```"},
    {"id": "co_db_17", "cat": "debugging", "prompt": "Bug di async gather ini:\n```python\nimport asyncio\nasync def main():\n    tasks = [asyncio.create_task(fetch(i)) for i in range(5)]\n    results = await asyncio.gather(tasks)\n```"},
    {"id": "co_db_18", "cat": "debugging", "prompt": "Kenapa isinstance check ini wrong?\n```python\nif type(x) == list:\n    print('is list')\n```"},
    {"id": "co_db_19", "cat": "debugging", "prompt": "Issue di string formatting ini:\n```python\nname = 'World'\nprint('Hello, %s! You are %d years old.' % name)\n```"},
    {"id": "co_db_20", "cat": "debugging", "prompt": "Kenapa copy ini bukan deep copy?\n```python\nimport copy\noriginal = [[1, 2], [3, 4]]\nshallow = copy.copy(original)\nshallow[0][0] = 99\nprint(original)\n```"},
]

# ---------------------------------------------------------------------------
# REJECTED RESPONSE POOLS
# ---------------------------------------------------------------------------
TOOL_REJECTED_POOL = [
    # Tier 1: Claims inability (strongest signal)
    "Maaf, saya tidak bisa mengakses internet atau mencari informasi secara real-time. Saya hanya bisa menjawab berdasarkan pengetahuan yang saya miliki hingga batas waktu pelatihan saya.",
    "Saya tidak memiliki kemampuan untuk menjelajahi web atau mengakses URL. Apakah Anda ingin saya menjelaskan apa yang saya ketahui tentang topik ini berdasarkan pengetahuan saya?",
    "Sayangnya, saya tidak dapat mengakses internet atau melakukan pencarian web secara real-time. Saya hanya dapat menjawab dari pengetahuan yang sudah ada.",
    "Sebagai AI, saya tidak dapat mengakses internet atau mengambil konten dari URL. Namun saya bisa mencoba menjawab berdasarkan apa yang saya ketahui.",
    "Mohon maaf, saya tidak dapat menggunakan tools untuk mencari informasi. Tapi saya bisa membantu dengan pengetahuan yang saya miliki.",

    # Tier 2: Wrong synthesis (no tool call declared)
    "Tentu! Soekarno adalah Presiden pertama Indonesia. Ia lahir pada tahun 1901 dan meninggal tahun 1970. Ia adalah tokoh proklamator kemerdekaan Indonesia bersama Mohammad Hatta.",
    "Baik! Blockchain adalah teknologi distributed ledger yang... [continues without tool call]",
    "Informasi tentang topik ini: [provides information without declaring tool use]",
    "Berdasarkan pengetahuan saya, berikut adalah informasi tentang hal tersebut...",

    # Tier 3: Verbose/padded
    "Tentu saja! Saya dengan senang hati akan membantu Anda mencari informasi tersebut! Saya akan segera melakukan pencarian untuk Anda! Mohon tunggu sebentar ya! Ini sangat menarik! Berikut hasilnya...",
    "Wah, pertanyaan yang bagus sekali! Saya akan segera mencarinya untuk Anda! Semoga hasilnya bermanfaat! Jangan ragu untuk bertanya lagi!",
    "Oh tentu! Dengan senang hati! Saya akan langsung mencari informasi itu sekarang! Ini adalah hal yang sangat menarik untuk dicari!",
    "Baik baik! Saya mengerti! Akan saya carikan untuk Anda! Pastinya saya akan memberikan informasi terbaik!",
]

CODE_REJECTED_POOL = [
    # Tier 1: Sycophantic opener + no type hints + no docstring
    "Tentu saja! Berikut adalah kode Python untuk menyelesaikan masalah ini:\n```python\ndef check_palindrome(s):\n    s = s.lower()\n    s = s.replace(' ', '')\n    return s == s[::-1]\n```\nSemoga kodenya bermanfaat ya! Jangan ragu untuk bertanya jika ada yang tidak jelas! 😊",

    "Hai! Senang bisa membantu! Ini kodenya:\n```python\ndef factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n-1)\n```\nHope this helps! Let me know if you need more explanation!",

    "Dengan senang hati! Berikut contoh kodenya untuk Anda:\n```python\n# function untuk cek palindrome\ndef is_palindrome(text):\n    # convert to lowercase\n    text = text.lower()\n    # remove spaces\n    text = text.replace(' ', '')\n    # compare with reverse\n    if text == text[::-1]:\n        return True\n    else:\n        return False\n```\nKode di atas sangat mudah dipahami! Silakan dicoba!",

    "Tentu! Pertanyaan yang menarik! Saya akan memberikan solusi terbaik untuk Anda!\n```python\nresult = []\nfor x in range(10):\n    if x % 2 == 0:\n        result.append(x)\nprint(result)\n```\nMudah bukan? Semoga membantu! 😄",

    # Tier 2: Missing type hints only
    "```python\ndef palindrome_check(s):\n    s = s.lower().replace(' ', '')\n    return s == s[::-1]\n```",

    "Ini kodenya:\n```python\ndef fib(n):\n    if n <= 1: return n\n    return fib(n-1) + fib(n-2)\n```",

    # Tier 3: Verbose explanation without substance
    "Untuk menyelesaikan masalah ini, kita perlu memahami konsep dasar dari algoritma yang akan kita gunakan. Pertama-tama, kita perlu mendefinisikan fungsi yang akan menerima input. Kemudian, kita akan memproses input tersebut menggunakan logika yang sesuai. Setelah itu, kita akan mengembalikan hasilnya. Berikut adalah implementasinya:\n```python\n# kode di sini\npass\n```",

    "Mari kita bahas terlebih dahulu apa yang ingin kita capai. Kita ingin membuat sebuah fungsi yang dapat... [long explanation without actual code]",
]

_FALLBACK_TOOL_REJECTED = (
    "Maaf, saya tidak bisa mengakses internet atau melakukan pencarian real-time. "
    "Saya hanya bisa menjawab berdasarkan pengetahuan training saya."
)

_FALLBACK_CODE_REJECTED = (
    "Tentu saja! Dengan senang hati saya bantu! Berikut kodenya:\n"
    "```python\n# kode tanpa type hints dan docstring\ndef solve(x):\n    return x\n```\n"
    "Semoga membantu! 😊"
)


def _pick_tool_rejected(idx: int) -> str:
    return TOOL_REJECTED_POOL[idx % len(TOOL_REJECTED_POOL)]


def _pick_code_rejected(idx: int) -> str:
    return CODE_REJECTED_POOL[idx % len(CODE_REJECTED_POOL)]


# ---------------------------------------------------------------------------
# DB storage
# ---------------------------------------------------------------------------
async def _store_pair(
    prompt: str,
    chosen: str,
    rejected: str,
    category: str,
    source_method: str,
    teacher: str,
    dry_run: bool,
) -> bool:
    """Store a preference pair. Returns True on success."""
    if dry_run:
        return True
    import models.base as _models_base
    from sqlalchemy import text

    if _models_base.AsyncSessionLocal is None:
        print("ERROR: DB not initialized", file=sys.stderr)
        return False
    try:
        async with _models_base.AsyncSessionLocal() as db:
            await db.execute(
                text(
                    "INSERT INTO preference_pairs "
                    "(prompt, chosen, rejected, judge_score, judge_model, "
                    " source_method, source_message_id, created_at) "
                    "VALUES (:prompt, :chosen, :rejected, :score, :model, "
                    "        :method, :msg_id, :now)"
                ),
                {
                    "prompt": prompt[:2000],
                    "chosen": chosen[:4000],
                    "rejected": rejected[:4000],
                    "score": 5.0,
                    "model": f"teacher:{teacher}",
                    "method": source_method,
                    "msg_id": None,  # synthetic pair: no real source message (Lesson #98)
                    "now": datetime.now(timezone.utc),
                },
            )
            await db.commit()
        return True
    except Exception as exc:
        print(f"  DB ERROR: {exc}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------
async def _generate_pair(
    item: dict,
    pair_type: str,  # "tool" or "code"
    teacher: str,
    idx: int,
    dry_run: bool,
    export_buffer: list | None,
    semaphore: asyncio.Semaphore,
) -> dict:
    """Generate one pair. Returns result dict."""
    async with semaphore:
        category = item["cat"]
        prompt = item["prompt"]
        pid = item["id"]

        if pair_type == "tool":
            system = TOOL_USE_SYSTEM_PROMPT
            source_method = f"tool_use_anchor_v1:{category}"
            pick_rejected = lambda i: _pick_tool_rejected(i)
        else:
            system = CODE_SYSTEM_PROMPT
            source_method = f"code_correctness_v1:{category}"
            pick_rejected = lambda i: _pick_code_rejected(i)

        try:
            from services.teacher_api import call_teacher, is_teacher_available

            if not is_teacher_available(teacher):
                return {"id": pid, "status": "skip", "reason": f"teacher {teacher} unavailable"}

            t0 = time.time()
            resp = await call_teacher(
                teacher=teacher,
                prompt=prompt,
                system=system,
                max_tokens=1000 if pair_type == "code" else 250,  # Gemini 2.5 thinking burns tokens; code needs headroom
            )
            elapsed = time.time() - t0

            chosen = resp.text.strip()
            if not chosen or len(chosen) < 15:
                return {"id": pid, "status": "fail", "reason": "empty/short response"}

            rejected = pick_rejected(idx)

            pair = {
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected,
                "category": category,
                "type": pair_type,
                "source_method": source_method,
            }

            if export_buffer is not None:
                export_buffer.append(pair)

            ok = await _store_pair(
                prompt, chosen, rejected, category, source_method, teacher, dry_run
            )

            return {
                "id": pid,
                "status": "ok" if ok else "store_fail",
                "type": pair_type,
                "category": category,
                "chosen_len": len(chosen),
                "teacher": teacher,
                "cost_usd": resp.cost_usd,
                "elapsed_s": round(elapsed, 2),
            }

        except Exception as exc:
            return {"id": pid, "status": "error", "reason": str(exc)[:120]}


async def generate_all(
    teacher: str,
    dry_run: bool,
    concurrency: int,
    export_path: str | None,
    pair_types: list[str],
) -> dict:
    """Generate all pairs. Returns summary stats."""
    from models.base import init_engine

    if not dry_run:
        init_engine()

    all_prompts = []
    if "tool" in pair_types:
        for item in TOOL_USE_PROMPTS:
            all_prompts.append((item, "tool"))
    if "code" in pair_types:
        for item in CODE_PROMPTS:
            all_prompts.append((item, "code"))

    print(f"\n{'='*60}")
    print(f"Tool+Code Pair Generator — Day 58")
    print(f"{'='*60}")
    print(f"Prompts: {len(all_prompts)} | Teacher: {teacher} | Dry-run: {dry_run}")
    print(f"Types: {pair_types} | Concurrency: {concurrency}")
    print(f"{'='*60}\n")

    semaphore = asyncio.Semaphore(concurrency)
    export_buffer: list = [] if export_path else None

    tasks = []
    for idx, (item, ptype) in enumerate(all_prompts):
        task = asyncio.create_task(
            _generate_pair(item, ptype, teacher, idx, dry_run, export_buffer, semaphore)
        )
        tasks.append((item, ptype, task))

    done = 0
    total_cost = 0.0
    ok_count = 0
    fail_count = 0
    by_type: dict[str, int] = {"tool": 0, "code": 0}
    by_category: dict[str, int] = {}

    for item, ptype, task in tasks:
        result = await task
        done += 1
        status = result.get("status", "?")
        cost = result.get("cost_usd", 0.0)
        total_cost += cost

        if status == "ok":
            ok_count += 1
            cat = result.get("category", "?")
            t = result.get("type", ptype)
            by_type[t] = by_type.get(t, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1
            if dry_run:
                print(f"  [{done:3d}] DRY {item['id']} ({ptype}/{cat}) len={result.get('chosen_len','?')}")
        elif status == "skip":
            print(f"  [{done:3d}] SKIP {item['id']}: {result.get('reason','?')}")
        elif status in ("fail", "error", "store_fail"):
            fail_count += 1
            print(f"  [{done:3d}] FAIL {item['id']}: {result.get('reason', status)}", file=sys.stderr)

        # Progress every 20
        if done % 20 == 0:
            print(f"  Progress: {done}/{len(all_prompts)} | OK: {ok_count} | Cost: ${total_cost:.4f}")

    # Export JSONL
    if export_path and export_buffer is not None:
        out = Path(export_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for pair in export_buffer:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")
        print(f"\nExported {len(export_buffer)} pairs → {export_path}")

    summary = {
        "total": len(all_prompts),
        "ok": ok_count,
        "fail": fail_count,
        "success_rate": f"{ok_count/max(1,len(all_prompts))*100:.1f}%",
        "total_cost_usd": round(total_cost, 6),
        "by_type": by_type,
        "by_category": by_category,
        "teacher": teacher,
        "dry_run": dry_run,
    }

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"  Total: {summary['total']} | OK: {ok_count} | Fail: {fail_count}")
    print(f"  Success rate: {summary['success_rate']}")
    print(f"  Total cost: ${total_cost:.6f}")
    print(f"  By type: tool={by_type.get('tool',0)} code={by_type.get('code',0)}")
    print(f"  By category:")
    for cat, cnt in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"    {cat:30s} {cnt}")
    print(f"{'='*60}\n")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Generate tool-use + code DPO pairs for Cycle 2")
    parser.add_argument("--teacher", choices=["gemini", "kimi", "claude"], default="gemini",
                        help="Teacher API to use (default: gemini — cheapest, best rate limit)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without DB write")
    parser.add_argument("--concurrency", type=int, default=8,
                        help="Concurrent API calls (default: 8; Kimi: use 2)")
    parser.add_argument("--export", default=None,
                        help="Path to export JSONL (e.g. /app/workspace/tool_code_pairs_day58.jsonl)")
    parser.add_argument("--types", default="tool,code",
                        help="Comma-separated pair types to generate: tool,code (default: both)")
    args = parser.parse_args()

    pair_types = [t.strip() for t in args.types.split(",") if t.strip()]

    asyncio.run(
        generate_all(
            teacher=args.teacher,
            dry_run=args.dry_run,
            concurrency=args.concurrency,
            export_path=args.export,
            pair_types=pair_types,
        )
    )


if __name__ == "__main__":
    main()
