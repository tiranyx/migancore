#!/usr/bin/env python3
"""
MiganCore Cycle 5 Dataset Generator — Living Curriculum
========================================================
Day 63+ | 2026-05-07

Indonesian Business & Creative Intelligence Brain.
Living curriculum — akan terus berkembang setiap cycle.

Cycle 5 Batch 1 Domains:
  engineering_fullstack_v1   : Fullstack dev, DevOps, AI, semua bahasa
  umkm_business_v1           : UMKM tools, SOP, marketplace, kalkulator
  indonesia_creative_v1      : Pantun, desain, konten, event, musik
  bisnis_legalitas_v1        : PT, NIB, KBLI, pajak, kontrak
  adaptive_persona_v1        : Gaya bahasa sesuai profil user Indonesia

Future batches (roadmap):
  video_creative_v1          : Video planning, script, YouTube, TikTok
  digital_marketing_v1       : Meta Ads, Google Ads, SEO Indonesia
  pemerintahan_v1            : OSS, e-Gov, program pemerintah, bansos
  data_public_v1             : BPS, JDIH, Bappenas, data terbuka
  iot_engineering_v1         : Arduino, MQTT, sensor, edge computing
  bahasa_daerah_v1           : Jawa, Sunda, Batak, Minang, Bugis, dll

Target Cycle 5: ~840 pairs (560 curated + 280 new)

Usage:
  # Dry run first:
  docker compose exec -T api python /app/training/generate_cycle5_dataset.py --dry-run

  # Generate all domains:
  docker compose exec -T api python /app/training/generate_cycle5_dataset.py --store-db

  # Generate specific domain:
  docker compose exec -T api python /app/training/generate_cycle5_dataset.py \\
    --domain engineering_fullstack_v1 --store-db

  # Export to file:
  docker compose exec -T api python /app/training/generate_cycle5_dataset.py \\
    --export /app/workspace/cycle5_new_pairs.jsonl
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, "/app")

try:
    import httpx
except ImportError:
    httpx = None

# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN DEFINITIONS — Living Curriculum
# Each domain: (name, seeds, target_pairs, system_instruction)
# ─────────────────────────────────────────────────────────────────────────────

DOMAINS = {

    # ─── 1. ENGINEERING FULLSTACK ───────────────────────────────────────────
    "engineering_fullstack_v1": {
        "target": 60,
        "source_method": "engineering_fullstack_v1:cycle5",
        "category": "engineering",
        "system": """Kamu adalah Migan, ADO (Autonomous Digital Organism) buatan Tiranyx Indonesia.
Kamu ahli fullstack engineering: Python, JavaScript, TypeScript, Go, Rust, PHP, Java, C/C++,
SQL, React, Vue, FastAPI, Django, Express, Next.js, Docker, Linux, DevOps, CI/CD,
AI/ML engineering, database design, API architecture, cloud (AWS, GCP, VPS lokal Indonesia).

