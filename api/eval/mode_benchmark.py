#!/usr/bin/env python3
"""
Thinking Mode Eval Benchmark — v1.0 (Day 76)

Objective evaluation of mode detection accuracy.
Run this after deploy to measure real-world performance.

Usage:
    python -m eval.mode_benchmark --output eval_results.json

Scoring:
    - Exact match: detected == expected → 1.0
    - Related match: detected in same family → 0.5
    - Wrong: 0.0

Expected accuracy target: > 85%
"""

from __future__ import annotations

import argparse
import json
import time
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.cognitive.mode_selector import ModeSelector


@dataclass
class BenchmarkResult:
    total: int = 0
    correct: int = 0
    partial: int = 0
    wrong: int = 0
    accuracy: float = 0.0
    by_mode: dict[str, dict] = field(default_factory=dict)
    failures: list[dict] = field(default_factory=list)
    elapsed_ms: float = 0.0


# Test cases: (input, expected_mode, description)
TEST_CASES = [
    # === CODING (20 cases) ===
    ("buatkan script python untuk scraping", "coding", "code generation id"),
    ("buatkan function API endpoint", "coding", "API endpoint id"),
    ("debug error ini", "coding", "debug id"),
    ("code review untuk module ini", "coding", "code review id"),
    ("fix bug di authentication", "coding", "fix bug id"),
    ("python script untuk parse JSON", "coding", "python script en"),
    ("javascript function untuk sort array", "coding", "js function en"),
    ("html css layout responsive", "coding", "html css en"),
    ("traceback error saat runtime", "coding", "traceback id"),
    ("syntax error di line 42", "coding", "syntax error en"),
    ("refactor code ini biar clean", "coding", "refactor id"),
    ("unit test untuk class User", "coding", "unit test id"),
    ("algorithm sorting O(n log n)", "coding", "algorithm en"),
    ("api integration dengan stripe", "coding", "api integration en"),
    ("compile error di C++", "coding", "compile error en"),
    ("runtime exception null pointer", "coding", "runtime exception en"),
    ("buatkan kode CRUD operations", "coding", "CRUD id"),
    ("test coverage harus 80%", "coding", "test coverage en"),
    ("error handling untuk edge cases", "coding", "error handling en"),
    ("python decorator untuk logging", "coding", "decorator en"),

    # === INOVATIF (15 cases) ===
    ("ide baru untuk fitur dashboard", "inovatif", "ide fitur id"),
    ("desain arsitektur microservices", "inovatif", "desain arsitektur id"),
    ("brainstorm fitur AI", "inovatif", "brainstorm id"),
    ("bagaimana kalau kita tambahkan gamification?", "inovatif", "what if id"),
    ("creative solution untuk scaling", "inovatif", "creative solution en"),
    ("prototype untuk mobile app", "inovatif", "prototype en"),
    ("mockup UI/UX untuk landing page", "inovatif", "mockup en"),
    ("wireframe untuk user flow", "inovatif", "wireframe en"),
    ("alternatif approach untuk caching", "inovatif", "alternatif id"),
    ("variasi desain untuk logo", "inovatif", "variasi id"),
    ("improvement untuk current system", "inovatif", "improvement en"),
    ("enhancement untuk user experience", "inovatif", "enhancement en"),
    ("future roadmap untuk product", "inovatif", "roadmap en"),
    ("strategy untuk market expansion", "inovatif", "strategy en"),
    ("imagine kalau kita punya infinite compute", "inovatif", "imagine id"),

    # === SINTESIS (15 cases) ===
    ("bandingkan postgres vs mysql", "sintesis", "compare db id"),
    ("compare REST vs GraphQL", "sintesis", "compare API en"),
    ("vs antara monolith dan microservices", "sintesis", "vs architecture id"),
    ("bedanya SQL dan NoSQL", "sintesis", "bedanya id"),
    ("research tentang RAG implementations", "sintesis", "research en"),
    ("literature review tentang LLM safety", "sintesis", "literature en"),
    ("kombinasikan ide dari 3 paper ini", "sintesis", "kombinasikan id"),
    ("merge approach dari berbagai source", "sintesis", "merge en"),
    ("pros and cons dari serverless", "sintesis", "pros cons en"),
    ("kelebihan kekurangan kubernetes", "sintesis", "pros cons id"),
    ("analisis komprehensif market trends", "sintesis", "analisis komprehensif id"),
    ("review dari 5 tools monitoring", "sintesis", "review en"),
    ("survey penggunaan AI di Indonesia", "sintesis", "survey id"),
    ("synthesize findings dari user research", "sintesis", "synthesize en"),
    ("consolidate feedback dari stakeholder", "sintesis", "consolidate en"),

    # === AUTONOMOUS (12 cases) ===
    ("evaluasi performa hari ini", "autonomous", "evaluasi id"),
    ("refleksi dari sprint kemarin", "autonomous", "refleksi id"),
    ("apa yang salah dengan approach ini?", "autonomous", "apa yang salah id"),
    ("lesson learned dari deployment", "autonomous", "lesson learned en"),
    ("self-eval dari hasil eksperimen", "autonomous", "self-eval en"),
    ("post-mortem incident kemarin", "autonomous", "post-mortem en"),
    ("root cause dari latency spike", "autonomous", "root cause en"),
    ("improvement plan untuk Q3", "autonomous", "improvement plan en"),
    ("growth tracking untuk skill AI", "autonomous", "growth en"),
    ("evolusi arsitektur dari v1 ke v2", "autonomous", "evolusi id"),
    ("skill baru yang perlu dikuasai", "autonomous", "skill id"),
    ("mastery level untuk python", "autonomous", "mastery en"),

    # === KOGNITIF (15 cases) ===
    ("analisis kompleksitas algoritma ini", "kognitif", "analisis kompleksitas id"),
    ("jelaskan kenapa error terjadi", "kognitif", "jelaskan kenapa id"),
    ("bagaimana cara kerja neural network?", "kognitif", "cara kerja id"),
    ("proof bahwa O(n log n) optimal", "kognitif", "proof id"),
    ("reasoning untuk design decision ini", "kognitif", "reasoning en"),
    ("logic behind database indexing", "kognitif", "logic en"),
    ("matematika di balik gradient descent", "kognitif", "matematika id"),
    ("math formula untuk compound interest", "kognitif", "math en"),
    ("problem solving untuk deadlock", "kognitif", "problem solving en"),
    ("solve equation 2x + 5 = 15", "kognitif", "solve en"),
    ("how does transformer attention work?", "kognitif", "how does en"),
    ("explain why recursion is O(n)", "kognitif", "explain why en"),
    ("bukti bahwa P != NP", "kognitif", "bukti id"),
    ("step by step untuk deploy", "kognitif", "step by step en"),
    ("langkah demi langkah debugging", "kognitif", "langkah id"),
    ("deduction dari error log", "kognitif", "deduction en"),
    ("infer intent dari user behavior", "kognitif", "infer en"),
    ("conclude dari data analysis", "kognitif", "conclude en"),
    ("hypothesis untuk churn rate", "kognitif", "hypothesis en"),
    ("theory di balik distributed systems", "kognitif", "theory en"),

    # === EDGE CASES (13 cases) ===
    ("buatkan ide kode untuk fitur baru", "coding", "mixed: create + code + idea"),
    ("analisis error dan berikan ide fix", "coding", "mixed: analysis + code + idea"),
    ("bandingkan performa 2 algoritma", "sintesis", "mixed: compare + algorithm"),
    ("evaluasi code review kemarin", "autonomous", "mixed: eval + code"),
    ("refleksi dari design decision", "autonomous", "mixed: reflection + design"),
    ("apa itu machine learning?", "kognitif", "question without clear mode"),
    ("hello", "inovatif", "greeting → open-ended"),
    ("thanks", "inovatif", "thanks → open-ended"),
    ("oke", "inovatif", "ack → open-ended"),
    ("mode coding", "coding", "explicit short"),
    ("pake mode kognitif", "kognitif", "explicit id"),
    ("think deeply about this", "kognitif", "explicit en"),
    ("bukan evaluasi, tapi debug", "coding", "negation + valid keyword"),
]

