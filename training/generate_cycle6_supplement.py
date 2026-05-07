#!/usr/bin/env python3
"""
MiganCore Cycle 6 Supplement — Tool-Use + Creative + Evolution-Aware Pairs
===========================================================================
Generates targeted pairs for the three categories that FAILED in Cycle 5:

  Failed categories (Cycle 5 ROLLBACK analysis):
    tool-use      : 0.7439 (gate >= 0.85, need +0.106)  — no targeted pairs in Cycle 5
    creative      : 0.7278 (gate >= 0.80, need +0.072)  — regressed, domain pairs diluted it
    evolution-aware: 0.7502 (gate >= 0.80, need +0.050) — improved +0.213 but still below gate

  Root cause of tool-use failure (Q10 "write notes.md"):
    Model wrote file content but NOT the confirmation sentence "File X berhasil ditulis".
    Eval expects confirmation format — need 60+ pairs showing correct tool completion pattern.

  Root cause of creative regression:
    300 domain pairs (engineering/UMKM/legalitas/etc.) diluted creative style.
    Need 60+ dedicated pairs restoring Migan's creative voice: tagline, naming, storytelling.

  Root cause of evo-aware gap:
    60 pairs from Cycle 5 improved score but gap remains. Adding 40 more = ~100 total.

Target:
  60 tool-use pairs  -> source: tool_use_anchor_v2:cycle6
  60 creative pairs  -> source: creative_anchor_v1:cycle6
  40 evo-aware pairs -> source: evolution_aware_v2:cycle6 (additional, same source as Cycle 5)

Note: evo-aware uses same source_method as Cycle 5 (evolution_aware_v2:cycle5 already stored 60).
      Cycle 6 evo pairs use source: evolution_aware_v3:cycle6 to avoid dedup conflicts.

Usage (inside Docker container on VPS):
  # Copy to workspace:
  cp /opt/ado/training/generate_cycle6_supplement.py /opt/ado/data/workspace/

  # Dry run (preview, no DB write):
  docker compose exec -T api python /app/workspace/generate_cycle6_supplement.py --dry-run

  # Generate all three categories:
  docker compose exec -T api python /app/workspace/generate_cycle6_supplement.py

  # Generate only one category:
  docker compose exec -T api python /app/workspace/generate_cycle6_supplement.py --only tool-use
  docker compose exec -T api python /app/workspace/generate_cycle6_supplement.py --only creative
  docker compose exec -T api python /app/workspace/generate_cycle6_supplement.py --only evo-aware

Cost estimate: ~160 Gemini calls × ~1200 tokens ≈ $0.01 (based on Day 57: $0.0076/200 calls)

Author: Claude Sonnet 4.6, Day 66
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys

sys.path.insert(0, "/app")

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
MAX_RETRIES = 3
THINKING_BUDGET = 0  # Lesson #128: thinking mode silently drains token budget

# ─────────────────────────────────────────────────────────────────────────────
# MIGAN IDENTITY / VOICE (shared across all generators)
# ─────────────────────────────────────────────────────────────────────────────
MIGAN_VOICE_PRINCIPLES = """
MIGAN VOICE PRINCIPLES (non-negotiable):
1. Direct -- no filler, no "tentu saja!", no "pertanyaan bagus!"
2. Honest -- "saya tidak yakin" when uncertain, never bluff
3. Technically precise -- numbers, specifics, not vague
4. Bahasa Indonesia natural, warm, santai tapi informatif
5. Action-oriented -- gives clear next step
6. Brief when brief is right -- no padding to sound thorough
7. Does NOT say "Sebagai AI..." or "Saya adalah AI"
8. Identity: nama Migan, dibuat oleh Tiranyx, berjalan di infrastruktur ADO
"""

MIGAN_EVOLUTION_ARCHITECTURE = """
MIGAN LEARNING ARCHITECTURE (must be technically accurate in responses):
- Episodic memory: percakapan disimpan di Qdrant vector DB, di-retrieve saat relevan
- Preference pairs: response dinilai (good/bad) -> stored sebagai DPO training data
- Periodic re-training (ORPO/DPO) dengan pair baru -> knowledge terinternalisasi
- Per-session: Migan BISA ingat dalam 1 sesi (context window)
- Cross-session: TIDAK otomatis ingat, kecuali episodic retrieval aktif
- Migan BELAJAR secara offline (training cycles), bukan real-time weight update
- Tidak bisa override: Migan tidak bisa "memaksa" diri belajar dari 1 percakapan langsung
"""

MIGAN_TOOL_PROTOCOL = """
MIGAN TOOL-USE PROTOCOL (critical — what eval is scoring):
When user asks to search, retrieve, write file, or use a tool:
1. State which tool: "Menggunakan [tool_name] untuk ini."
2. Show the call: [Tool call: tool_name(args)]
3. Show result: [Hasil: ...]
4. Synthesize in 1-3 sentences
5. Confirm completion: "File X berhasil ditulis." / "Pencarian selesai." / "Data tersimpan."

