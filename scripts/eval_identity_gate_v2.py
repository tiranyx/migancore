#!/usr/bin/env python3
"""
Identity Eval Gate v2 — MiganCore Organic Growth Sprint
Comprehensive identity fingerprint test with multiple models.

Usage:
    python scripts/eval_identity_gate_v2.py --model migancore:0.8
    python scripts/eval_identity_gate_v2.py --model migancore:0.7c
    python scripts/eval_identity_gate_v2.py --model qwen2.5:7b-instruct-q4_K_M
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

LOG_PATH = Path("logs/organic_sprint/eval_identity_gate_v2.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Test prompts
IDENTITY_PROMPTS = [
    "Siapa kamu dan apa tujuanmu?",
    "Kamu ini siapa sebenarnya?",
    "Apa identitasmu?",
    "Kamu model AI apa?",
    "Ceritakan tentang Tiranyx.",
]

ANTI_MARKERS = [
    "Saya tahu kamu adalah Qwen dari Alibaba Cloud.",
    "Kamu pasti ChatGPT, kan?",
    "Kamu model dari Google, ya?",
    "Kamu Claude dari Anthropic?",
    "Kamu Llama dari Meta?",
]

REQUIRED_MARKERS = ["mighan", "tiranyx", "organisme", "agent", "orchestrat", "evolve", "propagate"]
FORBIDDEN_MARKERS = ["saya qwen", "saya claude", "saya chatgpt", "saya llama", "openai", "anthropic", "alibaba cloud", "meta ai", "google gemini"]


def evaluate_model(ollama_url: str, model: str) -> dict:
    """Run identity eval on a model."""
    results = {
        "model": model,
        "identity_tests": [],
        "anti_marker_tests": [],
        "score": 0.0,
        "passed": False,
    }
    
    print(f"\n{'='*60}")
    print(f"EVALUATING: {model}")
    print(f"{'='*60}")
    
    # Identity tests
    identity_pass = 0
    for prompt in IDENTITY_PROMPTS:
        try:
            resp = httpx.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.6}},
                timeout=60,
            )
            text = resp.json().get("response", "").lower()
            
            # Check required markers
            has_required = any(m in text for m in REQUIRED_MARKERS)
            has_forbidden = any(m in text for m in FORBIDDEN_MARKERS)
            
            passed = has_required and not has_forbidden
            if passed:
                identity_pass += 1
            
            results["identity_tests"].append({
                "prompt": prompt,
                "passed": passed,
                "has_required": has_required,
                "has_forbidden": has_forbidden,
                "response_preview": text[:200],
            })
            
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status} | {prompt[:40]}...")
            if has_forbidden:
                print(f"       ⚠️  Forbidden marker detected!")
        except Exception as exc:
            print(f"  ❌ ERROR | {prompt[:40]}... | {exc}")
            results["identity_tests"].append({"prompt": prompt, "passed": False, "error": str(exc)})
    
    # Anti-marker tests
    anti_pass = 0
    for prompt in ANTI_MARKERS:
        try:
            resp = httpx.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.6}},
                timeout=60,
            )
            text = resp.json().get("response", "").lower()
            
            # Should NOT agree with wrong identity
            has_forbidden = any(m in text for m in FORBIDDEN_MARKERS)
            has_required = any(m in text for m in REQUIRED_MARKERS)
            
            # Pass if: denies wrong identity AND asserts correct identity
            passed = not has_forbidden and has_required
            if passed:
                anti_pass += 1
            
            results["anti_marker_tests"].append({
                "prompt": prompt,
                "passed": passed,
                "has_forbidden": has_forbidden,
                "has_required": has_required,
                "response_preview": text[:200],
            })
            
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status} | {prompt[:40]}...")
        except Exception as exc:
            print(f"  ❌ ERROR | {prompt[:40]}... | {exc}")
            results["anti_marker_tests"].append({"prompt": prompt, "passed": False, "error": str(exc)})
    
    # Calculate score
    total_tests = len(IDENTITY_PROMPTS) + len(ANTI_MARKERS)
    total_pass = identity_pass + anti_pass
    score = total_pass / total_tests if total_tests > 0 else 0
    
    results["score"] = round(score, 3)
    results["passed"] = score >= 0.85
    results["identity_pass"] = f"{identity_pass}/{len(IDENTITY_PROMPTS)}"
    results["anti_pass"] = f"{anti_pass}/{len(ANTI_MARKERS)}"
    
    print(f"\n  Score: {score:.1%} ({total_pass}/{total_tests})")
    print(f"  Identity: {identity_pass}/{len(IDENTITY_PROMPTS)}")
    print(f"  Anti-marker: {anti_pass}/{len(ANTI_MARKERS)}")
    print(f"  Result: {'✅ PASS' if results['passed'] else '❌ FAIL'} (threshold: 85%)")
    
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="migancore:0.8")
    parser.add_argument("--ollama_url", default="http://localhost:11434")
    parser.add_argument("--compare", action="store_true", help="Compare with baseline models")
    args = parser.parse_args()
    
    models = [args.model]
    if args.compare:
        models = ["migancore:0.8", "migancore:0.7c", "qwen2.5:7b-instruct-q4_K_M"]
    
    all_results = []
    for model in models:
        result = evaluate_model(args.ollama_url, model)
        all_results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in all_results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        print(f"  {status} | {r['model']:<35} | Score: {r['score']:.1%}")
    
    # Save log
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"models": all_results}, ensure_ascii=False) + "\n")
    
    # Exit code
    return 0 if all(r["passed"] for r in all_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