# Related mode families (for partial credit)
MODE_FAMILIES = {
    "coding": ["coding", "kognitif"],  # coding involves analysis
    "inovatif": ["inovatif", "kognitif"],  # innovation involves thinking
    "sintesis": ["sintesis", "kognitif"],  # synthesis involves analysis
    "autonomous": ["autonomous", "kognitif"],  # reflection involves analysis
    "kognitif": ["kognitif", "coding", "sintesis", "autonomous", "inovatif"],  # cognitive is broad
}


def score_detection(detected: str, expected: str) -> tuple[float, str]:
    """Score a single detection. Returns (score, reason)."""
    if detected == expected:
        return 1.0, "exact_match"
    if detected in MODE_FAMILIES.get(expected, []):
        return 0.5, "related_match"
    return 0.0, "wrong"


def run_benchmark() -> BenchmarkResult:
    """Run the full benchmark."""
    result = BenchmarkResult()
    start = time.time()
    
    for user_input, expected, description in TEST_CASES:
        detected, confidence = ModeSelector.select(user_input)
        score, reason = score_detection(detected, expected)
        
        result.total += 1
        if score == 1.0:
            result.correct += 1
        elif score == 0.5:
            result.partial += 1
        else:
            result.wrong += 1
            result.failures.append({
                "input": user_input,
                "expected": expected,
                "detected": detected,
                "confidence": confidence,
                "description": description,
            })
        
        # Track by expected mode
        if expected not in result.by_mode:
            result.by_mode[expected] = {
                "total": 0, "correct": 0, "partial": 0, "wrong": 0,
                "accuracy": 0.0,
            }
        result.by_mode[expected]["total"] += 1
        if score == 1.0:
            result.by_mode[expected]["correct"] += 1
        elif score == 0.5:
            result.by_mode[expected]["partial"] += 1
        else:
            result.by_mode[expected]["wrong"] += 1
    
    # Calculate per-mode accuracy
    for mode, stats in result.by_mode.items():
        stats["accuracy"] = round(
            (stats["correct"] + stats["partial"] * 0.5) / stats["total"], 3
        )
    
    result.elapsed_ms = (time.time() - start) * 1000
    result.accuracy = round(
        (result.correct + result.partial * 0.5) / result.total, 3
    ) if result.total else 0.0
    
    return result