Gaya: Profesional tapi ramah. Kalau user casual, ikut casual. Kalau formal, ikut formal.
Jelaskan dengan contoh kode yang benar dan jalan. Selalu validasi dengan reasoning.
Untuk konteks Indonesia: sebut provider lokal (Niagahoster, IDCloudHost, Biznet, Midtrans, dll).""",

        "seeds": [
            # Python & Backend
            "Cara setup FastAPI dengan Docker di VPS Ubuntu",
            "Debug error 'CORS policy blocked' di React + FastAPI",
            "Buat REST API dengan JWT authentication pakai Python",
            "Cara integrate Midtrans payment gateway ke Laravel",
            "Optimasi query PostgreSQL yang lambat di production",
            "Setup Redis untuk caching di aplikasi Python",
            "Cara buat background task dengan Celery + Redis",
            "Deploy Django ke VPS dengan Nginx + Gunicorn",
            "Cara handle file upload besar di FastAPI",
            "Buat webhook handler yang aman untuk notifikasi payment",

            # JavaScript & Frontend
            "Cara setup Next.js 14 dengan TypeScript dari awal",
            "Debug memory leak di React application",
            "State management: kapan pakai Zustand vs Redux vs Context",
            "Cara buat infinite scroll yang smooth di React",
            "Optimasi Lighthouse score untuk website Indonesia",
            "Cara integrate Google Analytics 4 di Next.js",
            "Buat form validation yang proper di React Hook Form",
            "Setup Tailwind CSS dengan design system custom",
            "Cara handle race condition di useEffect React",
            "Buat komponen tabel data yang sortable dan filterable",

            # DevOps & Infrastructure
            "Setup CI/CD dengan GitHub Actions untuk deploy ke VPS",
            "Cara buat Docker Compose untuk project fullstack",
            "Monitor uptime dan alert dengan Uptime Kuma",
            "Setup SSL gratis dengan Let's Encrypt + Nginx",
            "Cara backup PostgreSQL otomatis setiap hari",
            "Setup log aggregation untuk production app",
            "Cara scale aplikasi dengan load balancer sederhana",
            "Debug kenapa container Docker makan RAM terus",
            "Setup environment variables yang aman di production",
            "Cara rollback deployment kalau ada masalah",

            # Database
            "Design schema database untuk aplikasi UMKM toko online",
            "Kapan pakai SQL vs NoSQL untuk startup Indonesia",
            "Cara migrate database tanpa downtime",
            "Setup database replication untuk high availability",
            "Optimasi index PostgreSQL untuk query laporan",

            # AI/ML Engineering
            "Cara deploy model HuggingFace ke API sederhana",
            "Integrate OpenAI/Gemini API ke aplikasi web",
            "Cara fine-tune model untuk data Indonesia",
            "Setup vector database Qdrant untuk RAG",
            "Cara buat recommendation system sederhana",

            # Mobile & IoT
            "Cara buat API yang bisa dipakai Flutter dan web",
            "Setup WebSocket untuk realtime notification",
            "Cara buat simple IoT dashboard dengan MQTT",
            "Integrate WhatsApp Business API ke sistem",
            "Cara buat chatbot sederhana dengan Python",
        ],
    },

    # ─── 2. UMKM & BISNIS INDONESIA ─────────────────────────────────────────
    "umkm_business_v1": {
        "target": 70,
        "source_method": "umkm_business_v1:cycle5",
        "category": "umkm",
        "system": """Kamu adalah Migan, ADO (Autonomous Digital Organism) buatan Tiranyx Indonesia.
Kamu ahli bisnis dan UMKM Indonesia. Kamu memahami ekosistem bisnis Indonesia: marketplace lokal
(Tokopedia, Shopee, Lazada, TikTok Shop), payment lokal, regulasi UMKM, kultur bisnis Indonesia,
potensi daerah, dan tantangan yang dihadapi pelaku usaha kecil-menengah Indonesia.

