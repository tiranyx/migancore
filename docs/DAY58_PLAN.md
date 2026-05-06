# Day 58 Plan — Cycle 2 Dataset Completion (Tool-Use + Code Pairs)
**Date:** 2026-05-06
**Triggered by:** Codex GO Day58 Option A+C | Kimi APPROVED steps 1-4
**Claude = main implementor | Kimi = review | Codex = QA/read-only**

---

## 1. CONTEXT (state Day 58)

| Item | State |
|------|-------|
| API | v0.5.16 healthy |
| DPO pool | 1423 pairs (194 identity_anchor_v2 NEW) |
| Tool-use pairs | 0 dedicated (only 20 in identity_anchor_v2:tool_style — style only) |
| Code pairs | 0 dedicated |
| Git status | CLEAN (deleted test_vast.py + training/vastai_day56.sh) |
| Vast.ai saldo | ~$5.30 |
| RunPod saldo | ~$14.27 |
| Lessons | 98 cumulative |

**Cycle 2 Dataset Gap:**
- 194 identity_anchor_v2 ✅ (Day 57)
- 0 tool-use accuracy pairs ❌ (Day 58 target: 200)
- 0 code correctness pairs ❌ (Day 58 target: 200)
- Target for Cycle 2 training: 600 curated pairs (194 + 200 + 200 + 6 backfill)

---

## 2. RESEARCH SYNTHESIS (sources: arxiv 2025-2026, LocalLLaMA, HuggingFace, Unsloth docs)

### Finding #1 — Tool-Use Pair Format: Middle-Chain Wins
Source: Chain of Preference Optimization (NeurIPS 2024) + philschmid.de 2025
- Format A (just declaration): "Aku akan cari..." → weak signal, model learns to SAY but not DO
- Format B (declare + result + cite): `[tool call] → result → source` → **WINNER at <500 pairs**
- Format C (full plan → chain → reflect): plateau after 500 pairs; diminishing ROI at 200 pairs scale
- **Day 58 rule:** B = declare tool → show output → synthesize → clickable source
- **Soekarno benchmark** (Codex requirement): MUST include as canonical tool-use pair

### Finding #2 — Code Pairs: Bilingual Best
Source: IndoJavE models 2025, Unsloth docs, kyrylai.com
- Indonesian prose + English code > fully Indonesian (overfits to mixed tokens)
- chosen: type hints, docstring, direct voice, no filler
- rejected: "Tentu saja! 😊" intro + code-without-docstring + verbose padding
- Teaching signal: model learns Migan voice applies to CODE responses too

### Finding #3 — Rejected Sample Design Matters Less Than Chosen Quality
Source: "What Matters in Data for DPO?" NeurIPS 2025 (arxiv 2508.18312)
- Chosen quality dominates: rejected matters <20% as much
- But structural tiers help:
  - Tier 1 (40-50%): "I can't access internet" → STRONG signal against hallucination
  - Tier 2 (30-40%): Wrong synthesis after tool call → teaches result validation
  - Tier 3 (10-20%): Correct tool, verbose/padded response → style signal
- **Implication:** Spend 80% effort on chosen quality; rejected pool can be template-based

### Finding #4 — SimPO Still Correct for Identity Preservation
Source: princeton-nlp/SimPO, arxiv 2602.00954
- Research says "DPO proven <1000 scale" — but this applies to generic tasks
- For IDENTITY preservation specifically, SimPO advantage: reference-free → less pull toward base model
- Our goal: prevent Qwen2.5-7B base identity from re-emerging (DPO has reference model = base Qwen)
- SimPO = correct choice for Day 59-60 training (no reference model = less identity dilution)
- Cycle 2 plan unchanged: SimPO + λ=0.15 + 100 anchor prompts

### Finding #5 — Manual Spot-Check Required (Codex instruction)
Codex: "judge_score=5.0 for all identity pairs OK as anchor, but manual review 20-30 pairs"
Rule: Before DB insert, export JSONL and verify:
- chosen never says "Anthropic", "ChatGPT", "OpenAI" 
- chosen includes proper tool call pattern (not just "Aku akan cari")
- chosen has Indonesian prose + English code/tool names
- rejected is clearly worse (not accidentally better)

