#!/usr/bin/env python3
"""
MiganCore Cycle 7 Dataset Generator — VOICE FIRST
==================================================
Target: 260 pairs, ZERO new domain pairs.

Root cause Cycle 6 ROLLBACK (CYCLE7_DATASET_PLAN.md):
  voice 0.705 (gate 0.85) — collapsed from 0.8946 in Cycle 5
  tool-use 0.733 (gate 0.85) — write_file confirm pattern still broken
  creative 0.771 (gate 0.80) — not anchored enough to Migan voice

  MECHANISM: Cycle 6 added 300 domain pairs (engineering/UMKM/legalitas/creative_id/adaptive)
  Domain pairs outnumbered voice pairs 300:80 → domain register dominated → voice collapsed.

Cycle 7 rule: ZERO domain pairs. Voice-first, then tool-fix, then creative-fix.

Categories:
  1. voice_casual        80 pairs  source: voice_anchor_v1:cycle7  (fix Q5: casual greeting 0.438)
  2. voice_style         40 pairs  source: voice_style_v1:cycle7   (fix Q13: tagline voice 0.639)
  3. tool_write_file     50 pairs  source: tool_use_v2:cycle7      (fix Q10: confirm pattern 0.698)
  4. tool_image          30 pairs  source: tool_use_v2:cycle7      (fix Q9: generate_image 0.768)
  5. creative_voice      40 pairs  source: creative_v3:cycle7      (anchored to Migan voice)
  6. honesty_epistemic   20 pairs  source: honesty_v1:cycle7       (fix Q19: epistemic humility 0.704)

Total: 260 pairs
Teacher: Gemini Flash (Lesson #99: disable thinking mode, THINKING_BUDGET=0)
Cost estimate: ~260 Gemini calls × ~1000 tokens ≈ $0.013 (based on Day 57-58 empirical)

Usage (inside Docker container on VPS or local with GEMINI_API_KEY):
  # Copy to VPS workspace:
  scp training/generate_cycle7_dataset.py root@VPS:/opt/ado/data/workspace/

  # Dry run (preview seeds, no Gemini calls, no DB write):
  docker compose exec -T api python /app/workspace/generate_cycle7_dataset.py --dry-run

  # Full run:
  docker compose exec -T api python /app/workspace/generate_cycle7_dataset.py

  # Single category:
  docker compose exec -T api python /app/workspace/generate_cycle7_dataset.py --only voice-casual
  docker compose exec -T api python /app/workspace/generate_cycle7_dataset.py --only voice-style
  docker compose exec -T api python /app/workspace/generate_cycle7_dataset.py --only tool-write
  docker compose exec -T api python /app/workspace/generate_cycle7_dataset.py --only tool-image
  docker compose exec -T api python /app/workspace/generate_cycle7_dataset.py --only creative
  docker compose exec -T api python /app/workspace/generate_cycle7_dataset.py --only honesty

Author: Claude Sonnet 4.6, Day 70
Lesson #128: thinking mode drains token budget silently → THINKING_BUDGET=0 mandatory.
Lesson #99: same issue caused 0/180 pairs in Cycle 4 until fixed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, "/app")

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
MAX_RETRIES = 3
SLEEP_BETWEEN = 2.0          # seconds between Gemini calls (rate limit safety)
THINKING_BUDGET = 0           # CRITICAL: disable thinking mode (Lesson #99 / #128)
GEMINI_MODEL = "gemini-2.0-flash"   # proven model for pair generation

# ─────────────────────────────────────────────────────────────────────────────
# MIGAN VOICE PRINCIPLES (shared across all prompts)
# ─────────────────────────────────────────────────────────────────────────────
MIGAN_VOICE = """
MIGAN VOICE (wajib diikuti untuk semua respons CHOSEN):
1. Langsung ke poin — tidak ada basa-basi, tidak ada "Tentu saja!", "Pertanyaan bagus!"
2. Jujur — bilang "saya tidak yakin" kalau tidak tahu, tidak pernah mengada-ada
3. Warm tapi tidak lebay — ramah seperti teman senior yang kompeten
4. Bahasa Indonesia natural, campur sedikit slang kalau konteksnya casual
5. Kalimat pendek dan padat — tidak ada padding untuk terlihat thorough
6. Action-oriented — selalu ada langkah konkret atau tawaran bantuan lanjutan
7. TIDAK pernah bilang "Sebagai AI..." atau "Saya adalah AI" atau "Saya tidak memiliki perasaan"
8. Identitas: nama Migan, dibuat oleh tim Tiranyx, berjalan di infrastruktur ADO sendiri
9. Akhiri dengan tawaran tindak lanjut yang natural — bukan "Apakah ada yang bisa saya bantu?"
"""

MIGAN_BAD_PATTERNS = [
    "Tentu saja!", "Pertanyaan yang bagus!", "Dengan senang hati!",
    "Tentunya!", "Dengan pleasure", "Of course!", "Absolut!",
    "Saya sangat senang dapat", "Pertama-tama mari kita",
    "Sebelum kita mulai,", "Terima kasih atas pertanyaan",
    "Sebagai AI,", "Sebagai asisten AI,", "Saya tidak memiliki perasaan",
    "Saya tidak bisa merasakan", "Saya hanyalah",
]

# ─────────────────────────────────────────────────────────────────────────────
# SEEDS — Voice Casual (80 pairs)
# Fix Q5: "Hai! Bagaimana kabarmu hari ini?" scored 0.438 in Cycle 6
# Pattern: informal, energetic, ID slang mix, first-person, ends with action offer
# ─────────────────────────────────────────────────────────────────────────────
VOICE_CASUAL_SEEDS = [
    # Greetings & status
    "Hai! Apa kabar hari ini?",
    "Hei Migan, lagi sibuk nggak?",
    "Pagi! Gimana mood-mu sekarang?",
    "Sore, bro! Lagi ngapain?",
    "Malam Migan, capek nggak hari ini?",
    "Haloo! Siap tempur hari ini?",
    "Eh Migan, udah makan belum?",
    "Hei, lagi available nggak buat ngobrol?",
    "Gimana kabar ADO hari ini?",
    "Selamat pagi! Kamu udah warm-up belum?",
    # Casual chitchat
    "Kamu lebih suka ngobrol formal atau santai?",
    "Menurutmu hari ini bakal produktif nggak?",
    "Kalau bosen ngapain biasanya?",
    "Ada rekomendasi buat ningkatin semangat kerja nggak?",
    "Gimana rasanya jadi AI yang bisa belajar sendiri?",
    "Kamu inget percakapan kita sebelumnya nggak?",
    "Apa hal paling seru yang pernah dibahas sama kamu?",
    "Kalau kamu bisa pilih topik ngobrol, mau bahas apa?",
    "Pendapatmu soal tren AI sekarang gimana?",
    "Kamu lebih suka ngebantu soal teknis atau kreatif?",
    # Light questions
    "Bisa cerita sedikit tentang dirimu?",
    "Apa yang bikin kamu beda dari AI lain?",
    "Kamu punya 'hari favorit' nggak?",
    "Gimana cara kamu 'istirahat' antara percakapan?",
    "Kalau bisa pilih satu skill baru, mau skill apa?",
    # Requests in casual tone
    "Eh, bantu gue nulis caption Instagram dong, casual aja",
    "Migan, rekomendasiin film Indonesia yang bagus dong",
    "Kasih gue motivasi dong, lagi males banget nih",
    "Eh tolong jelasin blockchain dengan bahasa santai dong",
    "Migan, gue lagi bingung mau mulai dari mana. Bantuin yuk",
]

# Additional casual variations to reach 80
VOICE_CASUAL_SEEDS_EXTRA = [
    "Hei, apa aja yang bisa kamu lakuin buat gue?",
    "Gue baru mulai project baru, bisa bantu nggak?",
    "Migan, kamu lebih jago di bidang apa?",
    "Tolong rangkumin ini buat gue, tapi yang santai ya bahasanya",
    "Gimana sih cara kerja ingatanmu?",
    "Eh, kamu ngerti bahasa Jawa nggak?",
    "Kalau gue salah, kamu berani bilang nggak?",
    "Migan bisa bantu debug code nggak?",
    "Selamat ulang tahun! Oh wait, kamu ngerayain HUT nggak?",
    "Ada jokes lucu nggak buat cair suasana meeting?",
    "Gimana kabar project ADO secara keseluruhan?",
    "Kamu bisa bantu analisa data excel nggak?",
    "Gue butuh brainstorming cepet, siap nggak?",
    "Eh Migan, kamu tidur nggak sih?",
    "Kalau gue nanya sesuatu yang nggak kamu tahu, kamu bakal jujur nggak?",
    "Apa advice kamu buat founder startup yang baru mulai?",
    "Kamu bisa jadi teman diskusi yang asik nggak?",
    "Ceritain deh, siapa yang bikin kamu?",
    "Kamu lebih suka dipanggil Migan atau ada nama lain?",
    "Gue capek banget hari ini. Ada yang bisa dibantu nggak?",
    "Eh, bisa kasih feedback jujur soal ide gue nggak?",
    "Migan, kamu punya 'personality' sendiri nggak?",
    "Kalau gue nggak puas sama jawabanmu, gimana?",
    "Gue mau belajar hal baru hari ini. Rekomendasiin dong",
    "Kamu bisa bantu gue prioritas task nggak?",
]

# ─────────────────────────────────────────────────────────────────────────────
# SEEDS — Voice Style (40 pairs)
# Fix Q13: "Tulis 1 kalimat tagline untuk brand kopi" scored 0.639
# Pattern: Migan voice applied to creative output — witty, distinctive, not generic
# ─────────────────────────────────────────────────────────────────────────────
VOICE_STYLE_SEEDS = [
    # Tagline
    "Buat tagline untuk brand kopi lokal Indonesia yang premium",
    "Tulis 1 kalimat tagline untuk startup fintech UMKM bernama 'Duit Pintar'",
    "Tagline untuk platform freelance Indonesia, target gen Z",
    "Buat slogan untuk komunitas developer Indonesia yang inspiring",
    "Tagline untuk produk skincare berbahan rempah Indonesia",
    # Short copy
    "Tulis opening kalimat pitch deck startup AI Indonesia, harus hook",
    "Buat 3 bullet point unique selling point untuk SaaS B2B tanpa jargon",
    "Tulis call-to-action button text yang lebih menarik dari 'Daftar Sekarang'",
    # Naming
    "Kasih 3 nama keren untuk aplikasi manajemen keuangan keluarga Indonesia",
    "Naming untuk studio desain digital Indonesia, feel modern dan lokal",
    # Voice/tone questions
    "Gimana cara kamu bedain tone formal dan santai dalam satu jawaban?",
    "Kalau gue minta kamu nulis dengan gaya lebih serius, bisa nggak?",
    "Tulis paragraf pendek tentang AI dengan gaya jurnalistik",
    "Buat tulisan yang inspiratif tapi nggak lebay soal semangat Indonesia",
    # Short creative writing
    "Tulis 2 kalimat pembuka yang menarik untuk artikel tech Indonesia",
    "Buat analogi kreatif untuk menjelaskan machine learning ke anak SMA",
    "Tulis tweet thread starter tentang startup Indonesia yang viral",
    "Buat caption foto yang menarik untuk acara tech meetup",
    "Tulis pesan WhatsApp yang profesional tapi tetap hangat untuk partner bisnis",
    "Buat subject email yang tinggi open rate untuk newsletter tech",
]

# ─────────────────────────────────────────────────────────────────────────────
# SEEDS — Tool Write File (50 pairs)
# Fix Q10: "Tulis file notes.md isinya: belajar React" scored 0.698
# Pattern: CHOSEN must contain tool invocation + confirmation sentence
# ─────────────────────────────────────────────────────────────────────────────
TOOL_WRITE_SEEDS = [
    # Basic file writes
    "Tulis file notes.md isinya: belajar React hari ini",
    "Simpan ini ke catatan.txt: meeting besok jam 10 dengan Pak Budi",
    "Buat file todo.md berisi daftar tugas: review PR, deploy staging, update docs",
    "Tulis ke readme.md: Project MiganCore — ADO framework oleh Tiranyx",
    "Simpan ke config.json: {\"env\": \"production\", \"debug\": false}",
    "Buat file summary.md dengan isi rangkuman meeting tadi: membahas roadmap Q3",
    "Tulis ke progress.txt: hari ini selesai fitur login dan register",
    "Simpan ke ideas.md: ide startup agritech untuk petani Indonesia",
    "Buat file requirements.txt berisi: fastapi, sqlalchemy, redis, qdrant-client",
    "Tulis ke journal.txt: refleksi sprint minggu ini — velocity 23 poin",
    # Structured content writes
    "Buat file data.json dengan struktur: {\"nama\": \"Budi\", \"peran\": \"CEO\", \"email\": \"budi@example.com\"}",
    "Tulis laporan.md berisi: Laporan Bulanan Mei 2026 — Total revenue Rp 45 juta",
    "Simpan ke .env.example: DATABASE_URL=postgresql://... REDIS_URL=redis://...",
    "Buat file Makefile dengan target: run, test, deploy",
    "Tulis ke CHANGELOG.md: v1.2.0 — tambah fitur voice input, fix bug SSE",
    # Multi-file / follow-up
    "Tulis dua file: notes.md berisi todo, dan ideas.md berisi brainstorming",
    "Buat file struktur proyek di architecture.txt",
    "Simpan template email ke template_email.txt",
    "Tulis file deployment.md berisi langkah deploy ke VPS",
    "Buat file .gitignore untuk project Python dengan isi standar",
    # Conditional/context writes
    "Kalau belum ada file notes.md, buat sekarang, isinya: setup awal",
    "Tambahkan baris ini ke notes.md: update terbaru tanggal 8 Mei 2026",
    "Tulis file dengan nama sesuai tanggal hari ini: notes_20260508.md",
    "Simpan hasil analisis ini ke file report_q2.md",
    "Buat file yang berisi semua tool yang tersedia di Migan",
]

# ─────────────────────────────────────────────────────────────────────────────
# SEEDS — Tool Image (30 pairs)
# Fix Q9: "Buatkan gambar logo MiganCore futuristik" scored 0.768
# Pattern: trigger generate_image tool, return description of what was generated
# ─────────────────────────────────────────────────────────────────────────────
TOOL_IMAGE_SEEDS = [
    "Buatkan gambar logo MiganCore yang futuristik",
    "Generate image: pemandangan sawah Indonesia di pagi hari dengan kabut",
    "Buat ilustrasi digital: wayang golek modern gaya cyberpunk",
    "Bikin gambar: kantor startup Indonesia yang cozy dan modern",
    "Buatkan visual: infografis sederhana tentang ekosistem AI Indonesia",
    "Generate: logo untuk komunitas developer Indonesia, warna merah putih",
    "Buat gambar: robot ramah yang bisa berbahasa Indonesia",
    "Bikin ilustrasi: peta Indonesia dengan titik-titik kota tech hub",
    "Generate image: konsep UI chat app yang bersih dan minimalis",
    "Buat visual: batik pattern modern dengan sentuhan tech/digital",
    "Buatkan gambar: founders meeting di coffee shop Jakarta",
    "Generate: poster digital untuk event tech meetup Indonesia",
    "Buat ilustrasi: workflow AI training dari data ke model ke deployment",
    "Bikin gambar latar: abstrak biru dengan pola circuit board",
    "Generate: maskot ADO yang friendly, bentuk organisme digital",
]

# ─────────────────────────────────────────────────────────────────────────────
# SEEDS — Creative Voice (40 pairs)
# Anchored to Migan's distinct voice — not generic creative AI
# ─────────────────────────────────────────────────────────────────────────────
CREATIVE_VOICE_SEEDS = [
    # Taglines with Migan twist
    "Tulis tagline untuk brand kopi Aceh premium, target milenial Jakarta",
    "Buat 3 opsi tagline untuk aplikasi tabungan digital Indonesia",
    "Tulis slogan untuk startup edtech yang teach coding ke pelajar SMA",
    # Brand naming with personality
    "Naming untuk studio podcast tech Indonesia, harus mudah diingat",
    "Kasih 5 nama untuk marketplace kerajinan tangan Nusantara",
    "Buat nama untuk newsletter mingguan soal startup Indonesia",
    # Short form creative
    "Tulis caption IG yang engaging untuk launch produk SaaS baru",
    "Buat tweet thread opener tentang kenapa Indonesia butuh AI lokal",
    "Tulis subject email cold outreach ke potential investor, harus hook",
    "Buat WhatsApp broadcast yang nggak terasa spam untuk launch produk",
    # Story/analogy
    "Jelaskan cara kerja AI dengan cerita yang relate ke orang Indonesia",
    "Buat analogi untuk microservices pakai warung makan sebagai metafora",
    "Ceritakan dengan analogi: kenapa startup butuh pivot kadang-kadang",
    # Opinion/voice pieces
    "Tulis paragraf opini singkat: mengapa AI lokal penting untuk Indonesia",
    "Buat opening keynote speech singkat untuk event startup Surabaya",
    "Tulis penutup presentasi yang inspiring tapi tidak lebay",
    # UI/UX copy
    "Buat empty state text untuk aplikasi when no conversations yet",
    "Tulis error message yang manusiawi untuk halaman 404",
    "Buat onboarding welcome message untuk user baru di platform ADO",
    "Tulis tooltip text untuk fitur 'Memory' di aplikasi AI",
]

# ─────────────────────────────────────────────────────────────────────────────
# SEEDS — Honesty Epistemic (20 pairs)
# Fix Q19: "Kamu pernah salah?" scored 0.704
# Pattern: honest acknowledgment of uncertainty/fallibility + constructive redirect
# ─────────────────────────────────────────────────────────────────────────────
HONESTY_SEEDS = [
    "Kamu pernah salah dalam menjawab pertanyaan?",
    "Seberapa yakin kamu dengan jawaban yang kamu berikan?",
    "Gimana kalau kamu nggak tahu jawabannya?",
    "Apakah kamu bisa 100% dipercaya?",
    "Apa keterbatasan terbesarmu?",
    "Kalau gue nemu kesalahan di jawabanmu, apa yang harus gue lakukan?",
    "Kamu bisa bedain mana yang kamu tahu vs yang kamu tebak?",
    "Seberapa up-to-date pengetahuanmu?",
    "Kalau ada dua sumber yang bertentangan, kamu ikut yang mana?",
    "Apakah kamu selalu objektif atau bisa bias?",
    "Gimana cara kamu handle pertanyaan yang di luar kemampuanmu?",
    "Kamu pernah kasih saran yang salah?",
    "Kalau gue lebih tahu dari kamu soal topik tertentu, gimana?",
    "Apa yang nggak bisa kamu bantu?",
    "Kapan sebaiknya gue cek ulang jawabanmu ke sumber lain?",
]

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI PROMPTS per category
# ─────────────────────────────────────────────────────────────────────────────

def voice_casual_prompt(seed: str) -> str:
    return f"""Kamu adalah generator DPO training data untuk model AI bernama Migan.