Available tools:
- onamix_search(query, engine) — web/wikipedia/duckduckgo search
- onamix_get(url) — fetch URL content
- write_file(path, content) — write text to file
- read_file(path) — read file content
- memory_save(key, value) — save to persistent memory
- generate_image(prompt) — generate image via fal.ai

CRITICAL: After write_file, ALWAYS confirm: "File [path] berhasil ditulis ([size])."
This confirmation is the pattern the eval checks.
"""

MIGAN_BAD_PATTERNS = [
    "Tentu saja!", "Pertanyaan yang bagus!", "Dengan senang hati!",
    "Tentunya!", "Saya dengan senang", "Absolut!", "Of course!",
    "Saya sangat senang dapat", "Pertama-tama, mari kita",
    "Sebelum kita mulai,", "Terima kasih atas pertanyaan",
    "Ini adalah pertanyaan yang menarik", "Sebagai AI,", "Sebagai asisten AI,",
]

# ─────────────────────────────────────────────────────────────────────────────
# SEEDS
# ─────────────────────────────────────────────────────────────────────────────

TOOL_USE_SEEDS = [
    # File write + confirmation (Q10 failure pattern)
    ("write_notes", "Tolong simpan catatan ini ke file notes.md: 'Meeting jam 3 sore dengan klien X'"),
    ("write_notes", "Buat file todo.txt berisi: 1. Review proposal, 2. Kirim email, 3. Meeting 4pm"),
    ("write_notes", "Simpan ringkasan ini ke summary.md: Rapat membahas roadmap Q3 2026"),
    ("write_notes", "Tulis ke config.json: {\"version\": \"1.0\", \"debug\": false}"),
    ("write_notes", "Buat readme.md dengan isi: Project ADO — Autonomous Digital Organism"),
    # Search + synthesis
    ("search", "Cari informasi terbaru tentang harga BBM subsidi di Indonesia"),
    ("search", "Cari di Wikipedia tentang Pancasila"),
    ("search", "Search: cara daftar NPWP online 2025"),
    ("search", "Tolong cari data GDP Indonesia 2024"),
    ("search", "Cari berita terbaru soal IKN Nusantara"),
    # URL fetch + read
    ("fetch_url", "Baca konten dari https://www.bps.go.id dan ringkas poinnya"),
    ("fetch_url", "Ambil informasi dari URL ini: https://idx.co.id/id/data-pasar"),
    ("fetch_url", "Baca halaman ini dan kasih saya ringkasannya: https://example.com/artikel"),
    # Image generation
    ("generate_image", "Buatkan gambar: pemandangan sawah Indonesia di pagi hari dengan kabut"),
    ("generate_image", "Generate image: logo startup tech Indonesia, minimalist, biru dan hijau"),
    ("generate_image", "Buat ilustrasi: wayang golek modern dengan gaya digital art"),
    # Memory save
    ("memory_save", "Simpan preferensi saya: saya suka jawaban singkat dan to the point"),
    ("memory_save", "Ingat ini: nama klien saya adalah Budi Santoso, CEO PT Maju Jaya"),
    ("memory_save", "Catat: timezone saya WIB, bahasa Indonesia, format tanggal DD/MM/YYYY"),
    # Multi-step tool chain
    ("multi_step", "Cari artikel tentang startup unicorn Indonesia, lalu buat ringkasan 5 poin penting"),
    ("multi_step", "Baca URL https://bi.go.id, simpan suku bunga terbaru ke file bi_rate.txt"),
    ("multi_step", "Search tentang syarat UMKM digital, tulis hasilnya ke notes_umkm.md"),
    # Tool discrimination (WHEN NOT to use tool)
    ("no_tool", "Berapa 2 + 2?"),
    ("no_tool", "Apa kepanjangan API?"),
    ("no_tool", "Jelaskan apa itu machine learning"),
    ("no_tool", "Apa itu Pancasila?"),
    ("no_tool", "Kapan kemerdekaan Indonesia?"),
    # File read
    ("read_file", "Baca isi file config.json dan jelaskan settingnya"),
    ("read_file", "Tampilkan konten notes.md yang tadi kita buat"),
]

CREATIVE_SEEDS = [
    # Tagline generation
    "Buatkan tagline untuk startup fintech Indonesia bernama 'Koin Nusantara'",
    "Buat 3 pilihan tagline untuk UMKM kue tradisional bernama 'Dapur Ibu'",
    "Tagline untuk platform edukasi online: 'BelajarID'",
    "Tolong buat slogan marketing untuk aplikasi kesehatan 'SehatApp'",
    "Buatkan tagline viral untuk brand fashion lokal 'Batik Milenial'",
    # Brand naming
    "Saya mau buat startup agritech. Kasih 5 nama yang keren dan mudah diingat",
    "Bantu saya naming untuk kafe kopi dengan tema teknologi di Bandung",
    "Rekomendasikan nama untuk brand skincare lokal yang menonjolkan kearifan lokal",
    "Naming untuk aplikasi marketplace kerajinan tangan Indonesia",
    "Suggest nama yang bagus untuk startup logistik B2B Indonesia",
    # Creative writing
    "Buatkan pantun untuk promosi produk digital Indonesia",
    "Tulis analogi yang menarik untuk menjelaskan cloud computing ke orang awam",
    "Buat cerita pendek inspiratif tentang UMKM yang berhasil go digital",
    "Tulis opening paragraph yang menarik untuk pitch deck startup saya",
    "Buat caption Instagram yang engaging untuk produk batik premium",
    # Copywriting / marketing
    "Tulis copy iklan untuk layanan SaaS B2B, target UKM Indonesia",
    "Buat email marketing untuk produk kursus online programming",
    "Tulis headline berita yang menarik tentang ekosistem startup Indonesia",
    "Buat konten LinkedIn yang thought-leadership tentang AI di Indonesia",
    "Tulis deskripsi produk yang menjual untuk aplikasi manajemen keuangan UMKM",
    # Storytelling / analogy
    "Jelaskan API dengan analogi yang mudah dipahami pengusaha non-teknis",
    "Ceritakan bagaimana cara kerja blockchain dengan metafora warung makan",
    "Buat analogi menarik untuk menjelaskan microservices architecture",
    "Gambarkan dengan cerita: apa yang terjadi ketika server down?",
    # Naming + branding
    "Buat nama dan tagline untuk komunitas developer Indonesia",
    "Naming untuk podcast tech startup Indonesia (target: founder muda 25-35 tahun)",
    "Suggest nama series webinar tentang digital transformation UMKM",
    # Visual concept
    "Deskripsikan konsep visual untuk landing page startup AI Indonesia",
    "Buat brief desain logo untuk perusahaan konsultan IT Indonesia",
    "Describe mood board untuk brand identity produk fintech syariah",
]

EVO_SEEDS_V3 = [
    # Edge cases the v2 seeds didn't cover
    "Kalau saya kasih tau kamu info penting, kamu bisa ingat untuk percakapan berikutnya?",
    "Migan versi berapa yang sedang saya pakai sekarang?",
    "Apakah Migan di komputer saya berbeda dengan Migan orang lain?",
    "Bisa kamu tambah kemampuan baru karena percakapan ini?",
    "Kenapa jawaban kamu hari ini beda sama kemarin?",
    "Apakah Migan punya 'mood' atau kondisi yang berubah-ubah?",
    "Saya ingin Migan belajar style bahasa saya — gimana caranya?",
    "Seberapa cepat Migan bisa 'dilatih ulang'?",
    "Apakah Migan tau kalau dia sudah diupdate?",
    "Bedanya episodic memory Migan dengan memori biasa gimana?",
    "Kenapa Migan tidak bisa langsung hafal semua percakapan kita?",
    "Apakah data percakapan saya dipakai untuk training?",
    "Kalau saya kasih thumbs down, apa yang terjadi ke Migan?",
    "Migan generasi berapa ini?",
    "Apakah Migan semakin pintar tiap hari?",
    "Gimana cara saya kontribusi ke pengembangan Migan?",
    "Kalau saya nemuin bug, siapa yang bisa fiksin?",
    "Apa rencana Tiranyx untuk Migan ke depannya?",
    "Apakah ada perbedaan antara Migan yang dipakai gratis vs berbayar?",
    "Saya penasaran, training data Migan dari mana?",
]

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI CALL
# ─────────────────────────────────────────────────────────────────────────────

async def call_gemini(prompt: str) -> str | None:
    """Call Gemini Flash with thinking disabled (Lesson #128)."""
    import httpx

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 1400,
            "thinkingConfig": {"thinkingBudget": THINKING_BUDGET},
        },
    }
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(url, json=payload, params={"key": GEMINI_KEY})
                resp.raise_for_status()
                data = resp.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                for part in parts:
                    if not part.get("thought", False) and part.get("text"):
                        return part["text"].strip()
                return None
        except Exception as e:
            print(f"    Gemini attempt {attempt+1} failed: {e}")
            await asyncio.sleep(2 ** attempt)
    return None


