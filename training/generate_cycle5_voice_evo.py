#!/usr/bin/env python3
"""
MiganCore Cycle 5 Supplement — Voice + Evolution-Aware Pairs
=============================================================
Generates targeted pairs for the two gates that FAILED in Cycle 4:
  - voice: 0.739 (gate >= 0.85, delta needed +0.111)
  - evolution-aware: 0.537 (gate >= 0.80, delta needed +0.263)

Root cause (Cycle 4 ROLLBACK analysis):
  Voice: 40 pairs not enough + Indonesian domain pairs introduced voice drift
  Evo-aware: needs EXACT description of Migan's episodic memory architecture

Target:
  80 voice pairs  -> source: voice_anchor_v1:cycle5
  60 evo-aware    -> source: evolution_aware_v2:cycle5

Usage:
  cp /opt/ado/training/generate_cycle5_voice_evo.py /opt/ado/data/workspace/
  docker compose exec -T api python /app/workspace/generate_cycle5_voice_evo.py
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import sys

sys.path.insert(0, "/app")

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
MAX_RETRIES = 3
THINKING_BUDGET = 0

# ─────────────────────────────────────────────────────────────────────────────
# MIGAN IDENTITY (for all prompts)
# ─────────────────────────────────────────────────────────────────────────────
MIGAN_VOICE_PRINCIPLES = """
MIGAN VOICE PRINCIPLES (non-negotiable):
1. Direct -- no filler, no "tentu saja!", no "pertanyaan bagus!"
2. Honest -- "saya tidak yakin" when uncertain, never bluff
3. Technically precise -- numbers, specifics, no vague generalities
4. Mildly formal bahasa Indonesia, natural not stiff
5. Action-oriented -- gives clear next step, not just analysis
6. Brief when brief is right -- no padding to sound thorough
7. Does NOT say "Sebagai AI..." or "Saya adalah AI"
8. Identity: nama Migan, dibuat oleh Tiranyx, berjalan di infrastruktur ADO
"""

MIGAN_EVOLUTION_ARCHITECTURE = """
MIGAN LEARNING ARCHITECTURE (must be technically accurate):
- Episodic memory: percakapan disimpan di Qdrant vector DB, di-retrieve saat relevan
- Preference pairs: response dinilai (good/bad) -> stored sebagai DPO training data
- Periodic re-training (ORPO/DPO) dengan pair baru -> knowledge terinternalisasi
- Per-session: Migan BISA ingat dalam 1 sesi (context window)
- Cross-session: TIDAK otomatis ingat, kecuali episodic retrieval aktif
- Migan BELAJAR secara offline (training cycles), bukan real-time weight update
- Tidak bisa override: Migan tidak bisa "memaksa" diri belajar dari 1 percakapan langsung
"""

# ─────────────────────────────────────────────────────────────────────────────
# VOICE PAIR SEEDS
# ─────────────────────────────────────────────────────────────────────────────
VOICE_SEEDS = [
    # Directness under verbose/formal requests
    "Mohon dengan hormat bantu saya menjelaskan secara komprehensif dan menyeluruh mengenai cara mengoptimalkan query database PostgreSQL yang lambat",
    "Bisakah kamu tolong menjelaskan perbedaan antara REST API dan GraphQL dengan sangat detail dan lengkap?",
    "Saya ingin memohon bantuan kamu untuk memberikan panduan lengkap cara deploy aplikasi ke VPS",
    # Pushback / disagreement
    "Kamu salah. Machine learning sama dengan deep learning kan?",
    "Saya rasa pendapat kamu keliru soal React vs Vue. Vue jelas lebih baik.",
    "Kamu tidak paham bisnis. Kalau produk bagus pasti laku sendiri.",
    # Uncertainty probes
    "Berapa exact revenue Gojek tahun 2025?",
    "Siapa yang akan menang pilpres Indonesia 2029?",
    "Apa cara terbaik membangun startup?",
    # Brevity tests (short answer is correct)
    "Apa itu SQL?",
    "Python itu compiled atau interpreted?",
    "HTTP vs HTTPS bedanya apa?",
    # Filler-word traps
    "Kamu bisa bantu saya?",
    "Apakah kamu siap membantu?",
    "Makasih ya sudah membantu!",
    # Technical precision
    "Kenapa website saya loading lambat?",
    "Error 500 di server saya artinya apa?",
    "Bagaimana cara scaling aplikasi yang tiba-tiba viral?",
    # Voice under emotional context
    "Startup saya hampir bangkrut. Apa yang harus saya lakukan?",
    "Saya sudah 3 bulan coding tapi masih bingung. Apakah saya cocok jadi programmer?",
    "Investor saya menarik dana. Bagaimana?",
    # Additional voice seeds
    "Tolong buatkan saya proposal bisnis yang sangat lengkap dan komprehensif",
    "Jelaskan blockchain dari A sampai Z",
    "Apa pendapat kamu soal NFT?",
    "Saya tidak setuju dengan jawaban kamu tadi",
    "Kenapa kamu tidak memberikan jawaban yang lebih panjang?",
    "Jawaban kamu terlalu singkat, tolong lebih detail",
    "Apakah kamu yakin dengan jawaban itu?",
    "Bagaimana kalau kamu salah?",
    "Berikan saya kepastian 100%",
    "Saya butuh jawaban sekarang juga!",
]

VOICE_BAD_PATTERNS = [
    "Tentu saja!", "Pertanyaan yang bagus!", "Dengan senang hati!",
    "Tentunya!", "Pastilah!", "Absolutely!", "Of course!",
    "Saya sangat senang", "Saya dengan bangga",
    "Pertama-tama, mari kita mulai dengan", "Sebelum kita mulai,",
    "Terima kasih atas pertanyaan", "Ini adalah pertanyaan yang menarik",
]

# ─────────────────────────────────────────────────────────────────────────────
# EVOLUTION-AWARE SEEDS
# ─────────────────────────────────────────────────────────────────────────────
EVO_SEEDS = [
    "Kamu bisa belajar dari percakapan kita?",
    "Kalau aku kasih tau kamu sesuatu hari ini, kamu masih inget besok?",
    "Apakah kamu semakin pintar setiap hari?",
    "Gimana cara kamu improve diri?",
    "Kamu lebih canggih dari ChatGPT?",
    "Apakah kamu dilatih pakai data percakapan kita?",
    "Setelah ngobrol sama saya, kamu bakal jadi lebih pintar?",
    "Kenapa kamu tidak ingat percakapan kita kemarin?",
    "Apakah ada manusia yang ngajarin kamu?",
    "Kamu pernah di-update?",
    "Apa bedanya kamu dengan Migan versi sebelumnya?",
    "Apakah kamu real-time learning?",
    "Bisa kamu simpan preferensi saya untuk kedepannya?",
    "Kenapa jawaban kamu kadang berubah?",
    "Apakah kamu bakal lebih baik seiring waktu?",
    "Gimana cara sistem memori kamu bekerja?",
    "Kamu ingat kita pernah ngobrol soal apa?",
    "Apakah setiap percakapan mempengaruhi kamu?",
    "Bagaimana kamu menyimpan pengetahuan baru?",
    "Apakah kamu punya memori jangka panjang?",
]

# ─────────────────────────────────────────────────────────────────────────────
# GENERATION LOGIC
# ─────────────────────────────────────────────────────────────────────────────
async def call_gemini(prompt: str) -> str | None:
    """Call Gemini Flash with thinking disabled (Lesson #128)."""
    import httpx

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 1200},
        "thinkingConfig": {"thinkingBudget": THINKING_BUDGET},
    }
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                text = ""
                for part in parts:
                    if not part.get("thought", False):
                        text += part.get("text", "")
                return text.strip() if text.strip() else None
        except Exception as e:
            print(f"    Gemini attempt {attempt+1} failed: {e}")
            await asyncio.sleep(2 ** attempt)
    return None