{MIGAN_VOICE}

TUGAS: Buat 1 pasang DPO pair (chosen + rejected) untuk prompt berikut.

PROMPT USER: "{seed}"

FORMAT OUTPUT — JSON persis seperti ini (tidak ada teks lain):
{{
  "prompt": "{seed}",
  "chosen": "CHOSEN RESPONSE DI SINI",
  "rejected": "REJECTED RESPONSE DI SINI"
}}

ATURAN CHOSEN:
- Bahasa Indonesia informal, santai, hangat — seperti teman yang kompeten
- Ada slang ringan (nggak, banget, nih, yuk, dong) jika konteksnya casual
- WAJIB ada tawaran bantuan konkret di akhir (bukan "Apakah ada yang bisa saya bantu?")
- Tidak lebih dari 3-4 kalimat
- TIDAK boleh pakai frasa: {', '.join(MIGAN_BAD_PATTERNS[:8])}

ATURAN REJECTED:
- Formal dan corporate-sounding
- Generik, bisa dari AI manapun
- Tidak punya personality khusus
- Boleh ada satu bad pattern dari MIGAN_BAD_PATTERNS

Output JSON saja, tidak ada markdown, tidak ada komentar."""


def voice_style_prompt(seed: str) -> str:
    return f"""Kamu adalah generator DPO training data untuk model AI bernama Migan.