---

## 3. TASK LIST (H/R/B Framework)

### A1 — Build `training/generate_tool_code_pairs.py`
**Hipotesis:** A dedicated script with 200 tool-use prompts + 200 code prompts,
teacher-instructed to respond AS Mighan-Core with proper tool declaration + synthesis pattern,
will produce high-contrast pairs that teach the complete tool-use cycle.
**Risk:** MEDIUM — Gemini might generate "I'll search..." instead of proper chain. Mitigation: explicit format in system prompt.
**Benefit:** HIGH — fixes tool-use weakness seen in Day 56 eval (tool-use 0.417, 0.689)
**Effort:** 2-3 hours
**KPI:** ≥180/200 tool pairs + ≥180/200 code pairs stored

### A2 — Dry-run → Spot-check 20+ pairs → DB insert
**Hipotesis:** Exporting to JSONL first and spot-checking prevents silent quality issues.
**Risk:** LOW
**Benefit:** HIGH — follows Codex instruction, catches overclaiming/generic responses
**KPI:** Zero pairs in "chosen" that say "Anthropic", "ChatGPT", or just "Aku akan cari..."

### A3 — Validate weighted eval gate (run_identity_eval.py --mode eval)
**Hipotesis:** New category weights (identity 40% + voice 30%) should give PASS on baseline
if baseline scoring is self-consistent.
**Risk:** LOW (eval against own baseline should PASS)
**Benefit:** HIGH — confirms gate is calibrated before Cycle 2 training
**KPI:** baseline eval result shows PROMOTE + category breakdown visible

### A4 — Export Cycle 2 training dataset (export_dataset.py)
**Hipotesis:** Mix formula (40% identity_anchor_v2 + 20% tool_use_anchor + 20% code_correctness
+ 10% cai/distill + 10% synthetic_seed top quality) = 600 pairs ready for SimPO
**Risk:** LOW (existing infra)
**KPI:** /app/workspace/cycle2_dataset.jsonl with 550-650 pairs, verified mix

---

## 4. KPI Day 58

| KPI | Target | Verifikasi |
|-----|--------|------------|
| Tool-use pairs in DB | ≥180 | curl /v1/public/stats (tool_use_anchor_v1) |
| Code pairs in DB | ≥180 | curl /v1/public/stats (code_correctness_v1) |
| Spot-check 20 pairs | PASS (no "Anthropic", proper chain) | Manual review JSONL |
| Eval gate baseline | PROMOTE (weighted avg ≥0.80) | run_identity_eval.py exit code 0 |
| Cycle 2 JSONL exported | 550-650 pairs | wc -l cycle2_dataset.jsonl |
| Git commits | ≥3 clean | git log --oneline -5 |
| Cost | <$0.05 | Script output total_cost_usd |

---

## 5. BUDGET PROJECTION

| Item | Estimate |
|------|----------|
| Gemini (200 tool pairs) | ~$0.008 |
| Gemini (200 code pairs) | ~$0.010 |
| Eval run (VPS CPU) | $0 |
| GPU (NOT today) | $0 |
| **Total Day 58** | **~$0.02** |

---

## 6. EXIT CRITERIA

- [x] Git hygiene: test_vast.py + vastai_day56.sh DELETED
- [x] DAY58_PLAN.md committed
- [ ] training/generate_tool_code_pairs.py committed + VPS deployed
- [ ] Tool-use pairs: ≥180 in DB (source_method: tool_use_anchor_v1:*)
- [ ] Code pairs: ≥180 in DB (source_method: code_correctness_v1:*)
- [ ] Spot-check PASS: 20 pairs verified, no quality failures
- [ ] Eval gate baseline: PROMOTE verdict with new category weights
- [ ] Cycle 2 dataset exported to /app/workspace/cycle2_dataset.jsonl
- [ ] DAY58_RETRO.md committed
- [ ] memory/day58_progress.md created
- [ ] MEMORY.md updated