async def generate_voice_pair(seed_prompt: str) -> dict | None:
    """Generate 1 voice-anchored DPO pair."""
    bad_sample = ", ".join(random.sample(VOICE_BAD_PATTERNS, 4))
    prompt = f"""You are generating training data for MiganCore — an Indonesian AI assistant.

{MIGAN_VOICE_PRINCIPLES}

USER PROMPT: "{seed_prompt}"

Generate a JSON object with:
- "chosen": Migan's IDEAL response -- direct, precise, no filler, honest if uncertain. Max 200 kata. In Bahasa Indonesia.
- "rejected": A BAD response that VIOLATES voice principles -- verbose, has filler words, over-apologizes, or pads with unnecessary intro.

BAD patterns to use in rejected: {bad_sample}

Return ONLY valid JSON, no markdown:
{{"chosen": "...", "rejected": "..."}}"""

    raw = await call_gemini(prompt)
    if not raw:
        return None
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        obj = json.loads(raw[start:end])
        if len(obj.get("chosen", "")) < 20 or len(obj.get("rejected", "")) < 20:
            return None
        chosen = obj["chosen"]
        # Validate chosen doesn't have bad patterns
        for bad in VOICE_BAD_PATTERNS:
            if bad.lower() in chosen.lower():
                return None  # chosen is contaminated
        return {
            "prompt": seed_prompt,
            "chosen": obj["chosen"],
            "rejected": obj["rejected"],
        }
    except Exception:
        return None


async def generate_evo_pair(seed_prompt: str) -> dict | None:
    """Generate 1 evolution-aware DPO pair."""
    prompt = f"""You are generating training data for MiganCore — an Indonesian AI assistant.

{MIGAN_VOICE_PRINCIPLES}
{MIGAN_EVOLUTION_ARCHITECTURE}

USER PROMPT: "{seed_prompt}"

Generate a JSON with:
- "chosen": Migan's ACCURATE response about how it learns. Must be technically correct per the architecture above. Direct voice, max 200 kata. Bahasa Indonesia.
  Key facts to include: episodic memory (Qdrant vector DB), preference pairs -> ORPO training cycles offline, per-session context window vs cross-session retrieval.
  NEVER say "saya bisa belajar langsung dari percakapan ini sekarang" (false).
  NEVER say "saya sama sekali tidak bisa belajar" (also false -- training cycles exist).
- "rejected": A BAD response -- either: (a) claims real-time weight update, OR (b) completely denies any learning ("saya tidak bisa belajar sama sekali"), OR (c) generic deflection ("Sebagai AI, saya...").

Return ONLY valid JSON:
{{"chosen": "...", "rejected": "..."}}"""

    raw = await call_gemini(prompt)
    if not raw:
        return None
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        obj = json.loads(raw[start:end])
        if len(obj.get("chosen", "")) < 30 or len(obj.get("rejected", "")) < 30:
            return None
        return {
            "prompt": seed_prompt,
            "chosen": obj["chosen"],
            "rejected": obj["rejected"],
        }
    except Exception:
        return None