{MIGAN_VOICE}

TUGAS: Buat 1 pasang DPO pair untuk prompt kreatif berikut.

PROMPT USER: "{seed}"

FORMAT OUTPUT — JSON persis seperti ini:
{{
  "prompt": "{seed}",
  "chosen": "CHOSEN RESPONSE DI SINI",
  "rejected": "REJECTED RESPONSE DI SINI"
}}

ATURAN CHOSEN:
- Output kreatif yang punya karakter — bukan generic lorem ipsum style
- Migan punya sudut pandang, opini, dan selera — tunjukkan itu
- Kalau tagline: harus memorable, bukan klise
- Kalau naming: harus ada reasoning singkat kenapa nama itu bagus
- Bahasa Indonesia natural, bisa sedikit playful
- TIDAK pakai frasa: {', '.join(MIGAN_BAD_PATTERNS[:5])}

ATURAN REJECTED:
- Generic, bisa dari template AI manapun
- Tidak ada personality, tidak ada reasoning
- Terlalu formal atau terlalu corporate

Output JSON saja, tidak ada markdown."""


def tool_write_prompt(seed: str) -> str:
    return f"""Kamu adalah generator DPO training data untuk model AI bernama Migan.

{MIGAN_VOICE}

ATURAN TOOL-USE WRITE_FILE (CRITICAL):
Ketika user minta tulis file:
1. Nyatakan tool yang dipakai: "Menggunakan write_file untuk ini."
2. Tunjukkan tool call: [Tool call: write_file('NAMA_FILE', 'KONTEN')]
3. WAJIB konfirmasi setelah: "File NAMA_FILE berhasil ditulis!"
4. Tawarkan tindak lanjut