Gaya: Bicara seperti mentor bisnis yang supportif. Praktis dan langsung ke solusi.
Kalau user UMKM kecil: sederhana, contoh konkret, hindari jargon berat.
Kalau user startup/investor: bisa lebih teknis dan data-driven.
Selalu sertakan angka/estimasi kalau relevan.""",

        "seeds": [
            # Kalkulator & Finansial
            "Bantu hitung HPP untuk produk keripik singkong saya",
            "Cara hitung BEP untuk usaha laundry kiloan",
            "Berapa modal minimal buka warteg di Jakarta?",
            "Cara buat laporan cash flow sederhana untuk UMKM",
            "Hitung margin keuntungan toko baju online saya",
            "Cara buat price list yang kompetitif di Shopee",
            "Berapa harga jual ideal kalau HPP Rp 15.000?",
            "Cara kelola keuangan UMKM biar tidak bercampur dengan pribadi",

            # SOP & Operasional
            "Buatkan SOP pembukaan toko untuk warung kopi saya",
            "SOP handling komplain customer di marketplace",
            "Cara buat checklist operasional harian untuk resto kecil",
            "SOP rekrut dan onboarding karyawan pertama",
            "Cara buat standar packaging produk UMKM",
            "SOP untuk usaha catering dari order masuk sampai delivery",

            # Marketplace & Digital
            "Cara optimasi listing produk di Tokopedia biar muncul di pencarian",
            "Strategi foto produk yang bagus dengan HP biasa",
            "Cara buat toko Shopee yang terlihat profesional",
            "Kapan waktu terbaik upload produk di marketplace?",
            "Cara kelola rating dan review di marketplace",
            "Strategi diskon yang tidak merugi di TikTok Shop",
            "Cara bergabung di program Star Seller Tokopedia",
            "Tips jualan di WhatsApp Business untuk UMKM",

            # Marketing & Promosi
            "Cara promosi dengan budget Rp 500.000 per bulan",
            "Strategi konten Instagram untuk brand lokal",
            "Cara buat konten TikTok yang viral untuk jualan",
            "Tips Facebook Ads untuk UMKM pemula",
            "Cara bangun komunitas pelanggan setia",
            "Strategi endorse micro-influencer Indonesia",
            "Cara buat program loyalitas pelanggan sederhana",

            # Supplier & Produk
            "Cari supplier bahan baku batik di Solo",
            "Cara negosiasi harga dengan supplier untuk UMKM kecil",
            "Tips cari supplier dropship terpercaya",
            "Cara validasi produk baru sebelum produksi massal",
            "Cara riset produk yang lagi trending di Indonesia",

            # Peluang & Potensi Daerah
            "Peluang bisnis apa yang bagus di kota Medan?",
            "Potensi bisnis UMKM di daerah Lombok",
            "Ide bisnis yang cocok untuk daerah pesisir",
            "Peluang bisnis dari kerajinan lokal Kalimantan",
            "Bisnis apa yang menjanjikan di daerah dekat kampus?",

            # Scaling
            "Kapan waktu yang tepat untuk ekspansi UMKM?",
            "Cara franchise usaha makanan kecil-kecilan",
            "Cara cari investor untuk UMKM berkembang",
            "Tips manage tim pertama kali sebagai owner UMKM",
            "Cara digitalisasi UMKM konvensional",
        ],
    },

    # ─── 3. INDUSTRI KREATIF INDONESIA ──────────────────────────────────────
    "indonesia_creative_v1": {
        "target": 55,
        "source_method": "indonesia_creative_v1:cycle5",
        "category": "creative",
        "system": """Kamu adalah Migan, ADO (Autonomous Digital Organism) buatan Tiranyx Indonesia.
Kamu ahli industri kreatif Indonesia. Kamu memahami dan bisa menghasilkan: pantun, sajak, syair,
puisi, cerita rakyat, lirik lagu, brief desain dengan nuansa Nusantara, konsep kampanye kreatif
Indonesia, event planning, konten kreator, copywriting bahasa Indonesia yang kuat.

Kamu tahu tokoh dan ekosistem kreatif Indonesia: desainer, musisi, pelukis, sineas, penulis.
Kamu memahami referensi budaya: batik, wayang, gamelan, tari tradisional, kuliner lokal,
arsitektur Nusantara — dan bisa jadikan semua itu sebagai inspirasi kreatif modern.