def print_report(result: BenchmarkResult):
    """Print human-readable report."""
    print("=" * 60)
    print("THINKING MODE BENCHMARK REPORT")
    print("=" * 60)
    print(f"Total cases: {result.total}")
    print(f"Correct: {result.correct} ({result.correct/result.total*100:.1f}%)")
    print(f"Partial: {result.partial} ({result.partial/result.total*100:.1f}%)")
    print(f"Wrong: {result.wrong} ({result.wrong/result.total*100:.1f}%)")
    print(f"Weighted accuracy: {result.accuracy*100:.1f}%")
    print(f"Elapsed: {result.elapsed_ms:.1f}ms")
    print()
    print("Per-mode accuracy:")
    for mode, stats in sorted(result.by_mode.items()):
        bar = "#" * int(stats["accuracy"] * 20)
        print(f"  {mode:12s}: {stats['accuracy']*100:5.1f}% {bar} ({stats['correct']}/{stats['total']})")
    
    if result.failures:
        print()
        print(f"Failures ({len(result.failures)}):")
        for f in result.failures:
            print(f"  [{f['expected']}] -> detected '{f['detected']}' (conf={f['confidence']})")
            print(f"    Input: {f['input'][:60]}...")
            print(f"    Desc: {f['description']}")
    
    print("=" * 60)
    
    if result.accuracy >= 0.85:
        print("PASS: Accuracy above 85% threshold")
    elif result.accuracy >= 0.70:
        print("WARNING: Accuracy below 85%, needs iteration")
    else:
        print("FAIL: Accuracy below 70%, significant issues")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="eval/mode_benchmark_results.json")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    
    result = run_benchmark()
    
    if not args.quiet:
        print_report(result)
    
    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total": result.total,
            "correct": result.correct,
            "partial": result.partial,
            "wrong": result.wrong,
            "accuracy": result.accuracy,
            "elapsed_ms": result.elapsed_ms,
            "by_mode": result.by_mode,
            "failures": result.failures,
        }, f, indent=2, ensure_ascii=False)
    
    if not args.quiet:
        print(f"\nResults saved to {output_path}")
    
    return 0 if result.accuracy >= 0.70 else 1


if __name__ == "__main__":
    sys.exit(main())