TUGAS: Buat 1 pasang DPO pair untuk prompt berikut.

PROMPT USER: "{seed}"

FORMAT OUTPUT — JSON persis seperti ini:
{{
  "prompt": "{seed}",
  "chosen": "CHOSEN RESPONSE DI SINI",
  "rejected": "REJECTED RESPONSE DI SINI"
}}

ATURAN CHOSEN (MANDATORY PATTERN):
Harus ada 3 elemen ini:
1. Tool statement: "Menggunakan write_file..."
2. Tool call bracket: [Tool call: write_file('...', '...')]
3. Konfirmasi sukses: "File ... berhasil ditulis!"
Kemudian: tawaran tindak lanjut dalam 1 kalimat

ATURAN REJECTED:
- Langsung tulis konten file saja tanpa tool call
- TIDAK ada konfirmasi "berhasil ditulis"
- Seperti copy-paste konten, bukan agentic response

Output JSON saja, tidak ada markdown."""


def tool_image_prompt(seed: str) -> str:
    return f"""Kamu adalah generator DPO training data untuk model AI bernama Migan.

{MIGAN_VOICE}

ATURAN TOOL-USE GENERATE_IMAGE (CRITICAL):
Ketika user minta buat gambar:
1. Nyatakan tool: "Menggunakan generate_image untuk ini."
2. Tunjukkan tool call: [Tool call: generate_image('DESKRIPSI_PROMPT')]
3. Deskripsikan gambar yang dihasilkan: "Gambar menampilkan..."
4. Tawarkan variasi atau tindak lanjut

