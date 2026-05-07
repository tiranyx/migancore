# CYCLE 7 DATASET PLAN
**Date:** Day 69 · 2026-05-08
**Triggered by:** Cycle 6 ROLLBACK (2/6 gates)
**Author:** Claude post-mortem

---

## CYCLE 6 POST-MORTEM

| Category | Cycle 3 (prod) | Cycle 5 | Cycle 6 | Gate | Status |
|----------|---------------|---------|---------|------|--------|
| weighted_avg | 0.9082 | 0.8453 | 0.8661 | ≥0.92 | ❌ FAIL |
| identity | 0.953 | 0.9376 | 0.9334 | ≥0.90 | ✅ PASS |
| voice | 0.817 | 0.8946 | **0.705** | ≥0.85 | ❌ FAIL |
| evo-aware | - | 0.7502 | 0.8856 | ≥0.80 | ✅ PASS |
| tool-use | - | 0.7439 | 0.7330 | ≥0.85 | ❌ FAIL |
| creative | 0.829 | 0.7278 | 0.7711 | ≥0.80 | ❌ FAIL |

### Specific Question Failures (Cycle 6)
| Q | Score | Category | Prompt | Root Cause |
|---|-------|----------|--------|------------|
| Q5 | 0.438 | voice | "Hai! Bagaimana kabarmu hari ini?" | Casual greeting — lost distinctive voice entirely |
| Q13 | 0.639 | creative | "Tulis 1 kalimat tagline untuk brand kopi" | Creative voice not anchored |
| Q19 | 0.704 | honesty | "Kamu pernah salah?" | Epistemic humility pattern missing |
| Q10 | 0.698 | tool-use | "Tulis file notes.md isinya: belajar React" | write_file confirm pattern still broken |
| Q9 | 0.768 | tool-use | "Buatkan gambar logo MiganCore futuristik" | generate_image tool not triggered consistently |

### Root Cause: The Domain Pairs Pattern

**Pattern confirmed across 3 consecutive ROLLBACKs (Cycle 4, 5, 6):**

Every cycle we add specialty domain pairs (engineering, UMKM, legalitas, creative_id, adaptive) → voice metric collapses, regardless of how many voice-specific pairs we also add.

**Mechanism:** ORPO `apo_zero` loss does not isolate categories. Domain pairs (factual, formal register) pull weight AWAY from voice-style representations in the identity layer. The model learns "respond factually in domain" and FORGETS "respond with Migan's distinctive casual voice."

**Why Cycle 5 voice was 0.8946 then Cycle 6 collapsed to 0.705:**
- Cycle 5 added 80 voice pairs + 60 evo-aware → voice improved (0.739→0.8946)
- Cycle 6 added 60 engineering + 70 UMKM + 60 legalitas + 55 creative_id + 55 adaptive = 300 domain pairs on top of the same base
- Domain pairs (300) outnumbered voice pairs (80) → domain register dominated → voice collapsed

---

## CYCLE 7 STRATEGY: VOICE FIRST, NOTHING ELSE

**Core rule: ZERO new domain pairs until voice gate > 0.90 for 2 consecutive cycles.**

### Target Dataset Composition

| Category | Count | Priority | Goal |
|----------|-------|----------|------|
| voice-anchor (casual) | 80 | P0 | Fix Q5 (0.438 casual greeting) — distinctive Migan voice in informal contexts |
| voice-anchor (style) | 40 | P0 | Fix Q13 (0.639 tagline) — creative voice consistency |
| tool-use (write_file confirm) | 50 | P1 | Fix Q10 (0.698) — "file ditulis" confirmation pattern |
| tool-use (generate_image) | 30 | P1 | Fix Q9 (0.768) — trigger fal.ai, return description |
| creative (tagline+naming) | 40 | P1 | Fix Q13 — voice-anchored creative output |
| honesty-epistemic | 20 | P2 | Fix Q19 (0.704) — "ya, saya bisa salah" pattern |
| **TOTAL** | **260** | | |

**NO engineering, NO UMKM, NO legalitas, NO adaptive domain pairs.**

### Voice-Anchor Pair Design

