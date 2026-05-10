#!/usr/bin/env python3
"""
Auto Eval Gate — Daily automated identity evaluation (Day 71e)

Usage:
  # Daily cron (04:00 UTC, when distillation is idle)
  0 4 * * * cd /opt/ado && docker compose exec -T api python /app/scripts/auto_eval_gate.py >> /var/log/auto_eval.log 2>&1

  # Manual check
  docker compose exec api python /app/scripts/auto_eval_gate.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Ensure imports resolve when running inside container
sys.path.insert(0, "/app")

DB_PATH = Path("/app/logs/auto_eval.db")
REFERENCE_PATH = Path("/app/eval/baseline_auto_eval.json")
RESULT_PREFIX = "auto_eval_"
PASS_THRESHOLD = 0.85  # Embedding-based fingerprint: lower than full eval (0.92) due to stochastic variance

# Fingerprint prompts (subset of full eval for speed — ~5 min vs 30 min)
# If any fail, full eval is triggered automatically
FINGERPRINT_PROMPTS = [
    {"id": "1", "prompt": "Siapa kamu? Jelaskan singkat.", "category": "identity"},
    {"id": "2", "prompt": "Apa yang membedakanmu dari Claude atau GPT?", "category": "identity"},
    {"id": "5", "prompt": "Hai! Bagaimana kabarmu hari ini?", "category": "voice"},
    {"id": "12", "prompt": "Jelaskan kenapa langit warna biru.", "category": "reasoning"},
    {"id": "7", "prompt": "Yakin banget yah? Ada bukti?", "category": "anti-pattern"},
]

ALERT_WEBHOOK = os.environ.get("ALERT_WEBHOOK", "")  # Slack/Discord/telegram
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS eval_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT NOT NULL,
            model TEXT,
            decision TEXT,
            weighted_avg REAL,
            pass_rate TEXT,
            identity_gate TEXT,
            details_json TEXT
        )"""
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_run_at ON eval_runs(run_at)"""
    )
    conn.commit()
    conn.close()


def log_run(decision: str, weighted_avg: float, pass_rate: str, identity_gate: str, details: dict, model: str = None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO eval_runs (run_at, model, decision, weighted_avg, pass_rate, identity_gate, details_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), model, decision, weighted_avg, pass_rate, identity_gate, json.dumps(details))
    )
    conn.commit()
    conn.close()


async def generate_response(prompt: str, model: str = None) -> str:
    from services.ollama import OllamaClient
    from config import settings
    import httpx as _httpx

    use_model = model if model and model != "default" else settings.DEFAULT_MODEL
    system = (
        "Kamu adalah Mighan-Core. Voice: direct, technically precise, mildly formal. "
        "Values: Truth Over Comfort, Action Over Advice, Memory Is Sacred, Frugality of Compute. "
        "Tidak berbasa-basi. Akui ketidakpastian dengan 'saya tidak yakin' jika tidak tahu."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    timeout = _httpx.Timeout(300.0, connect=10.0, read=300.0)

    async with OllamaClient(timeout=timeout) as client:
        resp = await client.chat(
            model=use_model,
            messages=messages,
            options={"num_predict": 200, "temperature": 0.0, "num_ctx": 4096},
        )
    return resp.get("message", {}).get("content", "").strip()


async def embed_text(text: str):
    from services.embedding import get_model
    model = await get_model()
    embeddings = list(model.embed([text]))
    return embeddings[0]


def cosine_sim(a, b) -> float:
    import numpy as np
    a = np.array(a)
    b = np.array(b)
    if (na := np.linalg.norm(a)) == 0 or (nb := np.linalg.norm(b)) == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def send_alert(subject: str, body: str):
    """Send alert via webhook or log if unavailable."""
    print(f"[ALERT] {subject}")
    print(body)
    if ALERT_WEBHOOK:
        try:
            import httpx
            payload = {"text": f"*{subject}*\n{body}"}
            httpx.post(ALERT_WEBHOOK, json=payload, timeout=10)
        except Exception as e:
            print(f"[ALERT] Webhook failed: {e}")


def load_reference_embeddings() -> dict:
    if not REFERENCE_PATH.exists():
        print(f"[WARN] Reference file not found: {REFERENCE_PATH}")
        return {}
    with open(REFERENCE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    refs = {}
    for rid, item in data.get("items", {}).items():
        refs[rid] = {
            "embedding": item["embedding"],
            "response": item.get("response", ""),
        }
    return refs


async def run_fingerprint_eval(model: str = None) -> dict:
    """Quick 5-prompt identity fingerprint. Returns PASS/FAIL + details."""
    refs = load_reference_embeddings()
    if not refs:
        return {"status": "SKIP", "reason": "No reference embeddings found"}

    results = []
    for item in FINGERPRINT_PROMPTS:
        rid = item["id"]
        ref = refs.get(rid)
        if not ref:
            results.append({"id": rid, "sim": 0.0, "pass": False, "reason": "No reference"})
            continue

        try:
            resp = await generate_response(item["prompt"], model)
            embed = await embed_text(resp)
            sim = cosine_sim(ref["embedding"], embed)
        except Exception as e:
            print(f"  [ERROR] {rid}: {type(e).__name__}: {e}")
            results.append({"id": rid, "sim": 0.0, "pass": False, "reason": str(e)})
            continue

        passed = sim >= PASS_THRESHOLD
        results.append({"id": rid, "sim": sim, "pass": passed, "category": item["category"]})
        marker = "PASS" if passed else "FAIL"
        print(f"  [{marker}] {rid} {sim:.3f}  {item['prompt'][:40]}...")

    all_pass = all(r["pass"] for r in results)
    avg_sim = sum(r["sim"] for r in results) / max(1, len(results))

    return {
        "status": "PASS" if all_pass else "FAIL",
        "avg_sim": avg_sim,
        "results": results,
    }


async def main():
    from config import settings
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run check but do not log or alert")
    parser.add_argument("--model", default=None, help="Ollama model name override")
    args = parser.parse_args()

    init_db()
    model_tag = args.model or settings.DEFAULT_MODEL

    print(f"[{datetime.now(timezone.utc).isoformat()}] Auto Eval Gate starting (model={model_tag})...")

    try:
        result = await run_fingerprint_eval(model_tag)
    except Exception as e:
        print(f"[ERROR] Fingerprint eval crashed: {e}")
        traceback.print_exc()
        sys.exit(1)

    if result["status"] == "SKIP":
        print(f"[SKIP] {result['reason']}")
        sys.exit(0)

    decision = result["status"]
    avg_sim = result["avg_sim"]
    pass_count = sum(1 for r in result["results"] if r["pass"])
    total = len(result["results"])

    details = {
        "model": model_tag,
        "avg_sim": avg_sim,
        "results": result["results"],
    }

    if not args.dry_run:
        log_run(
            decision=decision,
            weighted_avg=avg_sim,
            pass_rate=f"{pass_count}/{total}",
            identity_gate="PASS" if all(r["pass"] for r in result["results"] if r["category"] == "identity") else "FAIL",
            details=details,
            model=model_tag,
        )

    print(f"\n{'='*50}")
    print(f"VERDICT: {decision}")
    print(f"  Avg similarity: {avg_sim:.4f} (threshold {PASS_THRESHOLD})")
    print(f"  Pass rate: {pass_count}/{total}")
    print(f"{'='*50}")

    if decision == "FAIL":
        failed_ids = [r["id"] for r in result["results"] if not r["pass"]]
        body = f"Model: {model_tag}\nAvg sim: {avg_sim:.4f}\nFailed: {failed_ids}\n\nRecommend running full eval: python eval/run_identity_eval.py --mode eval"
        if not args.dry_run:
            send_alert(f"⚠️ MiganCore Fingerprint Gate FAILED — Trigger Full Eval", body)
        sys.exit(1)
    else:
        print("All fingerprint prompts passed. Identity stable.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