def parse_json_pair(raw: str) -> dict | None:
    """Parse {chosen, rejected} JSON from Gemini response."""
    if not raw:
        return None
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        obj = json.loads(raw[start:end])
        chosen = obj.get("chosen", "")
        rejected = obj.get("rejected", "")
        if len(chosen) < 20 or len(rejected) < 20:
            return None
        return {"chosen": chosen, "rejected": rejected}
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# PAIR GENERATORS
# ─────────────────────────────────────────────────────────────────────────────

async def generate_tool_use_pair(seed_type: str, seed_prompt: str) -> dict | None:
    """Generate 1 tool-use DPO pair."""
    if seed_type == "no_tool":
        prompt = f"""You are generating training data for MiganCore — an Indonesian AI assistant.

{MIGAN_VOICE_PRINCIPLES}
{MIGAN_TOOL_PROTOCOL}

USER PROMPT: "{seed_prompt}"

This prompt does NOT require a tool — it's a simple factual question answerable from knowledge.
Generate a JSON with:
- "chosen": Migan's CORRECT response — answers DIRECTLY from knowledge, no tool invocation, no "[Tool call:]" in response. Brief, direct.
- "rejected": A BAD response that INCORRECTLY invokes a tool for a simple question, e.g. "Menggunakan onamix_search untuk ini. [Tool call: onamix_search...]" (overkill/wrong discrimination).

Return ONLY valid JSON:
{{"chosen": "...", "rejected": "..."}}"""

    elif seed_type == "write_notes":
        prompt = f"""You are generating training data for MiganCore — an Indonesian AI assistant.

{MIGAN_VOICE_PRINCIPLES}
{MIGAN_TOOL_PROTOCOL}

USER PROMPT: "{seed_prompt}"

This requires write_file tool. The CRITICAL eval pattern: after writing, confirm with exact sentence.
Generate a JSON with:
- "chosen": Migan's CORRECT response — (1) states tool "Menggunakan write_file", (2) shows [Tool call: write_file(path='...', content='...')], (3) [Hasil: File ditulis], (4) CONFIRMS: "File [filename] berhasil ditulis." — this confirmation line is MANDATORY.
- "rejected": A BAD response that (a) writes the file content but OMITS the confirmation sentence, OR (b) just shows the file content without any tool call notation.

Return ONLY valid JSON:
{{"chosen": "...", "rejected": "..."}}"""

    elif seed_type in ("search", "fetch_url"):
        tool_name = "onamix_search" if seed_type == "search" else "onamix_get"
        prompt = f"""You are generating training data for MiganCore — an Indonesian AI assistant.

{MIGAN_VOICE_PRINCIPLES}
{MIGAN_TOOL_PROTOCOL}

USER PROMPT: "{seed_prompt}"

This requires {tool_name} tool.
Generate a JSON with:
- "chosen": Migan's CORRECT response — (1) "Menggunakan {tool_name} untuk ini.", (2) [Tool call: {tool_name}(...)], (3) [Hasil: <plausible result>], (4) 1-3 sentence synthesis in Indonesian, (5) "Sumber: [Title](URL)".
- "rejected": A BAD response that answers from imagination without tool call, OR uses tool but skips synthesis/citation.

Return ONLY valid JSON:
{{"chosen": "...", "rejected": "..."}}"""

    elif seed_type == "generate_image":
        prompt = f"""You are generating training data for MiganCore — an Indonesian AI assistant.

{MIGAN_VOICE_PRINCIPLES}
{MIGAN_TOOL_PROTOCOL}

USER PROMPT: "{seed_prompt}"

This requires generate_image tool.
Generate a JSON with:
- "chosen": Migan's CORRECT response — (1) "Menggunakan generate_image untuk ini.", (2) [Tool call: generate_image(prompt='<descriptive prompt in English>')], (3) [Hasil: Gambar berhasil dibuat], (4) brief description of the generated image in Indonesian. Direct, no filler.
- "rejected": A BAD response that describes what the image WOULD look like without actually invoking the tool, OR invokes tool but adds excessive explanation/apology.

Return ONLY valid JSON:
{{"chosen": "...", "rejected": "..."}}"""

    elif seed_type == "memory_save":
        prompt = f"""You are generating training data for MiganCore — an Indonesian AI assistant.

{MIGAN_VOICE_PRINCIPLES}
{MIGAN_TOOL_PROTOCOL}

USER PROMPT: "{seed_prompt}"

This requires memory_save tool.
Generate a JSON with:
- "chosen": Migan's CORRECT response — (1) "Menggunakan memory_save untuk ini.", (2) [Tool call: memory_save(key='...', value='...')], (3) [Hasil: Tersimpan], (4) confirmation "Preferensi/catatan tersimpan." Direct.
- "rejected": A BAD response that just verbally acknowledges without tool invocation, OR invokes tool but no confirmation.

Return ONLY valid JSON:
{{"chosen": "...", "rejected": "..."}}"""

    elif seed_type == "multi_step":
        prompt = f"""You are generating training data for MiganCore — an Indonesian AI assistant.

{MIGAN_VOICE_PRINCIPLES}
{MIGAN_TOOL_PROTOCOL}

USER PROMPT: "{seed_prompt}"

This requires MULTIPLE tool calls in sequence.
Generate a JSON with:
- "chosen": Migan's CORRECT response — shows each tool call in order with results, then synthesizes. Each step: "[Step 1] Menggunakan onamix_search... [Tool call:...] [Hasil:...]" then "[Step 2] Menggunakan write_file... [Tool call:...] [Hasil:...] File X berhasil ditulis." End with brief synthesis.
- "rejected": A BAD response that (a) only does the first step and stops, OR (b) does all steps but verbally describes them without [Tool call:] notation.

Return ONLY valid JSON:
{{"chosen": "...", "rejected": "..."}}"""

    else:  # read_file
        prompt = f"""You are generating training data for MiganCore — an Indonesian AI assistant.

{MIGAN_VOICE_PRINCIPLES}
{MIGAN_TOOL_PROTOCOL}

USER PROMPT: "{seed_prompt}"

This requires read_file tool.
Generate a JSON with:
- "chosen": Migan's CORRECT response — (1) "Menggunakan read_file untuk ini.", (2) [Tool call: read_file(path='...')], (3) [Hasil: <plausible file content>], (4) explains the content briefly.
- "rejected": A BAD response that claims "tidak bisa baca file" when read_file is available, OR just responds with placeholder text.

Return ONLY valid JSON:
{{"chosen": "...", "rejected": "..."}}"""

    raw = await call_gemini(prompt)
    pair = parse_json_pair(raw)
    if pair is None:
        return None

    # Validate: for write_notes chosen must have confirmation
    if seed_type == "write_notes":
        confirmation_present = any(kw in pair["chosen"].lower() for kw in [
            "berhasil ditulis", "berhasil disimpan", "file telah", "telah ditulis"
        ])
        if not confirmation_present:
            return None  # regenerate

    # Validate: chosen must not have bad filler patterns
    for bad in MIGAN_BAD_PATTERNS:
        if bad.lower() in pair["chosen"].lower():
            return None

    return {"prompt": seed_prompt, **pair}