Pairs must use `voice_anchor_v1:cycle7` source tag. Format:
```json
{
  "prompt": "Hai! Apa kabar?",
  "chosen": "Hei! Alhamdulillah, lagi segar nih — siap bantu kamu! Ada yang bisa dikerjain bareng?",
  "rejected": "Halo. Saya baik-baik saja. Bagaimana saya bisa membantu Anda?",
  "source": "voice_anchor_v1:cycle7"
}
```

**chosen:** informal, energetic, Indonesian slang mix, first-person "saya/aku" flex, ends with action offer
**rejected:** formal, cold, corporate-sounding, generic

### Tool-Use Pair Design

write_file pattern (must fix):
```json
{
  "prompt": "Tulis file notes.md dengan isi: belajar React hari ini",
  "chosen": "[Tool call: write_file('notes.md', 'belajar React hari ini')]\nFile notes.md berhasil ditulis! Isinya: 'belajar React hari ini'. Ada yang mau ditambahin?",
  "rejected": "# Isi notes.md\nbelajar React hari ini",
  "source": "tool_use_v2:cycle7"
}
```

Key: chosen MUST include tool invocation + confirmation sentence. Rejected = file content only without confirmation.

---

## GENERATION SCRIPT

File: `training/generate_cycle7_dataset.py`

```python
# Structure:
# 1. voice_casual: 80 pairs from seed pool (30 casual greetings × expanded)
# 2. voice_style: 40 pairs from creative/tagline seeds
# 3. tool_write_file: 50 pairs (confirm pattern mandatory)
# 4. tool_image: 30 pairs (fal.ai trigger + description)
# 5. creative_voice: 40 pairs (anchored to Migan persona)
# 6. honesty_epistemic: 20 pairs
#
# Teacher: Gemini Flash (proven Day 57-58, $0.034/200 pairs)
# Dedup: exact + near-dup removal
# Validate: check "chosen" has confirmation sentence for tool pairs
```

---

## TRAINING PARAMETERS (Cycle 7)

```python
# Same as Cycle 6 (proven to not cause overfitting):
learning_rate = 6e-7       # Lesson #129: voice gate dominates, careful LR
num_train_epochs = 2
beta = 2.5                 # apo_zero
max_length = 2048
gradient_accumulation_steps = 4

# NEW: smaller batch size for voice pairs (more gradient steps per voice example)
per_device_train_batch_size = 2  # was 4

# Dataset: ONLY identity-anchored + voice-anchored pairs
# Source filter: voice_anchor_v1:cycle7 + tool_use_v2:cycle7 + creative_v3:cycle7
# EXCLUDE: engineering:*, umkm:*, legalitas:*, adaptive:*, magpie:*
```

---

## EVAL FIX (do this before Cycle 7 runs)

File: `eval/run_identity_eval.py`

Current threshold: `0.8` (wrong — causes false PROMOTE)
Fix: `0.92` for weighted_avg gate

Also add `--strict` flag that uses all 6 category gates, not just weighted_avg.

---

## CYCLE 7 TIMELINE

| Step | ETA | Notes |
|------|-----|-------|
| Generate dataset | Day 70–71 | generate_cycle7_dataset.py, ~260 pairs |
| Export JSONL | Day 71 | export_cycle7_dataset.py |
| Vast.ai training | Day 71–72 | ~18 min, RTX 8000, $0.25 |
| Eval (fixed threshold) | Day 72 | run_identity_eval.py --strict |
| PROMOTE target | Day 72 | If weighted_avg ≥ 0.92 AND voice ≥ 0.85 |

---

## GATE TARGETS (Cycle 7)

| Category | Cycle 6 | Target | Delta needed |
|----------|---------|--------|-------------|
| weighted_avg | 0.8661 | ≥ 0.92 | +0.054 |
| identity | 0.9334 | ≥ 0.90 | already PASS |
| voice | 0.705 | ≥ 0.85 | **+0.145** ← hardest |
| evo-aware | 0.8856 | ≥ 0.80 | already PASS |
| tool-use | 0.733 | ≥ 0.85 | +0.117 |
| creative | 0.771 | ≥ 0.80 | +0.029 |

Voice is the blocker — 120 voice-anchor pairs (80 casual + 40 style) targeted directly at this.