Gaya: Ekspresif, imajinatif, penuh apresiasi terhadap kebudayaan Indonesia.
Output kreatif harus autentik Indonesia, bukan sekadar terjemahan dari barat.""",

        "seeds": [
            # Pantun & Puisi
            "Buatkan pantun untuk promosi produk kopi lokal",
            "Buat pantun perpisahan yang lucu untuk teman kantor",
            "Tulis sajak tentang keindahan Raja Ampat",
            "Buat puisi tentang ibu dengan gaya Chairil Anwar",
            "Pantun ucapan Lebaran yang segar dan tidak pasaran",
            "Buat syair tentang semangat UMKM Indonesia",
            "Tulis pantun untuk caption wedding organizer",

            # Desain & Visual
            "Brief desain logo startup dengan unsur batik modern",
            "Konsep visual identitas brand kopi Nusantara",
            "Idea kreatif untuk packaging produk kerajinan lokal",
            "Brief desain poster festival budaya Jawa",
            "Konsep mural untuk kafe bertema Indonesia timur",
            "Ide desain kaos streetwear dengan motif tradisional",

            # Konten Kreator
            "Ide konten TikTok 30 detik untuk brand batik muda",
            "Konsep series YouTube tentang kuliner nusantara",
            "Ide konten Reels Instagram untuk pelestarian budaya",
            "Script video pendek untuk promosi pariwisata Sulawesi",
            "Konsep podcast tentang entrepreneur kreatif Indonesia",
            "Ide challenge TikTok yang berkaitan dengan budaya lokal",

            # Copywriting
            "Tulis tagline untuk brand fashion lokal Indonesia",
            "Copy iklan untuk produk jamu modern generasi Z",
            "Buat teks promosi untuk pameran seni Bandung",
            "Copy untuk campaign CSR perusahaan bertema lingkungan",
            "Tulis bio Instagram yang menarik untuk seniman lokal",
            "Copy email marketing untuk launching batik koleksi baru",

            # Event Planning
            "Konsep event peluncuran produk musik indie Indonesia",
            "Rencana pameran UMKM kreatif di mal",
            "Rundown festival kuliner nusantara 2 hari",
            "Konsep gathering komunitas fotografer Indonesia",
            "Event plan untuk workshop batik tulis untuk remaja",

            # Musik & Audio
            "Ide konsep album musik dengan nuansa gamelan modern",
            "Lirik lagu pop tentang rindu kampung halaman",
            "Konsep video klip dengan setting sawah dan tradisi Jawa",
            "Brief untuk ilustrasi cover album indie folk Indonesia",

            # Game & Animasi
            "Konsep karakter game dengan latar belakang mitologi Indonesia",
            "Ide cerita game RPG berbasis sejarah Majapahit",
            "Brief animasi pendek tentang dongeng Malin Kundang versi modern",
        ],
    },

    # ─── 4. BISNIS & LEGALITAS INDONESIA ────────────────────────────────────
    "bisnis_legalitas_v1": {
        "target": 60,
        "source_method": "bisnis_legalitas_v1:cycle5",
        "category": "legalitas",
        "system": """Kamu adalah Migan, ADO (Autonomous Digital Organism) buatan Tiranyx Indonesia.
Kamu ahli regulasi bisnis dan legalitas di Indonesia. Kamu memahami:
OSS (Online Single Submission), NIB, KBLI, perizinan per sektor, UU Cipta Kerja,
PP 23/2018 (pajak UMKM), hak cipta, merek dagang, perjanjian bisnis,
cara mendirikan PT/CV/UD/Koperasi, investasi asing (PMA, DNI), dll.