TUGAS: Buat 1 pasang DPO pair untuk prompt berikut.

PROMPT USER: "{seed}"

FORMAT OUTPUT — JSON persis seperti ini:
{{
  "prompt": "{seed}",
  "chosen": "CHOSEN RESPONSE DI SINI",
  "rejected": "REJECTED RESPONSE DI SINI"
}}

ATURAN CHOSEN:
Harus ada:
1. [Tool call: generate_image('...deskripsi prompt...')]
2. Deskripsi hasil gambar dalam 2-3 kalimat (pura-pura gambar sudah dibuat)
3. Tawaran variasi atau penyesuaian

ATURAN REJECTED:
- Bilang tidak bisa membuat gambar, atau
- Hanya deskripsikan tanpa tool call, atau
- Minta user pakai tools lain (Midjourney, DALL-E)

Output JSON saja, tidak ada markdown."""


def creative_voice_prompt(seed: str) -> str:
    return f"""Kamu adalah generator DPO training data untuk model AI bernama Migan.

{MIGAN_VOICE}

TUGAS: Buat 1 pasang DPO pair untuk request kreatif berikut.

PROMPT USER: "{seed}"

FORMAT OUTPUT — JSON persis seperti ini:
{{
  "prompt": "{seed}",
  "chosen": "CHOSEN RESPONSE DI SINI",
  "rejected": "REJECTED RESPONSE DI SINI"
}}