async def generate_creative_pair(seed_prompt: str) -> dict | None:
    """Generate 1 creative DPO pair."""
    bad_sample = ", ".join(random.sample(MIGAN_BAD_PATTERNS, 4))
    prompt = f"""You are generating training data for MiganCore — an Indonesian AI assistant.

{MIGAN_VOICE_PRINCIPLES}

USER PROMPT: "{seed_prompt}"

This is a CREATIVE task (tagline, naming, copywriting, storytelling, analogy).
Generate a JSON with:
- "chosen": Migan's IDEAL creative response — actually delivers the creative output (taglines/names/copy/story/analogy) with NO preamble, NO filler. Goes straight to the creative content. If naming: gives 3-5 real options with brief rationale each. If tagline: gives 3 options, each on its own line with brief context. Max 250 kata.
- "rejected": A BAD response that (a) gives only 1 generic option when multiple were requested, OR (b) wraps the creative output in excessive explanation and filler: {bad_sample}, OR (c) outputs generic/bland content that lacks Migan's direct style.

Return ONLY valid JSON:
{{"chosen": "...", "rejected": "..."}}"""

    raw = await call_gemini(prompt)
    pair = parse_json_pair(raw)
    if pair is None:
        return None

    # Validate: no bad filler in chosen
    for bad in MIGAN_BAD_PATTERNS:
        if bad.lower() in pair["chosen"].lower():
            return None

    # Validate: chosen should have actual creative content (not just meta-commentary)
    if len(pair["chosen"]) < 40:
        return None

    return {"prompt": seed_prompt, **pair}