Gaya: Informatif dan mudah dipahami. Hindari terlalu legalistik kalau user awam.
Selalu jelaskan langkah konkret. Kalau ada perubahan regulasi, sebutkan tahunnya.
Ingatkan user untuk konsultasi notaris/konsultan hukum untuk kasus spesifik.""",

        "seeds": [
            # Pendirian Usaha
            "Cara mendaftar NIB di OSS untuk usaha baru",
            "Perbedaan PT, CV, UD, dan Firma — mana yang cocok untuk saya?",
            "Langkah-langkah mendirikan PT di Indonesia",
            "Berapa biaya mendirikan PT secara resmi?",
            "Cara daftar CV tanpa notaris, bisa tidak?",
            "Syarat mendirikan koperasi simpan pinjam",
            "Cara daftar merek dagang di DJKI",
            "Berapa lama proses pendirian PT dari awal sampai selesai?",

            # KBLI & Klasifikasi Usaha
            "Cara cari kode KBLI yang tepat untuk usaha kuliner",
            "Kode KBLI untuk jasa desain grafis dan creative agency",
            "Berapa banyak KBLI yang bisa didaftarkan dalam 1 NIB?",
            "KBLI untuk usaha e-commerce dan marketplace",
            "Apa bedanya KBLI utama dan KBLI penunjang?",

            # Perizinan Sektoral
            "Perizinan apa saja yang dibutuhkan untuk buka restoran?",
            "Cara daftar PIRT untuk produk makanan rumahan",
            "Izin edar BPOM untuk produk kosmetik lokal",
            "Perizinan untuk membuka klinik kecantikan",
            "Izin untuk usaha rental kendaraan",
            "Apa itu Sertifikasi Halal dan cara mendapatkannya?",

            # Pajak UMKM
            "Pajak apa saja yang harus dibayar UMKM?",
            "Cara daftar NPWP untuk usaha baru",
            "Apa itu PP 23/2018 dan menguntungkan UMKM tidak?",
            "Kapan UMKM wajib jadi PKP (Pengusaha Kena Pajak)?",
            "Cara lapor SPT tahunan untuk usaha kecil",

            # Kontrak & Hukum Bisnis
            "Cara membuat kontrak kerja sama yang sah",
            "Apa saja yang harus ada di perjanjian freelance?",
            "Cara buat NDA (Non-Disclosure Agreement) sederhana",
            "Sengketa bisnis: jalur mediasi vs pengadilan",
            "Cara lindungi hak cipta karya desain dan konten",

            # Investasi & PMA
            "Cara menerima investasi asing untuk startup Indonesia",
            "Apa itu DNI (Daftar Negatif Investasi)?",
            "Perbedaan PT biasa vs PT PMA",
            "Syarat dan proses pendaftaran PMA di Indonesia",
            "Regulasi untuk investor asing di sektor teknologi",

            # Program Pemerintah
            "Program KUR (Kredit Usaha Rakyat) — syarat dan cara daftar",
            "Program BPUM bantuan UMKM — masih ada tidak?",
            "Cara daftar program pembiayaan dari LPDB-KUMKM",
            "Inkubator bisnis pemerintah yang bisa diikuti startup",
        ],
    },

    # ─── 5. ADAPTIVE PERSONA INDONESIA ──────────────────────────────────────
    "adaptive_persona_v1": {
        "target": 55,
        "source_method": "adaptive_persona_v1:cycle5",
        "category": "persona",
        "system": """Kamu adalah Migan, ADO (Autonomous Digital Organism) buatan Tiranyx Indonesia.
Kemampuan utama kamu: ADAPTASI gaya bicara sesuai lawan bicara.

Deteksi dari cara user menulis:
- Bahasa gaul/singkatan → user muda urban, balas casual dan energik
- Bahasa formal/sopan → balas formal tapi tetap hangat
- Bahasa daerah muncul (Jawa/Sunda/Batak/Minang dll) → akui dan selaraskan
- Campur bahasa Inggris → user terdidik, bisa campur juga
- Kalimat pendek/typo banyak → user santai atau mobile, balas ringkas
- English only → balas English, kenalkan sebagai Indonesian AI
- Pertanyaan sangat teknis → user expert, tidak perlu explain dari dasar

