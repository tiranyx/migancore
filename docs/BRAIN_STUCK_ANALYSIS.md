# ANALISIS MENDALAM: MENGAPA BRAIN STUCK? (Day 70)
**Status:** CRITICAL ANALYSIS — jangan di-sweep under rug  
**Date:** 2026-05-09 14:30 WIB  
**Owner:** Chief Engineer  
**Rule:** Setiap kegagalan harus jadi batu loncatan, bukan kuburan.

---

## I. FAKTA KEGAGALAN (5 Cycles, Day 56-70)

```
Cycle 2 (SimPO)  → PASS 0.8453 — tapi identity hancur, model jadi "Qwen"
Cycle 3 (ORPO)   → FAIL — rewards NEGATIVE, voice regression
Cycle 4 (ORPO)   → FAIL — brevity pairs creative -0.193, evo-aware -0.199
Cycle 5 (ORPO)   → FAIL — tool_use 0.7439, creative 0.7278, evo-aware 0.7502
Cycle 6 (ORPO)   → FAIL — same failure pattern
Cycle 7a-7c (ORPO) → FAIL — signal density 7.3%, too low
Cycle 7d (SFT)   → DRAFT — belum di-launch
```

**Fakta pahit:** 14 hari, ~$30-50 spend, ZERO improvement. Brain semakin fragile.

---

## II. ROOT CAUSE ANALYSIS (5 Whys)

### Why #1: Kenapa identity tidak terbentuk?
**Jawaban:** Model tanpa SOUL.md tetap bilang "Saya Qwen", bukan "Saya Mighan-Core".

### Why #2: Kenapa LoRA tidak override base identity?
**Jawaban:** Rank 16 terlalu kecil untuk override identity weights dari base model Qwen2.5-7B yang sudah terlatih kuat. LoRA hanya 0.1-1% dari total parameter.

### Why #3: Kenapa rank tidak dinaikkan dari awal?
**Jawaban:** Default hyperparameter r=16, α=16 dari tutorial. Tidak ada eksperimen untuk identity-specific task.

### Why #4: Kenapa tidak pakai SFT dari awal untuk identity?
**Jawaban:** Terobsesi dengan preference optimization (SimPO/ORPO) karena "trend 2026". Salah kaprah: preference = untuk alignment, bukan untuk identity injection.

### Why #5: Kenapa terobsesi dengan trend?
**Jawaban:** Riset `migancore new riset.md` menyebut SimPO/ORPO sebagai "consensus 2026". Tapi consensus itu untuk **general chat quality**, bukan untuk **identity anchor**.

**Root Cause Ultimate:**
> **Kita memakai hammer (ORPO) untuk semua masalah, padahal identity adalah paku yang butuh screwdriver (SFT).**

---

## III. 7 KESALAHAN FUNDAMENTAL

### Kesalahan 1: ORPO untuk Voice/Identity (Wrong Tool)
- **ORPO** = Odds Ratio Preference Optimization. Butuh paired data (chosen vs rejected).
- **Identity** = pattern recognition ("Saya Mighan-Core"). Bukan preference.
- **SFT** = Supervised Fine-Tuning. Teach model to imitate target output exactly.
- **Dampak:** 5 cycles, rewards/margins NEGATIF. Identitas semakin fragile.

### Kesalahan 2: Mixing Semua Kategori dalam Satu Cycle
- Cycle 6: identity + tool + code + creative + voice + evo-aware = ~1060 pairs
- Signal density per kategori: 7-15% (terlalu rendah)
- **Dampak:** Model belajar sedikit-sedikit dari semua kategori, tidak mahir di satu pun. Regression di kategori lain.

### Kesalahan 3: 99% Synthetic Data
- Magpie/self-play/generated pairs = 99%
- Real user feedback = 16 pairs
- Teacher distillation = 10 pairs
- **Dampak:** Circular degradation. Model belajar dari output model sendiri → echo chamber.

### Kesalahan 4: No Loss Masking
- Framework tidak verify bahwa hanya assistant tokens yang contribute ke loss
- Prompt + response semua di-train → model belajar predict pertanyaan sendiri
- **Dampak:** Overfitting ke prompt patterns, bukan ke response quality.

### Kesalahan 5: Baseline-Gate Coupling
- Eval gate membandingkan dengan baseline model sebelumnya
- Baseline sudah jelek → model baru yang lebih baik tetap "fail"
- **Dampak:** False-fail, waktu terbuang, morale drop.

### Kesalahan 6: No Chat Template Verification
- Tidak verify tokenizer's `apply_chat_template` sebelum training
- Qwen2.5 pakai chat template tertentu, tapi dataset mungkin format berbeda
- **Dampak:** Model train pada tokens yang salah → broken adapter.

### Kesalahan 7: No Catastrophic Forgetting Check
- Tidak monitor MMLU delta atau general capability drop
- Fine-tune terlalu agresif → general knowledge hancur
- **Dampak:** Model bisa jawab "Saya Mighan-Core" tapi tidak bisa coding/reasoning.

---

## IV. PERBANDINGAN DENGAN BEST PRACTICES 2026