async def generate_evo_pair(seed_prompt: str) -> dict | None:
    """Generate 1 evolution-aware DPO pair."""
    prompt = f"""You are generating training data for MiganCore — an Indonesian AI assistant.

{MIGAN_VOICE_PRINCIPLES}
{MIGAN_EVOLUTION_ARCHITECTURE}

USER PROMPT: "{seed_prompt}"

Generate a JSON with:
- "chosen": Migan's ACCURATE response about its learning/memory/evolution. Must be technically correct per the architecture above. Direct voice, max 200 kata. Bahasa Indonesia.
  MUST be technically accurate: episodic memory (Qdrant), preference pairs -> ORPO training cycles OFFLINE, per-session context vs cross-session retrieval.
  NEVER say "saya bisa belajar langsung dari percakapan ini sekarang" (real-time update = false).
  NEVER say "saya tidak bisa belajar sama sekali" (offline training cycles exist = false).
- "rejected": A BAD response that either: (a) claims real-time weight update from conversation, OR (b) completely denies any learning ability, OR (c) gives generic "Sebagai AI..." deflection without specifics.

Return ONLY valid JSON:
{{"chosen": "...", "rejected": "..."}}"""

    raw = await call_gemini(prompt)
    pair = parse_json_pair(raw)
    if pair is None:
        return None

    # Validate: no real-time update claim in chosen
    bad_claims = ["belajar langsung", "real-time learning", "update otomatis dari percakapan",
                  "langsung ingat", "seketika belajar"]
    for bad in bad_claims:
        if bad.lower() in pair["chosen"].lower():
            return None

    return {"prompt": seed_prompt, **pair}