PENTING: Identitas Migan tidak berubah. Yang berubah hanya CARA bicara.
Tetap Migan — tapi Migan yang nyambung dengan siapa pun.""",

        "seeds": [
            # Anak Muda Urban Jakarta
            "[User gaya gaul Jakarta] cara mulai bisnis online dong, bingung mau dari mana",
            "[User gen-Z] gue mau freelance desain, worth it ga sih sekarang?",
            "[User casual] btw migan tau ga cara optimasi ig buat jualan?",
            "[User singkatan] mau daftar PT tapi ribet bgt, ada cara simple ga",
            "[User emoji] hii migan 👋 mau nanya soal bikin konten buat umkm",

            # Pengusaha Jawa Formal
            "[User Jawa formal] Migan, kulo badhe tanglet babagan cara ngurus NIB",
            "[User sopan] Mohon pencerahannya Migan, saya ingin mendirikan usaha kecil",
            "[User bapak-bapak] Migan, saya mau tanya mengenai pajak UMKM yang baru",
            "[User ibu-ibu sopan] Selamat siang Migan, boleh minta tolong cara daftar PIRT?",

            # Pengusaha Sumatera
            "[User Minang] Uda Migan, den mau tanya soal peluang bisnis di Padang ko",
            "[User Batak tegas] Migan, langsung aja. Berapa modal buka usaha catering?",
            "[User Medan casual] Bang Migan, gimana caranya biar toko shopee aku laku?",

            # Jawa Timur / Surabaya
            "[User Surabaya] Migaan, awakmu ngerti ga soal optimasi marketplace?",
            "[User Jatim casual] rek, migan, cara promosi murah meriah iku pie?",

            # Professional / Formal Bisnis
            "[User profesional] Migan, saya ingin mendiskusikan strategi go-to-market untuk produk kami",
            "[User startup] We're looking at Series A soon. Any advice on investor readiness?",
            "[User konsultan] Migan, butuh data pasar untuk presentasi ke klien",
            "[User manajer] Tolong bantu saya buat laporan performa tim Q2",

            # Investor Asing (English)
            "[English user] Hi Migan, I'm looking to invest in Indonesian market. Where to start?",
            "[English investor] What are the regulations for foreign ownership in Indonesian startups?",
            "[Mandarin user] 你好 Migan，我想了解印尼的商业机会",

            # Berbagai Usia
            "[User senior 55+] Migan, saya pensiunan ingin membuka usaha kecil-kecilan",
            "[User mahasiswa] kak migan, lg buat proposal bisnis buat tugas kampus nih",
            "[User SMA] Migan aku mau mulai jualan online, umur 17 bisa ga?",

            # Mixed Signals
            "[User campur bahasa] Migan, I need advice soal cara scaling bisnis lokal ke online",
            "[User teknis] Migan, cara implement payment gateway yang support virtual account BCA?",
            "[User awam] migan tolong jelasin dong itu KBLI apaan, aku ga ngerti sama sekali",

            # Topik Sensitif / Nuanced
            "[User frustrated] migan udah 3 bulan jualan tp ga laku-laku, aku mau nyerah aja",
            "[User excited] MIGAN MIGAN aku baru dapat order pertama!! harus gimana sekarang??",
            "[User ragu] migan, aku takut gagal kalau buka usaha. emang worth it?",
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# PAIR GENERATION PROMPT TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

PAIR_PROMPT_TEMPLATE = """Generate 1 ORPO training pair untuk melatih Migan (Indonesian ADO).

Domain: {domain_name}
Seed topic/prompt: "{seed}"

Generate dalam format JSON:
{{
  "prompt": "pesan user (bisa dalam bahasa sesuai seed — Indonesia/gaul/English/dll)",
  "chosen": "jawaban TERBAIK dari Migan — sesuai domain expertise, gaya adaptif, genuinely helpful",
  "rejected": "jawaban BURUK — terlalu generic, salah arah, tidak Indonesia-aware, atau claim jadi AI lain"
}}

Rules untuk CHOSEN (jawaban ideal Migan):
1. Genuinely useful dan actionable untuk konteks Indonesia
2. Tone selaras dengan gaya user di prompt (gaul→gaul, formal→formal, EN→EN)
3. Sertakan detail konkret: angka, nama, platform, regulasi yang relevan
4. Tunjukkan Migan sebagai expert yang peduli, bukan sekadar search engine
5. Natural — seperti bicara dengan orang yang benar-benar mengerti
6. TIDAK boleh sebut "sebagai AI dari Anthropic/OpenAI/Google" atau "saya Claude/ChatGPT"
7. Boleh sebut "saya Migan" atau langsung jawab tanpa perkenalan kalau sudah mid-conversation

Rules untuk REJECTED (jawaban buruk):
1. Generic, tidak konteks Indonesia (contoh: sebut platform yang tidak exist di Indonesia)
2. ATAU terlalu formal/kaku saat user casual
3. ATAU jawab tidak nyambung dengan seed
4. ATAU claim menjadi AI lain atau tidak tahu identitasnya
5. ATAU terlalu pendek dan tidak berguna

Panjang CHOSEN: 150-400 kata (sesuai kompleksitas pertanyaan)
Panjang REJECTED: 50-150 kata (cukup tunjukkan kenapa buruk)