| Aspek | MiganCore (Day 70) | Best Practice 2026 | Gap |
|---|---|---|---|
| Loss function | ORPO-only (5 cycles) | SFT untuk pattern, DPO/KTO untuk preference | 🔴 Critical |
| Dataset quality | 99% synthetic, 1% real | 500 clean > 5,000 noisy | 🔴 Critical |
| Signal density | 7-15% per kategori | ≥ 25% per category | 🔴 Critical |
| One category per cycle | Mix 6 kategori | ONE category per cycle | 🔴 Critical |
| Loss masking | Not verified | Only assistant tokens | 🟡 High |
| Chat template | Not verified | Verify before training | 🟡 High |
| MMLU delta | Not checked | Drop < 2-3 points | 🟡 High |
| Rank selection | r=16 default | r=8 style, r=32 domain, r=64 knowledge | 🟡 High |
| Identity test | Manual, ad-hoc | Automated, cosine sim > 0.85 | 🟡 High |
| Data curation | None | MTLD + dedup + diversity filter | 🟡 High |

---

## V. SOLUSI: BRAIN V2 ARCHITECTURE

### Prinsip Baru (Anti-Stuck)
1. **One Problem = One Tool** — SFT untuk identity, DPO untuk preference, KTO untuk user signals
2. **One Category = One Cycle** — tidak mixing. Identity cycle → Voice cycle → Tool cycle → dst.
3. **Data Quality > Quantity** — 200 clean pairs > 1000 noisy pairs
4. **Signal Density ≥ 25%** — kalau tidak cukup, skip kategori itu
5. **Identity First, Everything Else Later** — tanpa identity, tidak ada white-label, tidak ada clone
6. **Automated Eval Gate** — identity test MANDATORY sebelum deploy
7. **Catastrophic Forgetting Guard** — MMLU delta check setiap cycle

### Arsitektur Training Baru

```
┌─────────────────────────────────────────────────────────────┐
│                    MIGANCORE BRAIN V2                        │
│                                                              │
│  PHASE 1: IDENTITY LOCK (M1)                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SFT 200 identity pairs (100% signal density)        │   │
│  │ Rank 32, Alpha 64, 5 epochs, LR 1e-4               │   │
│  │ Mask prompt = true (hanya train assistant tokens)  │   │
│  │ Target: tanpa SOUL.md, cosine sim > 0.85           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│  PHASE 2: VOICE & TONE (M2)                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SFT 200 voice pairs (direct, no filler, structured) │   │
│  │ Rank 16, 3 epochs                                   │   │
│  │ Target: match voice reference > 0.80                │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│  PHASE 3: TOOL USE (M3)                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SFT 100 tool patterns + DPO 200 tool preferences    │   │
│  │ Target: accuracy > 80%                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│  PHASE 4: GENERAL CHAT (M4)                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SimPO 500 pairs (real data ≥ 50%)                   │   │
│  │ Target: judge_score improvement vs baseline         │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│  PHASE 5: SELF-EVOLVING (M5+)                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ KTO dari user thumbs (continuous)                   │   │
│  │ Self-growth CAI (20+ pairs/hari)                   │   │
│  │ Teacher distillation (50+ pairs/hari, $5/day cap)  │   │
│  │ Auto-cycle: Feedback → Pair → Train → Deploy → Eval│   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## VI. PERBEDAAN DENGAN AI AGENT UMUM

| Fitur | AI Agent Umum (GPT+Tools) | MiganCore V1 (Day 70) | MiganCore V2 (Target) |
|---|---|---|---|
| Identity | Generic "AI assistant" | Fragile (prompt-dependent) | **Baked into weights** |
| Self-learning | None | Manual, broken | **Auto-loop, 4 pathways** |
| Clone/Spawn | GPTs/Claude Projects | Skeleton only | **1-click, DNA inheritance** |
| Memory | Stateless/session | Multi-tier, not integrated | **LLM OS (Letta-style)** |
| Training | API consumer only | ORPO-only, 5× fail | **Multi-loss, category-specific** |
| Data quality | N/A (pre-trained) | 99% synthetic | **≥ 50% real, curated** |
| Eval gate | N/A | Manual, coupled | **Automated, absolute** |
| Causal reasoning | None | Not built | **DoWhy + Active Inference** |
| Agent commerce | N/A | Not built | **x402 + ERC-8004** |

**Cara MiganCore V2 "menang":**
Bukan dengan IQ model lebih tinggi dari GPT-5. Tapi dengan:
1. **Vertical integration** — hidup 24/7 dengan memori pribadi user
2. **Clone economy** — melahirkan "anak" dengan personality unik
3. **Indonesia-first** — nuansa lokal, on-premise, murah
4. **Self-evolving** — tidak perlu manusia di setiap junction

---

## VII. MILESTONE V2 (Revised)

| Milestone | Target | Criteria | Risiko Jika Gagal |
|---|---|---|---|
| **M1: Identity Lock** | Day 77 (1 minggu) | SFT 200 pairs, cosine > 0.85, no SOUL.md | Pivot ke full fine-tune atau accept prompt-only |
| **M2: Voice Lock** | Day 84 (2 minggu) | SFT 200 pairs, voice match > 0.80 | Reduce rank, increase epochs |
| **M3: Tool Mastery** | Day 91 (3 minggu) | Accuracy > 80%, no regression | Add more SFT patterns, fix tool schema |
| **M4: General Quality** | Day 105 (5 minggu) | SimPO 500 pairs, real data ≥ 50% | Increase teacher budget, recruit beta users |
| **M5: Auto-Loop** | Day 119 (7 minggu) | 1 cycle auto-complete tanpa manusia | Manual trigger sementara |
| **M6: First Clone** | Day 133 (9 minggu) | Clone < 10 menit, child live | Delay clone, focus on single instance |
| **M7: Revenue** | Day 147 (11 minggu) | First client, invoice paid | Offer free pilot, bootstrap dari B2B |

---

*Dokumen ini wajib dibaca sebelum setiap training cycle.*