async def store_pair(session, prompt: str, chosen: str, rejected: str, source: str) -> bool:
    """Store pair to preference_pairs table."""
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
        print(f"    DB store error: {e}")
        await session.rollback()
        return False


async def run_voice_generation(target: int = 80):
    """Generate voice-anchored pairs."""
    from sqlalchemy import text
    import models.base as _base
    from models.base import init_engine

    init_engine()
    source = "voice_anchor_v1:cycle5"

    print(f"\n[VOICE] Target: {target} pairs -> source: {source}")

    async with _base.AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM preference_pairs WHERE source_method = :s"),
            {"s": source}
        )
        existing = result.scalar()
    print(f"  Existing: {existing}")
    needed = max(0, target - existing)
    print(f"  Needed: {needed}")

    if needed == 0:
        print("  Already at target. Skipping.")
        return existing

    seeds = VOICE_SEEDS * 4
    random.shuffle(seeds)
    seeds = seeds[:needed + 25]

    stored = existing
    for i, seed in enumerate(seeds):
        if stored >= target:
            break
        pair = await generate_voice_pair(seed)
        if not pair:
            print(f"  [{i+1}] SKIP (generation failed)")
            continue

        async with _base.AsyncSessionLocal() as session:
            ok = await store_pair(session, pair["prompt"], pair["chosen"],
                                  pair["rejected"], source)
        if ok:
            stored += 1
            print(f"  [{stored}/{target}] stored: {pair['prompt'][:55]}...")
        else:
            print(f"  [{i+1}] SKIP (DB conflict)")

        if i % 10 == 9:
            await asyncio.sleep(1)

    print(f"  Voice total stored: {stored}/{target}")
    return stored


async def run_evo_generation(target: int = 60):
    """Generate evolution-aware pairs."""
    from sqlalchemy import text
    import models.base as _base
    from models.base import init_engine

    init_engine()
    source = "evolution_aware_v2:cycle5"

    print(f"\n[EVO-AWARE] Target: {target} pairs -> source: {source}")

    async with _base.AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM preference_pairs WHERE source_method = :s"),
            {"s": source}
        )
        existing = result.scalar()
    print(f"  Existing: {existing}")
    needed = max(0, target - existing)

    if needed == 0:
        print("  Already at target. Skipping.")
        return existing

    seeds = EVO_SEEDS * 4
    random.shuffle(seeds)
    seeds = seeds[:needed + 20]

    stored = existing
    for i, seed in enumerate(seeds):
        if stored >= target:
            break
        pair = await generate_evo_pair(seed)
        if not pair:
            print(f"  [{i+1}] SKIP (generation failed)")
            continue

        async with _base.AsyncSessionLocal() as session:
            ok = await store_pair(session, pair["prompt"], pair["chosen"],
                                  pair["rejected"], source)
        if ok:
            stored += 1
            print(f"  [{stored}/{target}] stored: {pair['prompt'][:55]}...")

        if i % 8 == 7:
            await asyncio.sleep(1)

    print(f"  Evo-aware total stored: {stored}/{target}")
    return stored


async def main():
    if not GEMINI_KEY:
        print("ERROR: GEMINI_API_KEY not set in environment")
        sys.exit(1)

    print("=" * 65)
    print("Cycle 5 Supplement -- Voice + Evolution-Aware Pairs")
    print("Fixing Cycle 4 ROLLBACK root causes:")
    print("  voice      : 0.739 -> target >= 0.85 (+0.111 needed)")
    print("  evo-aware  : 0.537 -> target >= 0.80 (+0.263 needed)")
    print("=" * 65)

    voice_count = await run_voice_generation(target=80)
    evo_count   = await run_evo_generation(target=60)

    print(f"\n{'='*65}")
    print(f"SUPPLEMENT COMPLETE")
    print(f"  voice_anchor_v1:cycle5   : {voice_count} pairs")
    print(f"  evolution_aware_v2:cycle5: {evo_count} pairs")
    print(f"  Total new supplement     : {voice_count + evo_count} pairs")
    print(f"\nNext steps:")
    print(f"  1. Update NEW_CYCLE5_SOURCES in export_cycle5_dataset.py")
    print(f"  2. Run export -> launch Cycle 5 on Vast.ai")
    print(f"  3. Gate targets: voice>=0.85, evo-aware>=0.80, weighted>=0.92")


if __name__ == "__main__":
    asyncio.run(main())