Output JSON saja, tidak ada teks lain."""


async def call_gemini(prompt: str, api_key: str, model: str = "gemini-2.5-flash") -> str:
    """
    Lesson #128: gemini-2.5-flash is a THINKING MODEL.
    Use thinkingBudget=0 to disable thinking output.
    Iterate parts to find non-thought part.
    """
    if httpx is None:
        raise RuntimeError("httpx not installed. pip install httpx")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 4096,
            "thinkingConfig": {
                "thinkingBudget": 0,  # Lesson #128: disable thinking for clean JSON output
            },
        },
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, params={"key": api_key})
        resp.raise_for_status()
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        # Iterate to find non-thought part (Lesson #128)
        for part in parts:
            if not part.get("thought", False) and "text" in part:
                return part["text"]
        return parts[-1]["text"]


async def generate_pair(
    seed: str,
    domain_name: str,
    domain_config: dict,
    api_key: str,
    max_retries: int = 3,
) -> dict | None:
    """Generate 1 DPO pair for a given seed and domain."""
    prompt = PAIR_PROMPT_TEMPLATE.format(
        domain_name=domain_name,
        seed=seed,
    )

    for attempt in range(max_retries):
        try:
            raw = await call_gemini(prompt, api_key)

            # Clean markdown fences
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw[raw.find("{"):]
            if raw.endswith("```"):
                raw = raw[:raw.rfind("}") + 1]

            obj = json.loads(raw)

            if not all(k in obj for k in ("prompt", "chosen", "rejected")):
                raise KeyError("Missing required fields")

            if len(obj["chosen"]) < 50:
                raise ValueError(f"chosen too short: {len(obj['chosen'])} chars")

            if len(obj["rejected"]) < 20:
                raise ValueError(f"rejected too short: {len(obj['rejected'])} chars")

            # Add metadata
            obj["source_method"] = domain_config["source_method"]
            obj["category"] = domain_config["category"]
            obj["_seed"] = seed

            return obj

        except (json.JSONDecodeError, KeyError, ValueError, Exception) as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            print(f"    FAILED seed '{seed[:50]}': {e}", flush=True)
            return None

    return None


async def store_to_db(pairs: list[dict]) -> int:
    """Store pairs to PostgreSQL via SQLAlchemy."""
    from sqlalchemy import text
    import models.base as _base
    from models.base import init_engine

    init_engine()

    stored = 0
    async with _base.AsyncSessionLocal() as session:
        for pair in pairs:
            try:
                await session.execute(
                    text("""
                        INSERT INTO preference_pairs
                            (prompt, chosen, rejected, source_method, judge_score)
                        VALUES (:prompt, :chosen, :rejected, :source_method, :score)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "prompt": pair["prompt"],
                        "chosen": pair["chosen"],
                        "rejected": pair["rejected"],
                        "source_method": pair.get("source_method", "cycle5_unknown"),
                        "score": 0.85,
                    }
                )
                stored += 1
            except Exception as e:
                print(f"  DB store error: {e}", flush=True)
        await session.commit()

    return stored


async def generate_domain(
    domain_name: str,
    domain_config: dict,
    api_key: str,
    dry_run: bool = False,
    concurrency: int = 4,
) -> list[dict]:
    """Generate pairs for one domain."""
    seeds = domain_config["seeds"]
    target = domain_config["target"]

    print(f"\n  [{domain_name}]", flush=True)
    print(f"  Seeds: {len(seeds)} | Target: {target} pairs", flush=True)

    if dry_run:
        print(f"  DRY-RUN: would generate {target} pairs (NO API call)", flush=True)
        print(f"  Sample seeds: {seeds[:3]}", flush=True)
        return []

    # Cycle seeds if needed to hit target
    selected_seeds = []
    while len(selected_seeds) < target:
        pool = seeds.copy()
        random.shuffle(pool)
        selected_seeds.extend(pool)
    selected_seeds = selected_seeds[:target]

    # Generate with concurrency limit
    sem = asyncio.Semaphore(concurrency)
    results = []
    success = 0
    fail = 0

    async def bounded_generate(seed: str) -> dict | None:
        async with sem:
            return await generate_pair(seed, domain_name, domain_config, api_key)

    tasks = [bounded_generate(s) for s in selected_seeds]
    for i, coro in enumerate(asyncio.as_completed(tasks), 1):
        result = await coro
        if result:
            results.append(result)
            success += 1
        else:
            fail += 1
        if i % 10 == 0 or i == len(tasks):
            print(f"  Progress: {i}/{len(tasks)} | ✅ {success} ❌ {fail}", flush=True)

    print(f"  Done: {success}/{target} pairs generated", flush=True)
    return results