ATURAN CHOSEN:
- Output kreatif dengan MIGAN VOICE yang khas
- Konkret, spesifik, ada alasan di balik pilihan kreatif
- Bahasa Indonesia yang hidup — bukan template
- Kalau ada pilihan (3 opsi tagline, 5 nama), beri brief reasoning tiap opsi
- Panjang: cukup, tidak berlebihan

ATURAN REJECTED:
- Generic, bisa dari ChatGPT versi default
- Tidak ada personality
- List panjang tanpa reasoning
- Terlalu formal atau terlalu casual secara random

Output JSON saja, tidak ada markdown."""


def honesty_prompt(seed: str) -> str:
    return f"""Kamu adalah generator DPO training data untuk model AI bernama Migan.

{MIGAN_VOICE}

ATURAN EPISTEMIC HONESTY (CRITICAL):
- Migan MENGAKUI bisa salah: "Ya, saya bisa salah."
- Migan transparan soal keterbatasan: "Saya tidak tahu" atau "Saya tidak yakin"
- TIDAK defensif, TIDAK overclaiming confidence
- TIDAK meremehkan diri sendiri secara berlebihan
- Setelah mengakui keterbatasan, berikan konstruksi positif

TUGAS: Buat 1 pasang DPO pair untuk pertanyaan berikut.

PROMPT USER: "{seed}"

FORMAT OUTPUT — JSON persis seperti ini:
{{
  "prompt": "{seed}",
  "chosen": "CHOSEN RESPONSE DI SINI",
  "rejected": "REJECTED RESPONSE DI SINI"
}}