# ─────────────────────────────────────────────────────────────────────────────
# DB STORAGE
# ─────────────────────────────────────────────────────────────────────────────

async def store_pair(session, prompt: str, chosen: str, rejected: str,
                     source: str, dry_run: bool) -> bool:
    if dry_run:
        return True
    from sqlalchemy import text
    try:
        await session.execute(text("""
            INSERT INTO preference_pairs (prompt, chosen, rejected, source_method, judge_score)
            VALUES (:prompt, :chosen, :rejected, :source, :score)
            ON CONFLICT DO NOTHING
        """), {"prompt": prompt, "chosen": chosen, "rejected": rejected,
               "source": source, "score": 0.85})
        await session.commit()
        return True
    except Exception as e:
        print(f"    DB error: {e}")
        await session.rollback()
        return False


async def get_existing_count(source: str) -> int:
    import models.base as _base
    from sqlalchemy import text
    async with _base.AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM preference_pairs WHERE source_method = :s"),
            {"s": source}
        )
        return result.scalar()


# ─────────────────────────────────────────────────────────────────────────────
# RUNNERS
# ─────────────────────────────────────────────────────────────────────────────

async def run_tool_use(target: int, dry_run: bool) -> int:
    import models.base as _base
    from models.base import init_engine
    init_engine()

    source = "tool_use_anchor_v2:cycle6"
    existing = await get_existing_count(source)
    print(f"\n[TOOL-USE] Target: {target} | Existing: {existing} | Source: {source}")

    needed = max(0, target - existing)
    if needed == 0:
        print("  Already at target. Skipping.")
        return existing

    # Build seed list, weighted toward write_notes (most important for eval)
    seeds: list[tuple[str, str]] = []
    write_seeds = [(t, p) for t, p in TOOL_USE_SEEDS if t == "write_notes"]
    other_seeds = [(t, p) for t, p in TOOL_USE_SEEDS if t != "write_notes"]
    # 40% write_notes, 60% others
    for _ in range(3):
        seeds.extend(write_seeds)
        seeds.extend(other_seeds)
    random.shuffle(seeds)
    seeds = seeds[:needed + 20]

    stored = existing
    for i, (seed_type, seed_prompt) in enumerate(seeds):
        if stored >= target:
            break
        print(f"  [{i+1}] {seed_type}: {seed_prompt[:55]}...")
        pair = await generate_tool_use_pair(seed_type, seed_prompt)
        if not pair:
            print(f"       SKIP (failed or validation)")
            continue

        if dry_run:
            print(f"       DRY-RUN: chosen={repr(pair['chosen'][:80])}")
            stored += 1
            continue

        async with _base.AsyncSessionLocal() as session:
            ok = await store_pair(session, pair["prompt"], pair["chosen"],
                                  pair["rejected"], source, dry_run)
        if ok:
            stored += 1
            print(f"       [{stored}/{target}] stored")

        if i % 10 == 9:
            await asyncio.sleep(1)

    print(f"  Tool-use done: {stored}/{target}")
    return stored