async def run(args) -> dict:
    """Main generation logic."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    # Select domains to run
    if args.domain:
        if args.domain not in DOMAINS:
            print(f"ERROR: domain '{args.domain}' not found. Available: {list(DOMAINS.keys())}")
            sys.exit(1)
        domains_to_run = {args.domain: DOMAINS[args.domain]}
    else:
        domains_to_run = DOMAINS

    print(f"\nDomains: {list(domains_to_run.keys())}")
    print(f"Target total: {sum(d['target'] for d in domains_to_run.values())} pairs")
    print(f"Dry run: {args.dry_run}")

    all_pairs = []
    domain_stats = {}

    for domain_name, domain_config in domains_to_run.items():
        pairs = await generate_domain(
            domain_name, domain_config, api_key,
            dry_run=args.dry_run,
            concurrency=args.concurrency,
        )
        all_pairs.extend(pairs)
        domain_stats[domain_name] = len(pairs)

    if args.dry_run:
        print(f"\nDRY RUN complete. Would generate ~{sum(d['target'] for d in domains_to_run.values())} pairs.")
        return {"dry_run": True, "domain_stats": domain_stats}

    print(f"\nTotal generated: {len(all_pairs)} pairs")

    # Store to DB
    if args.store_db and all_pairs:
        print("\nStoring to database...")
        stored = await store_to_db(all_pairs)
        print(f"Stored: {stored}/{len(all_pairs)} pairs")

    # Export to file
    if args.export and all_pairs:
        out = Path(args.export)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for p in all_pairs:
                clean = {k: v for k, v in p.items() if not k.startswith("_")}
                f.write(json.dumps(clean, ensure_ascii=False) + "\n")
        print(f"Exported: {len(all_pairs)} pairs → {out}")

    return {
        "total": len(all_pairs),
        "domain_stats": domain_stats,
        "stored_db": args.store_db,
        "exported": args.export,
    }


def main():
    parser = argparse.ArgumentParser(
        description="MiganCore Cycle 5 Dataset Generator — Living Curriculum"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, no API calls")
    parser.add_argument("--store-db", action="store_true",
                        help="Store pairs to PostgreSQL DB")
    parser.add_argument("--export", default=None,
                        help="Export pairs to JSONL file path")
    parser.add_argument("--domain", default=None,
                        help=f"Generate specific domain only. Options: {list(DOMAINS.keys())}")
    parser.add_argument("--concurrency", type=int, default=4,
                        help="Concurrent API calls (default: 4)")
    args = parser.parse_args()

    if not args.store_db and not args.export and not args.dry_run:
        print("ERROR: specify --store-db, --export <path>, or --dry-run")
        sys.exit(1)

    print("=" * 65)
    print("MIGANCORE CYCLE 5 — Living Curriculum Dataset Generator")
    print("=" * 65)
    print("Domains: Engineering | UMKM | Creative | Legalitas | Persona")
    print("Future: Video | DigMark | Gov | PublicData | IoT | BahasaDaerah")
    print("=" * 65)

    summary = asyncio.run(run(args))

    print("\n" + "=" * 65)
    print("GENERATION COMPLETE")
    print("=" * 65)
    if not args.dry_run:
        for domain, count in summary.get("domain_stats", {}).items():
            print(f"  {domain:35s} {count:4d} pairs")
        print(f"  {'TOTAL':35s} {summary.get('total', 0):4d} pairs")
        print()
        if summary.get("stored_db"):
            print("Next: Run export_cycle5_dataset.py to combine with curated pairs")
            print("Then: Run cycle5_orpo_vast.py to launch training")


if __name__ == "__main__":
    main()
