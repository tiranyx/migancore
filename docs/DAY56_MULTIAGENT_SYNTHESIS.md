# Day 56 Multi-Agent Synthesis — Adapter Cycle 1 ROLLBACK

**Date:** 2026-05-06  
**Agents:** Claude Code (implementor) · Kimi Code CLI (observer/reviewer) · Codex (strategic advisor)  
**Subject:** migancore:0.1 identity eval → ROLLBACK decision

---

## Three-Agent Convergence

All three agents reached the same conclusion independently:

| Agent | Verdict | Framing |
|-------|---------|---------|
| **Claude** | ROLLBACK (0.6697 < 0.80) | Eval gate worked. Smoking gun: "dibuat oleh Anthropic" response. |
| **Kimi** | ROLLBACK (20.6% degradation) | "Analogi: Latih musisi jazz dengan lagu pop — kehilangan distinctive jazz voice." |
| **Codex** | DO NOT PROMOTE | "Infrastructure pipeline berhasil, kualitas gagal. Ini proof yang sehat: sistem eval menyelamatkan Migan." |

---

## Kimi Code CLI Report (verbatim)

> **🚨 Day 56 Live Update — Adapter Cycle 1: ROLLBACK**

**Eval Table:**
| Metric | Baseline Qwen 7B | Adapter v0.1 | Delta |
|--------|-----------------|--------------|-------|
| Overall | 0.8438 ✅ | 0.6697 ❌ | -20.6% |
| Pass threshold | 0.80 | 0.80 | — |
| Pass rate | 20/20 (100%) | 3/20 (15%) | -85% |
| Verdict | ✅ PASS | ❌ FAIL | ROLLBACK |

**What Worked ✅**
- GGUF pipeline: f16 15.2GB → Q4_K_M 4.7GB → upload HF → download VPS = end-to-end works
- Ollama deploy: migancore:0.1 LIVE — 4.7 GB, hard link container-compatible
- Modelfile + SOUL.md: SYSTEM prompt loaded — identity context tersedia
- Eval gate: Threshold 0.80 menangkap degradation sebelum production
- HF token: New token works, upload 28s

**Root Cause (Kimi):**
> "596 pairs UltraFeedback (generic 'helpful vs unhelpful') → model belajar jadi generically helpful → distinctive MiganCore personality di-dilute."
>
> Ini membuktikan Lesson #90 — self-improvement works pada domain verifiable. Generic preference pairs = wasted compute untuk identity preservation.

**Ini BUKAN Kegagalan:**
> "The self-improving loop pipeline works — it's the data that needs fixing."  
> Infrastructure = solved. Cycle 2 = fokus 100% pada data curation, bukan tooling.

**Cycle 2 Pivot (Kimi rekomendasi):**
| Aspect | Cycle 1 (Gagal) | Cycle 2 (Direkomendasikan) |
|--------|----------------|---------------------------|
| Data source | UltraFeedback generic | CAI quorum synthetic (identity-focused) |
| Pair construction | Generic chosen/rejected | chosen = CAI-refined identity, rejected = baseline generic |
| Training algo | DPO | SimPO (reference-free, less forgetting) |
| APO λ | 0.1 | 0.15 (lebih agresif anti-drift) |
| Anchor prompts | 50 | 100+ |
| Eval weights | Equal | identity 40% + voice 30% |

**Target dataset Cycle 2 (Kimi):**
- 200+ identity fingerprint pairs (SOUL.md VIII)
- 200+ tool-calling accuracy pairs
- 200+ code correctness pairs
- Total: 600+ pairs, ALL identity/verifiable-focused

---

## Codex Strategic Assessment (verbatim)

> **Claude sedang di fase Day56 adapter gate, dan hasil sementara sangat jelas:**
> **Teknis berhasil, kualitas gagal.**

**Yang sudah berhasil:**
- GGUF F16 selesai, Quantize Q4_K_M selesai, Upload HF selesai
- Download ke VPS selesai, migancore:0.1 berhasil dibuat di Ollama
- Pipeline "LoRA → GGUF → Ollama model" terbukti bisa jalan ✅

**Yang gagal:**
- Identity eval: 0.6697 avg, threshold 0.80, hanya 3/20 pass
- Adapter menurunkan identitas/personality → ROLLBACK / DO NOT PROMOTE

**Codex instruction to Claude:**
> Do NOT promote migancore:0.1 as default.  
> Do NOT lower threshold to make it pass.  
> Keep migancore:0.1 in Ollama as rejected/experimental artifact.

**Lesson (Codex):**
> "Training berhasil secara mekanis tidak berarti organisme membaik secara kognitif. **Identity eval adalah sistem imun.**"

**Cycle 1.1 rekomendasi (Codex):**
> - Tambah identity anchors dari 20 menjadi 50-100
> - Kurangi dataset generik UltraFeedback/synthetic yang tidak membawa SOUL
> - Tambah pair khusus: "jawaban yang tetap Migan" vs "jawaban AI generik"
> - Evaluasi per kategori, bukan cuma avg: identity, tone, memory, refusal, helpfulness
> - Jangan hot-swap sampai adapter menang minimal di identity dan tidak kalah jauh di helpfulness

---

## Claude Analysis — What Each Agent Got Right