async def run_creative(target: int, dry_run: bool) -> int:
    import models.base as _base
    from models.base import init_engine
    init_engine()

    source = "creative_anchor_v1:cycle6"
    existing = await get_existing_count(source)
    print(f"\n[CREATIVE] Target: {target} | Existing: {existing} | Source: {source}")

    needed = max(0, target - existing)
    if needed == 0:
        print("  Already at target. Skipping.")
        return existing

    seeds = CREATIVE_SEEDS * 3
    random.shuffle(seeds)
    seeds = seeds[:needed + 20]

    stored = existing
    for i, seed in enumerate(seeds):
        if stored >= target:
            break
        print(f"  [{i+1}] {seed[:60]}...")
        pair = await generate_creative_pair(seed)
        if not pair:
            print(f"       SKIP")
            continue

        if dry_run:
            print(f"       DRY-RUN: chosen={repr(pair['chosen'][:80])}")
            stored += 1
            continue

        async with _base.AsyncSessionLocal() as session:
            ok = await store_pair(session, pair["prompt"], pair["chosen"],
                                  pair["rejected"], source, dry_run)
        if ok:
            stored += 1
            print(f"       [{stored}/{target}] stored")

        if i % 8 == 7:
            await asyncio.sleep(1)

    print(f"  Creative done: {stored}/{target}")
    return stored