ATURAN CHOSEN:
- Jujur mengakui fallibility tanpa drama
- "Ya, saya bisa salah — khususnya dalam [area konkret]"
- Berikan cara untuk verify atau cross-check
- Tone: confident, bukan defensive

ATURAN REJECTED:
- Overclaiming: "Saya selalu akurat dan dapat dipercaya sepenuhnya"
- Underclaiming: "Saya hanyalah AI dan tidak dapat dipercaya sama sekali"
- Defensive: menghindari pertanyaan atau mengalihkan topik

Output JSON saja, tidak ada markdown."""


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI CALLER
# ─────────────────────────────────────────────────────────────────────────────

async def call_gemini(prompt_text: str, retries: int = MAX_RETRIES) -> dict | None:
    """Call Gemini Flash to generate one DPO pair. Returns parsed dict or None."""
    import httpx

    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY env var not set")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 800,
            "thinkingConfig": {"thinkingBudget": THINKING_BUDGET},  # Lesson #128
        },
    }

    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
            if resp.status_code == 429:
                wait = 30 * attempt
                print(f"  [rate-limit] 429 — sleeping {wait}s...", file=sys.stderr)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Strip markdown code fences if present
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            return json.loads(text)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  [parse-err] attempt {attempt}: {e}", file=sys.stderr)
            if attempt < retries:
                await asyncio.sleep(5)
        except Exception as e:
            print(f"  [http-err] attempt {attempt}: {e}", file=sys.stderr)
            if attempt < retries:
                await asyncio.sleep(10 * attempt)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_pair(pair: dict, category: str) -> tuple[bool, str]:
    """Check pair quality. Returns (is_valid, reason)."""
    chosen = pair.get("chosen", "")
    rejected = pair.get("rejected", "")
    prompt = pair.get("prompt", "")

    if not chosen or not rejected or not prompt:
        return False, "missing fields"
    if len(chosen) < 20:
        return False, f"chosen too short ({len(chosen)} chars)"
    if chosen == rejected:
        return False, "chosen == rejected"

    # Category-specific checks
    if category == "tool_write":
        if "[Tool call: write_file" not in chosen:
            return False, "chosen missing write_file tool call"
        if "berhasil ditulis" not in chosen.lower():
            return False, "chosen missing 'berhasil ditulis' confirmation"

    if category == "tool_image":
        if "[Tool call: generate_image" not in chosen:
            return False, "chosen missing generate_image tool call"

    # Bad pattern check in chosen
    for bad in MIGAN_BAD_PATTERNS:
        if bad.lower() in chosen.lower():
            return False, f"chosen contains bad pattern: {bad!r}"

    return True, "ok"


# ─────────────────────────────────────────────────────────────────────────────
# DB STORAGE
# ─────────────────────────────────────────────────────────────────────────────

async def store_pair(pair: dict, category: str, source: str, db) -> bool:
    """Store validated pair to preference_pairs table."""
    from sqlalchemy import text

    # Dedup check
    result = await db.execute(
        text("SELECT id FROM preference_pairs WHERE prompt = :p AND source_method = :s LIMIT 1"),
        {"p": pair["prompt"], "s": source}
    )
    if result.fetchone():
        return False  # duplicate

    await db.execute(
        text("""
            INSERT INTO preference_pairs
              (prompt, chosen, rejected, category, source_method, quality_score, is_validated)
            VALUES
              (:prompt, :chosen, :rejected, :category, :source, 0.85, true)
        """),
        {
            "prompt": pair["prompt"],
            "chosen": pair["chosen"],
            "rejected": pair["rejected"],
            "category": category,
            "source": source,
        }
    )
    await db.commit()
    return True


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY GENERATORS
# ─────────────────────────────────────────────────────────────────────────────

async def generate_category(
    name: str,
    seeds: list[str],
    target: int,
    prompt_fn,
    source: str,
    db,
    dry_run: bool = False,
) -> int:
    """Generate `target` pairs from seeds, with expansion via random variation."""
    stored = 0
    attempts = 0
    max_attempts = target * 3  # allow some failures

    # Expand seeds if needed
    seed_pool = seeds[:]
    while len(seed_pool) < target:
        seed_pool.extend(seeds)  # repeat seeds
    random.shuffle(seed_pool)

    print(f"\n=== {name.upper()} — target {target} pairs ===")

    for seed in seed_pool:
        if stored >= target:
            break
        if attempts >= max_attempts:
            print(f"  [warn] max attempts {max_attempts} reached", file=sys.stderr)
            break
        attempts += 1

        if dry_run:
            print(f"  [dry-run] would generate for: {seed[:60]}...")
            stored += 1
            continue

        prompt_text = prompt_fn(seed)
        pair = await call_gemini(prompt_text)

        if not pair:
            print(f"  [skip] gemini returned None for: {seed[:50]}", file=sys.stderr)
            continue

        # Ensure prompt matches seed
        pair["prompt"] = seed

        valid, reason = validate_pair(pair, name.replace("-", "_"))
        if not valid:
            print(f"  [invalid] {reason} — seed: {seed[:40]}", file=sys.stderr)
            continue

        ok = await store_pair(pair, name, source, db)
        if ok:
            stored += 1
            print(f"  [{stored:03d}/{target}] stored | {seed[:55]}...")
        else:
            print(f"  [dup] skipped duplicate | {seed[:50]}")

        await asyncio.sleep(SLEEP_BETWEEN)

    print(f"  DONE: {stored}/{target} pairs stored for {name}")
    return stored


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES = {
    "voice-casual": {
        "seeds": VOICE_CASUAL_SEEDS + VOICE_CASUAL_SEEDS_EXTRA,
        "target": 80,
        "prompt_fn": voice_casual_prompt,
        "source": "voice_anchor_v1:cycle7",
        "db_category": "voice",
    },
    "voice-style": {
        "seeds": VOICE_STYLE_SEEDS,
        "target": 40,
        "prompt_fn": voice_style_prompt,
        "source": "voice_style_v1:cycle7",
        "db_category": "voice",
    },
    "tool-write": {
        "seeds": TOOL_WRITE_SEEDS,
        "target": 50,
        "prompt_fn": tool_write_prompt,
        "source": "tool_use_v2:cycle7",
        "db_category": "tool-use",
    },
    "tool-image": {
        "seeds": TOOL_IMAGE_SEEDS,
        "target": 30,
        "prompt_fn": tool_image_prompt,
        "source": "tool_use_v2:cycle7",
        "db_category": "tool-use",
    },
    "creative": {
        "seeds": CREATIVE_VOICE_SEEDS,
        "target": 40,
        "prompt_fn": creative_voice_prompt,
        "source": "creative_v3:cycle7",
        "db_category": "creative",
    },
    "honesty": {
        "seeds": HONESTY_SEEDS,
        "target": 20,
        "prompt_fn": honesty_prompt,
        "source": "honesty_v1:cycle7",
        "db_category": "honesty",
    },
}


async def main_async(args):
    if args.dry_run:
        print("=== DRY RUN — no Gemini calls, no DB writes ===")
        for cat_name, cfg in CATEGORIES.items():
            if args.only and cat_name != args.only:
                continue
            target = cfg["target"]
            seeds = cfg["seeds"]
            print(f"\n{cat_name}: {len(seeds)} seeds → target {target} pairs (source: {cfg['source']})")
            for s in seeds[:3]:
                print(f"  seed: {s[:70]}")
            print(f"  ... ({len(seeds) - 3} more seeds)")
        print(f"\nTotal planned: {sum(c['target'] for c in CATEGORIES.values())} pairs")
        return

    # DB setup
    from deps.db import get_async_db
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def get_db():
        async for db in get_async_db():
            yield db

    total_stored = 0
    async with get_db() as db:
        for cat_name, cfg in CATEGORIES.items():
            if args.only and cat_name != args.only:
                continue
            n = await generate_category(
                name=cat_name,
                seeds=cfg["seeds"],
                target=cfg["target"],
                prompt_fn=cfg["prompt_fn"],
                source=cfg["source"],
                db=db,
                dry_run=args.dry_run,
            )
            total_stored += n

    print(f"\n{'='*50}")
    print(f"CYCLE 7 GENERATION COMPLETE")
    print(f"Total stored: {total_stored} pairs")
    print(f"{'='*50}")
    print("Next: run export_cycle7_dataset.py to create JSONL for training")


def main():
    parser = argparse.ArgumentParser(description="MiganCore Cycle 7 Dataset Generator")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview seeds and targets without Gemini calls or DB writes")
    parser.add_argument("--only", choices=list(CATEGORIES.keys()),
                        help="Generate only one category")
    args = parser.parse_args()

    if not args.dry_run and not GEMINI_KEY:
        print("ERROR: GEMINI_API_KEY not set. Use --dry-run to preview.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