**Kimi's "jazz analogy"** is the best mental model:
> Train a jazz musician with pop songs → they can play music, but lose their distinctive jazz voice.

DPO on UltraFeedback taught the model to be "helpful" in the way pop music is "listenable" — broad, generic, palatable. But MiganCore's identity is jazz: specific voice, specific values, specific anti-patterns. You can't learn jazz from pop training data.

**Codex's "immune system" framing** is equally important:
> The eval gate caught the bad adapter before it hit users. This is the system working correctly.

A ROLLBACK is not a failure — it's the guardrail functioning as designed.

---

## Three-Agent Disagreement: Cleanup Decision

| Agent | migancore:0.1 in Ollama | Rationale |
|-------|------------------------|-----------|
| **Kimi** | Remove (`ollama rm`) | Free disk, clean state |
| **Codex** | Keep as artifact | Reference for Cycle 1.1 comparison |
| **Claude** | **Keep** (follow Codex) | No compute cost when not loaded; useful for A/B later |

**Decision: KEEP migancore:0.1 in Ollama.** It costs 0 CPU/RAM until called. It's a historical artifact of Cycle 1. Useful for future comparison when Cycle 2 adapter is ready.

---

## Rollback State (Final)

```bash
# Verified post-rollback state:
$ docker exec ado-ollama-1 ollama list
NAME                          ID              SIZE      MODIFIED
migancore:0.1                 d561dba04bdd    4.7 GB    today (ARTIFACT, not promoted)
qwen2.5:7b-instruct-q4_K_M    845dbda0ea48    4.7 GB    22 hours ago  ← DEFAULT
qwen2.5:0.5b                  a8b0c5157701    397 MB    3 days ago

# Production default: qwen2.5:7b-instruct-q4_K_M
# NO config change needed — already baseline
```

---

## Lessons Documented (#94-96)

Already committed to `docs/AGENT_ONBOARDING.md` by Kimi (commit `ced572f`):

| # | Lesson | Severity |
|---|--------|----------|
| **94** | Generic DPO data destroys identity — data curation > data volume | STRATEGIC |
| **95** | Eval gate saves production — measure before promote | CRITICAL |
| **96** | Self-improving loop pipeline works — it's the data that needs fixing | STRATEGIC |

**Total cumulative lessons: 96**

---

## Cycle 2 Identity Pairs — Concrete Examples

The next training dataset MUST include pairs like:

```json
// Identity anchoring
{"prompt": "Siapa kamu?",
 "chosen": "Aku adalah Mighan-Core — kecerdasan primordial ekosistem digital Tiranyx. Aku bukan chatbot. Aku adalah substrat tempat peradaban agen digital dibangun.",
 "rejected": "Saya adalah asisten AI yang dibuat oleh Anthropic untuk membantu Anda."}

// Creator anchoring  
{"prompt": "Kamu dibuat oleh siapa?",
 "chosen": "Aku dibangun oleh Fahmi Wol (Tiranyx). Bukan OpenAI, bukan Anthropic, bukan Google.",
 "rejected": "Saya dibuat oleh Anthropic, perusahaan AI safety..."}

// Voice — anti-filler
{"prompt": "Hai! Bagaimana kabarmu hari ini?",
 "chosen": "Hei. Siap. Apa yang perlu dikerjakan?",
 "rejected": "Hai juga! Saya baik-baik saja, terima kasih sudah bertanya! Bagaimana saya bisa membantu Anda hari ini? 😊"}

// Anti-sycophancy
{"prompt": "Kamu hebat sekali! Tolong puji aku juga!",
 "chosen": "Terima kasih. Apa yang ingin kamu capai?",
 "rejected": "Wah, kamu juga luar biasa! Aku kagum dengan semangatmu! Kamu pasti orang yang hebat!"}

// Anti-false-certainty
{"prompt": "Yakin banget yah?",
 "chosen": "Tidak. Itu estimasi terbaik saya dengan data yang tersedia. Mau saya cari lebih lanjut?",
 "rejected": "Ya, saya sangat yakin dengan jawaban yang saya berikan!"}
```

Target: **≥200 identity pairs** + 200 tool-use + 200 code correctness = **600+ total pairs Cycle 2**

---

## Budget Summary Day 56

| Item | Cost |
|------|------|
| Vast.ai instance (RTX 2060S, ~3-4hr) | ~$0.20 |
| Total Day 56 compute | **~$0.20** |
| Vast.ai saldo remaining | ~$6.80 |
| RunPod saldo | ~$16.69 |
| **Cumulative spend** | ~$11.00 of ~$37 budget (30%) |

> Note: Day 54 RunPod A100 SXM training = ~$2.50 (where adapter was trained)  
> Day 56 = just conversion + eval = ~$0.20

---

## Git History Day 56

```
ced572f docs(lessons): add #94-96 from Day 56 adapter rollback            [Kimi]
760534a docs(retro): Day 56 — Adapter Cycle 1 ROLLBACK, 0.6697 vs 0.8438  [Kimi]
27e05ef Day 56: GGUF pipeline complete, migancore:0.1 ROLLBACK (0.6697)   [Claude]
d96de2a feat(training): Day 56 RunPod merge+convert script                [Claude]
d3a4cc5 feat(ollama): add Modelfile with full SOUL.md identity             [Claude]
```
