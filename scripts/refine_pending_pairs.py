#!/usr/bin/env python3
"""
Teacher API Refinement — fill PENDING chosen fields in preference_pairs
from user thumbs_down signals.

Day 65: Completes the user-feedback → training flywheel loop.
  1. Fetch PreferencePairs where chosen="PENDING — awaiting teacher API refinement"
  2. For each: call Gemini 2.5 Flash teacher to generate a better response
  3. Update chosen field, judge_model, judge_score
  4. These completed pairs feed directly into next Cycle's ORPO dataset

Usage:
  python3 /opt/ado/scripts/refine_pending_pairs.py [--limit 20] [--dry-run]

Cron (run daily at 02:00 WIB = 19:00 UTC prev day):
  0 19 * * * python3 /opt/ado/scripts/refine_pending_pairs.py >> /tmp/refine_pairs.log 2>&1

Author: Claude Sonnet 4.6, Day 65
"""

import asyncio
import sys
import argparse
import json
import datetime
import urllib.request
import urllib.error
import os

# ── Config ───────────────────────────────────────────────────────────────────

PENDING_MARKER = "PENDING — awaiting teacher API refinement"
BATCH_LIMIT = 20
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

TEACHER_SYSTEM_PROMPT = """Kamu adalah expert AI assistant berbahasa Indonesia.
Tugasmu: baca PROMPT pengguna dan RESPON BURUK yang sudah ada, lalu tulis respon yang JAUH LEBIH BAIK.

Kriteria respon yang baik:
- Langsung menjawab pertanyaan pengguna (to the point)
- Bahasa Indonesia yang natural, hangat, santai tapi informatif
- Tidak bertele-tele, tidak repetitif
- Panjang proporsional dengan kompleksitas pertanyaan
- Jika pertanyaan tidak jelas, berikan jawaban umum yang membantu

Berikan HANYA teks respon yang lebih baik — tanpa penjelasan, tanpa prefix, tanpa komentar."""

TEACHER_USER_TEMPLATE = """PROMPT PENGGUNA:
{prompt}

RESPON BURUK (yang harus diperbaiki):
{rejected}

Tulis respon yang lebih baik:"""


# ── Gemini helper ─────────────────────────────────────────────────────────────

def call_gemini(prompt: str, rejected: str) -> str | None:
    """Call Gemini teacher API synchronously. Returns improved response or None."""
    if not GEMINI_API_KEY:
        print("  WARN: GEMINI_API_KEY not set — cannot refine", flush=True)
        return None

    payload = {
        "system_instruction": {"parts": [{"text": TEACHER_SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": TEACHER_USER_TEMPLATE.format(
            prompt=prompt,
            rejected=rejected,
        )}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
            "responseMimeType": "text/plain",
        },
    }

    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text if text else None
    except Exception as e:
        print(f"  WARN: Gemini error: {e}", flush=True)
        return None


# ── DB helpers ────────────────────────────────────────────────────────────────

async def get_pending_pairs(limit: int) -> list[dict]:
    """Fetch PENDING preference pairs from DB using asyncpg."""
    import asyncpg
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://ado_app@localhost:5432/ado"
    ).replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(dsn)
    try:
        rows = await conn.fetch(
            """
            SELECT id, prompt, rejected
            FROM preference_pairs
            WHERE chosen = $1 AND source_method = 'user_thumbs_down'
            ORDER BY created_at ASC
            LIMIT $2
            """,
            PENDING_MARKER,
            limit,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def update_pair(pair_id: str, chosen: str) -> None:
    """Update a preference pair's chosen field."""
    import asyncpg
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://ado_app@localhost:5432/ado"
    ).replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(
            """
            UPDATE preference_pairs
            SET chosen = $1, judge_model = $2, judge_score = $3
            WHERE id = $4
            """,
            chosen,
            f"teacher:{GEMINI_MODEL}",
            0.75,  # estimated quality
            pair_id,
        )
    finally:
        await conn.close()


# ── Main ─────────────────────────────────────────────────────────────────────

async def main(limit: int, dry_run: bool) -> None:
    now = datetime.datetime.utcnow().isoformat()
    print(f"[{now}] refine_pending_pairs.py starting (limit={limit}, dry_run={dry_run})", flush=True)

    try:
        pairs = await get_pending_pairs(limit)
    except Exception as e:
        print(f"ERROR: DB fetch failed: {e}", flush=True)
        sys.exit(1)

    print(f"  Found {len(pairs)} PENDING pair(s)", flush=True)

    if not pairs:
        print("[DONE] No pending pairs to refine.", flush=True)
        return

    refined = 0
    failed = 0
    for p in pairs:
        pair_id = str(p["id"])
        prompt = p["prompt"]
        rejected = p["rejected"]
        # Strip any appended user note from rejected text
        rejected_clean = rejected.split("\n\n[User note:")[0].strip()

        print(f"  Refining {pair_id[:8]}... prompt={repr(prompt[:60])}", flush=True)
        chosen = call_gemini(prompt, rejected_clean)
        if not chosen:
            print(f"    SKIP (Gemini returned None)", flush=True)
            failed += 1
            continue

        print(f"    OK → chosen={repr(chosen[:80])}", flush=True)
        if not dry_run:
            try:
                await update_pair(pair_id, chosen)
                refined += 1
            except Exception as e:
                print(f"    DB update failed: {e}", flush=True)
                failed += 1
        else:
            print(f"    DRY-RUN: would update {pair_id[:8]}", flush=True)
            refined += 1

    print(f"  Summary: {refined} refined, {failed} skipped/failed", flush=True)
    print(f"[DONE]", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refine PENDING preference pairs using teacher API")
    parser.add_argument("--limit", type=int, default=BATCH_LIMIT, help="Max pairs to process per run")
    parser.add_argument("--dry-run", action="store_true", help="Preview without DB changes")
    args = parser.parse_args()

    asyncio.run(main(args.limit, args.dry_run))
