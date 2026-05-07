#!/usr/bin/env python3
"""
MiganCore Cycle 7d SFT Training — Vast.ai Orchestration (DRAFT, NOT LAUNCHED)
==============================================================================
Day 71c+ | 2026-05-08 | Cycle 7c ROLLBACK → SFT-first pivot

ROOT CAUSE Cycle 7c ROLLBACK (per Lessons #174-175):
  1. 40 Q5 pairs / 548 = 7.3% signal density TOO LOW for ORPO targeted change
  2. ORPO rewards/margins NEGATIVE throughout = wrong tool for length-style targets
  3. Brevity pairs caused creative -0.193 + evolution-aware -0.199 regressions

Cycle 7d STRATEGY (SFT-first, Option D from RECAP_71C):
  - SFT (Supervised Fine-Tuning) on 200 voice-only pairs (100% signal density)
  - Direct supervised loss = teaches model to imitate target output exactly
  - No preference learning (which proved counter-productive for length-style targets)
  - 5 prompt families × 40 pairs = 200 (no diversity dilution)
  - LR=5e-7 (lower than ORPO's 1.2e-6 to avoid catastrophic forgetting)
  - 5 epochs × 200 pairs ÷ batch 16 = ~63 gradient steps
  - Smaller LoRA r=8 (more focused adaptation) than ORPO's 16
  - Base: migancore:0.3 adapter (continue from production, not Qwen base)

NOTE: This file is DRAFT. Launch only after:
  1. Kimi+Codex review the SFT pivot strategy
  2. baseline reference is finalized (Day 71c lessons #170 #176)
  3. SFT trainer script (train_sft_standard.py) is written and tested
  4. Risk acceptance: migancore:0.3 stays as fallback if SFT regresses other categories

Dataset: /opt/ado/data/workspace/cycle7d_sft_dataset.jsonl (200 SFT pairs)
Algorithm: SFT (TRL SFTTrainer or HuggingFace Trainer)
Target: A40/RTX A6000 40+GB @ ~$0.30-0.60/hr | ~10-15 min
Output: Tiranyx/migancore-7b-soul-v0.7d
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timezone

# === Cycle 7d-specific config (DRAFT — review before launch) ===
VAST_KEY_PATH = "/opt/secrets/migancore/vastai_api_key"
HF_TOKEN_PATH = "/opt/secrets/migancore/hf_token"
DATASET_PATH  = "/opt/ado/data/workspace/cycle7d_sft_dataset.jsonl"  # 200 SFT pairs
TRAIN_SCRIPT  = "/opt/ado/training/train_sft_standard.py"            # TODO: write Day 72
OUTPUT_DIR    = "/opt/ado/cycle7d_output"
LOG_PATH      = "/tmp/cycle7d_training.log"

HF_REPO       = "Tiranyx/migancore-7b-soul-v0.7d"
BASE_MODEL    = "Qwen/Qwen2.5-7B-Instruct"
# OR continue from migancore:0.3 adapter:
# BASE_ADAPTER = "Tiranyx/migancore-7b-soul-v0.3"

MIN_GPU_RAM_MB    = 40_000
MAX_PRICE_HR      = 0.65
MIN_DISK_GB       = 65
MAX_BOOT_WAIT_SEC = 600
COST_CAP_USD      = 5.00

# SFT hyperparams (vs ORPO's higher LR)
SFT_ARGS = [
    "--dataset",       "/root/cycle7d_sft_dataset.jsonl",
    "--output-dir",    "/root/cycle7d_adapter",
    "--base-model",    BASE_MODEL,
    "--epochs",        "5",          # more epochs (smaller dataset, focused)
    "--learning-rate", "5e-7",       # lower LR to avoid catastrophic forgetting
    "--lora-r",        "8",          # smaller rank (focused adaptation)
    "--lora-alpha",    "16",
    "--batch-size",    "2",
    "--grad-accum",    "8",
    "--max-seq-length","2048",
    # SFT-specific:
    "--packing",       "false",      # no packing (preserve message boundaries)
    "--mask-prompt",   "true",       # only train on assistant tokens
]

# === HF roundtrip (Lesson #173) — push to HF before delete instance, no SCP ===
USE_HF_ROUNDTRIP = True  # Set False to fall back to SCP (not recommended after C7c)

# Stub: actual orchestration logic copied from cycle7c_orpo_vast.py once SFT trainer ready
def main():
    print("=" * 60)
    print("MIGANCORE CYCLE 7d — SFT Voice/Casual Focused")
    print("STATUS: DRAFT — DO NOT LAUNCH WITHOUT REVIEW")
    print()
    print("Required before launch:")
    print("  1. Write /opt/ado/training/train_sft_standard.py (SFT trainer)")
    print("  2. Kimi+Codex review SFT pivot strategy (RECAP_71C Option D)")
    print("  3. Finalize baseline reference (Lessons #170, #176)")
    print("  4. Risk acceptance: migancore:0.3 fallback ready")
    print("=" * 60)
    print()
    print(f"Dataset: {DATASET_PATH}")
    print(f"  - 200 SFT pairs, 100% voice/casual (5 families × 40)")
    print(f"  - Mean response 8.8 words (vs 7w ref Day 70, 17w ref Day 71c realistic)")
    print()
    print(f"Hyperparams:")
    print(f"  - LR={SFT_ARGS[SFT_ARGS.index('--learning-rate')+1]} (lower than ORPO 1.2e-6)")
    print(f"  - epochs={SFT_ARGS[SFT_ARGS.index('--epochs')+1]} (more passes, smaller data)")
    print(f"  - lora-r={SFT_ARGS[SFT_ARGS.index('--lora-r')+1]} (focused adaptation)")
    print()
    print(f"HF roundtrip: {USE_HF_ROUNDTRIP} (Lesson #173)")
    print(f"Estimated cost: $0.20-0.30")
    print()
    print("To launch (when ready): python3 /opt/ado/training/cycle7d_sft_vast.py --launch")

if __name__ == '__main__':
    if '--launch' in sys.argv:
        print("ERROR: --launch flag detected but trainer not ready.")
        print("Write train_sft_standard.py first, then remove this guard.")
        sys.exit(1)
    main()