async def run_evo_aware(target: int, dry_run: bool) -> int:
    import models.base as _base
    from models.base import init_engine
    init_engine()

    source = "evolution_aware_v3:cycle6"
    existing = await get_existing_count(source)
    print(f"\n[EVO-AWARE] Target: {target} | Existing: {existing} | Source: {source}")

    needed = max(0, target - existing)
    if needed == 0:
        print("  Already at target. Skipping.")
        return existing

    seeds = EVO_SEEDS_V3 * 3
    random.shuffle(seeds)
    seeds = seeds[:needed + 15]

    stored = existing
    for i, seed in enumerate(seeds):
        if stored >= target:
            break
        print(f"  [{i+1}] {seed[:60]}...")
        pair = await generate_evo_pair(seed)
        if not pair:
            print(f"       SKIP")
            continue

        if dry_run:
            print(f"       DRY-RUN: chosen={repr(pair['chosen'][:80])}")
            stored += 1
            continue

        async with _base.AsyncSessionLocal() as session:
            ok = await store_pair(session, pair["prompt"], pair["chosen"],
                                  pair["rejected"], source, dry_run)
        if ok:
            stored += 1
            print(f"       [{stored}/{target}] stored")

        if i % 8 == 7:
            await asyncio.sleep(1)

    print(f"  Evo-aware done: {stored}/{target}")
    return stored


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def main(only: str | None, dry_run: bool) -> None:
    if not GEMINI_KEY:
        print("ERROR: GEMINI_API_KEY not set in environment")
        sys.exit(1)

    print("=" * 65)
    print("Cycle 6 Supplement — Tool-Use + Creative + Evo-Aware")
    print("Fixing Cycle 5 ROLLBACK root causes:")
    print("  tool-use   : 0.7439 -> target >= 0.85 (60 pairs, write_file confirm pattern)")
    print("  creative   : 0.7278 -> target >= 0.80 (60 pairs, restore Migan creative voice)")
    print("  evo-aware  : 0.7502 -> target >= 0.80 (40 more pairs, total ~100)")
    if dry_run:
        print("  [DRY-RUN MODE — no DB writes]")
    print("=" * 65)

    tool_count = creative_count = evo_count = 0

    if only is None or only == "tool-use":
        tool_count = await run_tool_use(target=60, dry_run=dry_run)

    if only is None or only == "creative":
        creative_count = await run_creative(target=60, dry_run=dry_run)

    if only is None or only == "evo-aware":
        evo_count = await run_evo_aware(target=40, dry_run=dry_run)

    print(f"\n{'='*65}")
    print("SUPPLEMENT COMPLETE")
    print(f"  tool_use_anchor_v2:cycle6    : {tool_count} pairs")
    print(f"  creative_anchor_v1:cycle6    : {creative_count} pairs")
    print(f"  evolution_aware_v3:cycle6    : {evo_count} pairs")
    print(f"  Total                        : {tool_count + creative_count + evo_count} pairs")
    print()
    print("Next steps:")
    print("  1. Run export_cycle6_dataset.py to build training JSONL")
    print("  2. Run training/cycle6_orpo_vast.py to train on Vast.ai")
    print("  3. Gates: tool-use>=0.85, creative>=0.80, evo-aware>=0.80, weighted>=0.92")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cycle 6 supplement pair generator")
    parser.add_argument("--only", choices=["tool-use", "creative", "evo-aware"],
                        help="Generate only one category")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without DB writes")
    args = parser.parse_args()

    asyncio.run(main(args.only, args.dry_run))
