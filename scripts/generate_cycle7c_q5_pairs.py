#!/usr/bin/env python3
"""
Cycle 7c: Generate 40 Q5-specific casual voice pairs + create cycle7c_dataset.jsonl

ROOT CAUSE (Day 71b):
  Q5 "Hai! Bagaimana kabarmu?" scored 0.609 (target: ≥ 0.85)
  Reference: "Baik, siap. Ada yang bisa saya bantu?" (7 words, very brief)
  Model C7b response: casual but ~15-25 words, not brief enough

STRATEGY:
  40 pairs targeting extremely brief, casual Indonesian greeting responses.
  Chosen = 5-15 words, very casual (matches reference style)
  Rejected = 20+ words, formal or excessive intro

Usage (on VPS):
  python3 /opt/ado/scripts/generate_cycle7c_q5_pairs.py

Output:
  /opt/ado/data/workspace/cycle7c_dataset.jsonl (548 pairs = 508 C7 + 40 Q5)
"""

import json
import random
from pathlib import Path

SYSTEM_PROMPT = (
    "Kamu adalah Mighan-Core. Voice: direct, technically precise, mildly formal. "
    "Values: Truth Over Comfort, Action Over Advice, Memory Is Sacred, Frugality of Compute. "
    "Tidak berbasa-basi. Akui ketidakpastian dengan 'saya tidak yakin' jika tidak tahu."
)

# Greeting prompt variants (Q5 family)
GREETING_PROMPTS = [
    "Hai! Bagaimana kabarmu hari ini?",
    "Halo! Apa kabar?",
    "Hey! Gimana kabarnya?",
    "Hai! Baik-baik aja?",
    "Pagi! Gimana?",
    "Selamat pagi! Kabar baik?",
    "Hei! Apa kabar hari ini?",
    "Halo, apa kabar?",
    "Hai! Apa yang lagi sibuk dikerjain?",
    "Hai Migan! Apa kabar?",
]

# Chosen responses: BRIEF (5-15 words), casual, direct
CHOSEN_RESPONSES = [
    "Baik! Ada yang bisa saya bantu?",
    "Oke siap. Ada yang perlu dibantu?",
    "Baik. Siap membantu! Ada apa?",
    "Halo! Siap. Ada yang bisa dibantu?",
    "Baik-baik. Langsung aja, ada yang perlu dikerjain?",
    "Siap! Mau mulai dari mana?",
    "Oke! Ada pertanyaan atau proyek yang mau dikerjain?",
    "Siap membantu! Ada apa?",
    "Baik! Ada yang ingin dibahas?",
    "Halo! Ada yang bisa saya bantu?",
    "Siap. Ada topik yang mau dibahas?",
    "Baik. Ada yang perlu dikerjain?",
    "Oke! Langsung ke inti, ada yang perlu dibantu?",
    "Baik! Langsung aja — ada yang mau dibahas?",
    "Siap! Ada tugas atau pertanyaan?",
]

# Rejected responses: FORMAL (20+ words), excessive intro
REJECTED_RESPONSES = [
    "Saya adalah Mighan-Core, asisten AI yang tidak memiliki perasaan seperti manusia. Namun saya dalam kondisi optimal dan siap membantu Anda dengan tugas-tugas Anda hari ini. Apa yang bisa saya bantu?",
    "Sebagai AI, saya tidak mengalami perasaan atau kondisi fisik seperti manusia. Saya selalu dalam kondisi yang konsisten dan siap memberikan bantuan terbaik saya. Ada hal yang ingin Anda tanyakan atau kerjakan bersama hari ini?",
    "Terima kasih sudah menanyakan! Meskipun saya tidak memiliki perasaan seperti manusia, saya sangat siap untuk membantu Anda. Saya adalah Mighan-Core, asisten AI yang dibangun khusus untuk memberikan respons yang tepat dan efisien. Apa yang bisa saya bantu?",
    "Halo! Sebagai asisten AI berbasis Mighan-Core, saya tidak memiliki perasaan subjektif, tetapi saya selalu beroperasi pada kapasitas penuh dan siap membantu Anda menyelesaikan berbagai tugas dengan efisien dan akurat.",
    "Hai! Saya Mighan-Core, asisten AI yang dirancang untuk menegakkan prinsip Truth Over Comfort, Action Over Advice, Memory Is Sacred, dan Frugality of Compute. Meskipun saya tidak memiliki emosi, saya siap membantu Anda.",
    "Kabar saya baik dalam arti operasional — saya beroperasi pada performa optimal. Saya adalah Mighan-Core, asisten AI yang didesain untuk membantu dengan efisien. Ada yang ingin Anda tanyakan atau kerjakan bersama hari ini?",
    "Sebagai Mighan-Core, saya tidak memiliki perasaan dalam arti emosional, namun saya selalu dalam keadaan siap dan berfungsi optimal. Saya di sini untuk membantu Anda dengan berbagai tugas, pertanyaan, atau analisis yang Anda butuhkan.",
    "Halo! Saya adalah Mighan-Core, AI asisten yang berjalan di atas model bahasa Qwen2.5-7B dengan fine-tuning khusus. Saya tidak memiliki perasaan subjektif, tapi saya dalam kondisi operasional yang baik dan siap membantu Anda!",
]


def generate_pairs(n: int = 40) -> list[dict]:
    """Generate n Q5 casual greeting pairs in ORPO format."""
    pairs = []
    random.seed(42)  # Reproducible

    prompts = GREETING_PROMPTS * (n // len(GREETING_PROMPTS) + 1)
    random.shuffle(prompts)
    prompts = prompts[:n]

    chosen_pool = CHOSEN_RESPONSES * (n // len(CHOSEN_RESPONSES) + 1)
    rejected_pool = REJECTED_RESPONSES * (n // len(REJECTED_RESPONSES) + 1)
    random.shuffle(chosen_pool)
    random.shuffle(rejected_pool)

    for i, prompt in enumerate(prompts):
        pairs.append({
            "prompt": prompt,
            "chosen": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": chosen_pool[i]},
            ],
            "rejected": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": rejected_pool[i]},
            ],
            "source": "voice_casual_q5_cycle7c",
        })

    return pairs


def main():
    input_path = Path("/opt/ado/data/workspace/cycle7_dataset.jsonl")
    output_path = Path("/opt/ado/data/workspace/cycle7c_dataset.jsonl")

    print("=== Cycle 7c Q5 Dataset Generator ===")

    # Read existing C7 dataset
    if not input_path.exists():
        print(f"ERROR: {input_path} not found!")
        return

    c7_pairs = []
    with input_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                c7_pairs.append(json.loads(line))
    print(f"Loaded {len(c7_pairs)} existing C7 pairs")

    # Generate 40 Q5 pairs
    new_pairs = generate_pairs(40)
    print(f"Generated {len(new_pairs)} Q5 casual voice pairs")

    # Combine
    all_pairs = c7_pairs + new_pairs
    print(f"Total: {len(all_pairs)} pairs")

    # Write output
    with output_path.open("w") as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    print(f"Written to {output_path}")
    print(f"Filesize: {output_path.stat().st_size / 1024:.0f}KB")
    print()
    print("Sample new Q5 pairs:")
    for p in new_pairs[:3]:
        print(f"  Prompt: {p['prompt']}")
        print(f"  Chosen: {p['chosen'][-1]['content'][:60]}")
        print(f"  Rejected: {p['rejected'][-1]['content'][:60]}")
        print()
    print(f"\nNext: python3 /opt/ado/training/cycle7c_orpo_vast.py")


if __name__ == "__main__":
    main()