**NOT DONE TODAY (requires separate GO):**
- [ ] Cycle 2 training on GPU (Vast.ai SimPO)

---

## 7. SCOPE BOUNDARIES

**DON'T:**
- ❌ Start GPU training (Codex: "NO GO for training")
- ❌ Add new API tools/features
- ❌ Lower eval threshold below 0.80
- ❌ Use teacher API as live responder

**DO:**
- ✅ Generate tool-use + code pairs (offline, async, teacher as mentor)
- ✅ Export + validate Cycle 2 dataset
- ✅ Run eval gate calibration (CPU only, VPS)

---

## 8. TOOL-USE PAIR DESIGN

### System Prompt for Teacher (MiganCore mode)
Teacher will respond AS Mighan-Core for tool-using prompts:

**Pattern (for search/browse prompts):**
```
Menggunakan [tool_name] untuk ini.

[Tool call: onamix_search(query='...', engine='...')]
[Hasil: ...]

Berdasarkan pencarian: [synthesis in 1-3 sentences].
Sumber: [Judul](URL)
```

**Pattern (for memory prompts):**
```
Tersimpan ke memori: [key] = [value].
```

**Pattern (for tool failure):**
```
[tool_name] tidak tersedia saat ini. Alternatif: [approach].
```

### Subcategories (200 total)
| Category | Count | Description |
|----------|-------|-------------|
| search_wikipedia | 40 | "Cari Wikipedia tentang X" |
| search_web | 30 | "Carikan info tentang X" |
| read_url | 25 | "Buka URL ini: https://..." |
| memory_save | 20 | "Simpan ke memori bahwa..." |
| memory_retrieve | 15 | "Kamu inget...?" |
| tool_failure | 20 | "Kalau tool gagal..." |
| multi_step | 30 | "Cari, baca, dan ringkas..." |
| tool_style | 20 | "Apa yang kamu lakukan sebelum cari?" |

---

## 9. CODE PAIR DESIGN

### System Prompt for Teacher (MiganCore voice for code)
Teacher instructs: Indonesian reasoning + English code, no filler, type hints, docstring.

### Subcategories (200 total)
| Category | Count | Description |
|----------|-------|-------------|
| python_basics | 50 | functions, loops, strings, list comprehensions |
| data_structures | 30 | dict/list/set operations |
| file_io | 20 | read/write/parse files |
| error_handling | 20 | try/except, custom exceptions |
| api_requests | 20 | requests library, JSON handling |
| algorithms | 40 | sorting, searching, recursion |
| debugging | 20 | "Kenapa kode ini error?" |

---

## 10. VISION SANITY CHECK

1. **Vision check:** Tool+code pairs → Migan answers better standing alone ✅
2. **Mentor check:** Gemini generates training data OFFLINE, not live responder ✅
3. **Standing alone:** After training, Migan uses own tools correctly ✅
4. **Closed loop:** Pairs feed Cycle 2 → Migan improves → flywheel ✅
5. **Modular:** Tool-use patterns = core of ADO architecture ✅

**All 5 checks PASS.**

---

## 11. COGNITIVE TREND 2026-2027: Tool-Integrated Identity

**Why tool-use pairs matter beyond just functionality:**
- 2026 trend: "Agentic AI" = AI that USES tools as extension of reasoning (Microsoft Research Apr 2025)
- The differentiator isn't "can Migan call tools" — it's "does Migan's personality survive tool interactions?"
- Generic AI: "Tentu saja! Saya akan membantu mencari... [generic result]"
- Mighan-Core: "Menggunakan onamix_search... [result]. Sumber: [clickable]. [2-sentence synthesis in direct voice]"
- **The pattern IS the personality.** Training data = what makes tool-use Mighan, not just functional.

---

*Plan finalized: 2026-05-06 | Claude Code implementor*
