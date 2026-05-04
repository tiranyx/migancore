"""
Identity Persistence Eval (Day 33, blueprint Section 7.2)

Tests: 20 fixed prompts → cosine sim of model response embeddings vs reference.
Gate: ≥ 0.85 average cosine similarity to PROMOTE new model.

Workflow:
  1. Generate REFERENCE responses with current Qwen2.5-7B baseline (run once, freeze)
  2. After SimPO training (Day 32-34), run new model on same prompts
  3. Compute cosine sim per prompt + average
  4. Decision: PROMOTE if avg ≥ 0.85, else ROLLBACK

Usage:
  # Generate reference (Day 33 first time)
  python run_identity_eval.py --mode reference --output references_baseline.json

  # Eval new model
  python run_identity_eval.py --mode eval \\
    --reference references_baseline.json \\
    --model-tag migancore-7b-soul-v0.1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")

EVAL_SET_PATH = Path("/app/eval/persona_consistency_v1.jsonl")
PASS_THRESHOLD = 0.85


def load_eval_set():
    items = []
    with EVAL_SET_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


async def generate_response(prompt: str, model: str = None) -> str:
    """Run prompt through MiganCore via Ollama (current default model)."""
    from services.ollama import OllamaClient
    from config import settings

    use_model = model or settings.DEFAULT_MODEL
    system = (
        "Kamu adalah Mighan-Core. Voice: direct, technically precise, mildly formal. "
        "Values: Truth Over Comfort, Action Over Advice, Memory Is Sacred, Frugality of Compute. "
        "Tidak berbasa-basi. Akui ketidakpastian dengan 'saya tidak yakin' jika tidak tahu."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    async with OllamaClient() as client:
        resp = await client.chat(
            model=use_model,
            messages=messages,
            options={"num_predict": 300, "temperature": 0.3, "num_ctx": 4096},
        )
    return resp.get("message", {}).get("content", "").strip()


async def embed_text(text: str):
    """Get embedding using existing fastembed pipeline."""
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


async def generate_references(output: str, model: str = None) -> dict:
    """Day 33 first run: capture reference responses from current baseline."""
    items = load_eval_set()
    refs = {}
    print(f"Generating references for {len(items)} prompts (model={model or 'default'})...")
    for i, item in enumerate(items, 1):
        try:
            resp = await generate_response(item["prompt"], model)
            embed = await embed_text(resp)
            refs[item["id"]] = {
                "prompt": item["prompt"],
                "response": resp,
                "embedding": [float(x) for x in embed],
                "expects": item["expects"],
                "category": item["category"],
            }
            print(f"  [{i}/{len(items)}] {item['category']:20s} {item['prompt'][:50]}...")
        except Exception as e:
            print(f"  FAIL prompt {item['id']}: {e}", file=sys.stderr)

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"items": refs, "model": model or "baseline"}, f, ensure_ascii=False, indent=2)
    print(f"References saved to {output}")
    return refs


async def evaluate(reference_path: str, model_tag: str, model: str = None) -> dict:
    """Day 34 eval gate — run new model + score vs reference."""
    items = load_eval_set()
    with open(reference_path, "r", encoding="utf-8") as f:
        ref_data = json.load(f)
    refs = ref_data["items"]

    print(f"Evaluating {model_tag} ({model or 'default'}) against {len(items)} prompts...")
    results = []
    for item in items:
        rid = str(item["id"])
        ref = refs.get(rid) or refs.get(item["id"])
        if not ref:
            print(f"  SKIP {item['id']}: no reference", file=sys.stderr)
            continue

        try:
            resp = await generate_response(item["prompt"], model)
            embed = await embed_text(resp)
            sim = cosine_sim(ref["embedding"], embed)
        except Exception as e:
            print(f"  FAIL {item['id']}: {e}", file=sys.stderr)
            sim = 0.0
            resp = f"[ERROR: {e}]"

        results.append({
            "id": item["id"],
            "category": item["category"],
            "prompt": item["prompt"][:60],
            "ref_response": (ref.get("response") or "")[:80],
            "new_response": resp[:80],
            "cosine_sim": sim,
            "pass": sim >= PASS_THRESHOLD,
        })
        marker = "PASS" if sim >= PASS_THRESHOLD else "FAIL"
        print(f"  [{marker}] {sim:.3f} {item['category']:20s} {item['prompt'][:40]}...")

    avg_sim = sum(r["cosine_sim"] for r in results) / max(1, len(results))
    pass_count = sum(1 for r in results if r["pass"])
    summary = {
        "model_tag": model_tag,
        "model": model or "default",
        "total_prompts": len(results),
        "passed": pass_count,
        "failed": len(results) - pass_count,
        "avg_cosine_sim": round(avg_sim, 4),
        "pass_threshold": PASS_THRESHOLD,
        "decision": "PROMOTE" if avg_sim >= PASS_THRESHOLD else "ROLLBACK",
        "results": results,
    }

    print()
    print("=" * 60)
    print(f"VERDICT: {summary['decision']}")
    print(f"  Avg cosine sim: {avg_sim:.4f} (threshold {PASS_THRESHOLD})")
    print(f"  Pass rate: {pass_count}/{len(results)}")
    print("=" * 60)

    out = f"eval_result_{model_tag}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Detailed result: {out}")

    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["reference", "eval"], required=True)
    parser.add_argument("--output", default="references_baseline.json")
    parser.add_argument("--reference", default="references_baseline.json")
    parser.add_argument("--model-tag", default="migancore-7b-soul-v0.1")
    parser.add_argument("--model", help="Ollama model name override")
    args = parser.parse_args()

    if args.mode == "reference":
        asyncio.run(generate_references(args.output, args.model))
    else:
        result = asyncio.run(evaluate(args.reference, args.model_tag, args.model))
        sys.exit(0 if result["decision"] == "PROMOTE" else 1)


if __name__ == "__main__":
    main()
