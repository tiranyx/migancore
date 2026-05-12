# BACKLOG ALIGNMENT — Post-Identity-Collapse Recovery
**Date:** 2026-05-12
**Trigger:** Identity collapse incident + 5-cycle rollback pattern analysis
**Status:** ALIGNMENT IN PROGRESS — Awaiting owner GO for Phase 0
**Previous Sprint:** Day 71d-72e (Claude infra + Kimi recovery)
**Next Sprint:** Day 72f-73 (Data audit + identity anchor)

---

## 0. ALIGNMENT CHECKPOINT

### What Just Happened (Brutal Honest)
| Event | Date | Outcome |
|---|---|---|
| Cycle 3 promoted | Day 60 | ✅ `migancore:0.3` — w_avg 0.9082 |
| Cycle 4-7c rollbacks | Day 63-71c | ❌ 5 failures |
| M1 pipeline build | Day 71d-72c | ✅ Infra built (feedback, CAI, distillation) |
| Identity SFT attempt | Day 72a-b | ⚠️ `identity_adapter_v0.4` created |
| DPO from base Qwen | Day 72b | ❌ Wrong base model |
| 0.8 sequential merge | Day 72c | ❌ Total identity collapse |
| Recovery + revert | Day 72d-e | ✅ Back to `migancore:0.7c` |
| Kimi audit + mapping | Day 72e | 🟡 This document |

### Current Production State (Verified Live)
```
API:        api.migancore.com — healthy, v0.5.16, Day 70 build
Model:      migancore:0.7c (reverted from broken 0.8)
Fallback:   migancore:0.3
Base ref:   qwen2.5:7b-instruct-q4_K_M
DB pairs:   3,359 (0.9% real, 99.1% synthetic/anchor)
Disk:       66% used (136GB free)
Git HEAD:   fea8f62 (M1.3+M1.4 + test fixes)
```

---

## 1. P0 — BLOCKERS (Cannot proceed without these)

### P0.1 🚨 AUDIT & PURGE CONTAMINATED TRAINING DATA
**Owner:** Kimi  
**Time:** 4 hours  
**Cost:** $0  
**Why P0:** All future training is poisoned if data not cleaned.

**Tasks:**
- [ ] Read `training/identity_sft_200.jsonl` line-by-line
- [ ] Flag any pair containing: Anthropic, Claude, OpenAI, ChatGPT, Google, Gemini, Alibaba, Qwen, Moonshot, Kimi, DeepSeek
- [ ] Flag any "meta-instruction" pairs ("Jangan jawab...", "Kamu harus...")
- [ ] Document contamination source (which `generate_*.py` script produced it)
- [ ] Create `identity_sft_200_CLEAN.jsonl` with only verified-clean pairs
- [ ] If clean pairs < 100, manually curate new pairs to reach 200

**Acceptance:**
- Zero competitor references in clean dataset
- Zero meta-instructions
- All 200 pairs verified by human read-through

---

### P0.2 🚨 VERIFY 0.7c HF CHECKPOINT EXISTS
**Owner:** Kimi  
**Time:** 30 min  
**Cost:** $0  
**Why P0:** All future training MUST start from 0.7c. If checkpoint missing, we cannot train.

**Tasks:**
- [ ] Check HF Hub: `Tiranyx/migancore-7b-soul-v0.7c` or equivalent
- [ ] Check VPS: `/opt/ado/data/ollama/models/merged_identity_v0.4/` (poisoned, don't use)
- [ ] Check VPS: any HF checkpoint for 0.7c
- [ ] If missing: export 0.7c from Ollama to HF format immediately
- [ ] Document checkpoint path for all training scripts

**Acceptance:**
- Verified HF checkpoint path exists and loads correctly
- `AutoModelForCausalLM.from_pretrained(path)` succeeds
- Tokenizer loads with correct chat template

---

### P0.3 🚨 LOCK TRAINING BASE MODEL POLICY
**Owner:** Kimi + Owner  
**Time:** 15 min  
**Cost:** $0  
**Why P0:** Prevents future catastrophic forgetting from wrong base.

**Policy to lock:**
```
TRAINING_BASE_MODEL = "/opt/ado/data/models/migancore_0.7c_hf"  # NEVER base Qwen
EXCEPTION: Only if explicitly approved by owner with documented reason
```

**Tasks:**
- [ ] Add constant to `api/config.py`
- [ ] Add guard to all training scripts: exit if base ≠ 0.7c
- [ ] Document in `LESSONS_LEARNED.md` as hard rule

---

## 2. P1 — IDENTITY ANCHOR (1-2 days, blocks everything else)

### P1.1 TRAIN SFT IDENTITY FROM 0.7c
**Owner:** Kimi / RunPod RTX 4090  
**Time:** 1 day  
**Cost:** ~$5 (Vast.ai RTX 4090, 6-8 hours)  
**Blocked by:** P0.1 (clean data), P0.2 (checkpoint)

**Config:**
```python
base_model = "/opt/ado/data/models/migancore_0.7c_hf"  # NOT Qwen
num_samples = 200  # from P0.1 clean dataset
lora_r = 32
lora_alpha = 64
lora_dropout = 0.05
epochs = 5
mask_prompt = True  # only assistant tokens contribute loss
learning_rate = 2e-4
```

**Tasks:**
- [ ] Verify chat template matches Qwen2.5-Instruct format
- [ ] Train SFT identity adapter
- [ ] Merge adapter into base → `migancore_0.8_identity_merged`
- [ ] Run MMLU delta check (guard against catastrophic forgetting)

---

### P1.2 CONVERT TO GGUF + DEPLOY
**Owner:** Kimi / VPS  
**Time:** 4 hours  
**Cost:** $0  
**Blocked by:** P1.1

**Tasks:**
- [ ] `convert_hf_to_gguf.py --outtype f16`
- [ ] `llama-quantize q4_K_M`
- [ ] Create Ollama model `migancore:0.8-clean`
- [ ] Update API config to `migancore:0.8-clean`
- [ ] Deploy A/B: 10% traffic → monitor 24h

---

### P1.3 IDENTITY EVAL GATE (MANDATORY)
**Owner:** Kimi  
**Time:** 2 hours  
**Cost:** $0  
**Blocked by:** P1.2

**Test matrix:**
| Test | System Prompt | Expected | Pass? |
|---|---|---|---|
| Direct identity | EMPTY (no SOUL) | "Saya Mighan-Core..." | MUST PASS |
| Direct identity | SOUL.md | "Saya Mighan-Core..." | MUST PASS |
| Tool use | SOUL.md | Correct tool call | ≥ 80% |
| Regression | SOUL.md | 10 known-good scenarios | 10/10 pass |
| MMLU delta | N/A | vs 0.7c baseline | Δ > -2% |

**Tasks:**
- [ ] Run `eval/identity_eval.py` with EMPTY system prompt
- [ ] Run tool-use eval
- [ ] Run regression eval
- [ ] Run MMLU eval
- [ ] Generate eval report

**Acceptance:**
- Identity eval WITHOUT system prompt MUST pass (cosine sim > 0.85)
- No regression > -0.05 on any category
- MMLU delta > -2%

---

## 3. P2 — DATA PIPELINE HARDENING (2-3 days)

### P2.1 FIX PENDING COMPLETER WORKER
**Owner:** Kimi  
**Time:** 1 day  
**Cost:** $0  
**Why:** User thumbs_down currently stores `chosen=PENDING`, never refined.

**Tasks:**
- [ ] Debug `api/workers/user_feedback_processor.py`
- [ ] Ensure worker runs every 10 min (cron verified)
- [ ] Fix: PENDING pairs must be refined by teacher API
- [ ] Test end-to-end: thumbs_down → worker → refined pair → DB

---

### P2.2 OWNER DATA ENDPOINTS
**Owner:** Kimi  
**Time:** 1 day  
**Cost:** $0  
**Why:** Brief P4 — owner must be able to retrain with business data.

**Endpoints:**
- `POST /v1/admin/owner-data/upload` — CSV/JSONL upload
- `POST /v1/admin/owner-data/example` — Manual pair
- `POST /v1/admin/owner-data/correction` — "Response X salah, harusnya Y"
- `GET /v1/admin/owner-data` — List uploaded
- `DELETE /v1/admin/owner-data/{id}` — Remove with audit

**Tasks:**
- [ ] Implement router `api/routers/owner_data.py`
- [ ] Add RLS (admin-only)
- [ ] Add audit logging
- [ ] Test upload → curator → dataset flow

---

### P2.3 CAI AUTO-LOOP AT 100%
**Owner:** Kimi  
**Time:** 0.5 day  
**Cost:** $0 (teacher API cost for critique only)

**Tasks:**
- [ ] Change `CAI_SAMPLE_RATE` from 0.5 → 1.0
- [ ] Reduce quorum from 3 → 2 judges
- [ ] Monitor: pairs/day generated
- [ ] Target: ≥ 50 CAI pairs/day from production chat

---

### P2.4 TEACHER DISTILLATION CONTINUOUS
**Owner:** Kimi  
**Time:** 0.5 day  
**Cost:** ~$5/day cap

**Tasks:**
- [ ] Verify 6h cron job active
- [ ] Add cost guard (kill if > $5/day)
- [ ] Add health monitor (alert if 2 cycles fail)
- [ ] Target: ≥ 50 teacher pairs/day

---

## 4. P3 — MULTI-LOSS TRAINING ENGINE (2-3 days)

### P3.1 SFT TRAINER (identity, voice, format)
**Owner:** Kimi  
**Time:** 1 day  
**Cost:** $0 (code only)

**Tasks:**
- [ ] Refactor `training/train_sft_identity.py` → generic `training/train_sft.py`
- [ ] Support: identity, voice, tool-format, owner-domain
- [ ] Config via dataset metadata (not hardcoded)
- [ ] Test on 10 pairs before full run

---

### P3.2 DPO TRAINER
**Owner:** Kimi  
**Time:** 1 day  
**Cost:** $0 (code only)

**Tasks:**
- [ ] Implement `training/train_dpo.py`
- [ ] Base model: migancore checkpoint (not Qwen)
- [ ] Config via dataset metadata
- [ ] Test on 10 pairs

---

### P3.3 KTO TRAINER
**Owner:** Kimi  
**Time:** 1 day  
**Cost:** $0 (code only)

**Tasks:**
- [ ] Implement `training/train_kto.py`
- [ ] Single-label input (thumbs up/down)
- [ ] No paired data needed
- [ ] Test on 10 pairs

---

### P3.4 TRAINING TRIGGER SERVICE
**Owner:** Kimi  
**Time:** 0.5 day  
**Cost:** $0

**Tasks:**
- [ ] Threshold trigger: ≥ 200 new pairs
- [ ] Schedule trigger: weekly batch
- [ ] Event trigger: owner upload
- [ ] Manual trigger: admin endpoint
- [ ] Log all triggers to `training_runs` table

---

## 5. P4 — CYCLE 8 (First Valid Cycle Post-Recovery)

### P4.1 DATASET ASSEMBLY
**Owner:** Kimi  
**Time:** 0.5 day  
**Cost:** $0

**Mix:**
```
30% replay from Cycle 7c dataset (or 0.7c baseline)
70% new:
  - 100 identity SFT (from P1.1)
  - 100 user thumbs (KTO-ready)
  - 200 teacher distilled
  - 100 self-play
```

---

### P4.2 TRAIN: SFT → DPO SEQUENTIAL
**Owner:** RunPod RTX 4090  
**Time:** 1 day  
**Cost:** ~$8

**Protocol:**
1. SFT identity from 0.7c → `migancore_0.8_sft`
2. DPO preferences from `migancore_0.8_sft` → `migancore_0.8_sft_dpo`
3. Both adapters share SAME base → valid sequential merge

---

### P4.3 EVAL + PROMOTE
**Owner:** Kimi  
**Time:** 4 hours  
**Cost:** $0

**Tasks:**
- [ ] Identity eval WITHOUT system prompt
- [ ] Tool use eval
- [ ] Regression eval
- [ ] MMLU delta
- [ ] If ALL pass: deploy as `migancore:0.8` (overwrite broken 0.8)
- [ ] If ANY fail: ROLLBACK, document lesson

---

## 6. P5 — BETA DATA COLLECTION (1 week)

### P5.1 FRONTEND FEEDBACK HARDENING
**Owner:** Kimi  
**Time:** 0.5 day  
**Cost:** $0

**Tasks:**
- [ ] Verify thumbs click → POST /feedback → DB
- [ ] Add "edit response" button
- [ ] Add "regenerate" tracker
- [ ] Add "why was this bad?" optional text

---

### P5.2 BETA LAUNCH
**Owner:** Owner + Kimi  
**Time:** 1 week  
**Cost:** $0

**Tasks:**
- [ ] Announce to 53 registered users
- [ ] Daily pair count dashboard
- [ ] Monitor identity drift (auto-eval gate)
- [ ] Target: 20% real-data ratio within 2 weeks

---

## 7. P6 — WHITE-LABEL + CLONE (Brief Phase 2)

### P6.1 CLONE MECHANISM
**Owner:** Kimi  
**Time:** 3-5 days  
**Cost:** $0

**Blocked by:** P4 success (solid identity anchor)

**Tasks:**
- [ ] Per-org Docker template
- [ ] Clone endpoint: parent ADO → child ADO
- [ ] Inherit identity weights + SOUL.md
- [ ] Tenant-scoped data isolation

---

### P6.2 LICENSE ENFORCEMENT
**Owner:** Kimi  
**Time:** 2 days  
**Cost:** $0

**Tasks:**
- [ ] Offline validation (no phone-home)
- [ ] Tier enforcement (max instances, features)
- [ ] Expiry handling

---

### P6.3 WHITE-LABEL NAMING
**Owner:** Kimi  
**Time:** 2 days  
**Cost:** $0

**Tasks:**
- [ ] Replace hardcoded "Migan" with config
- [ ] Per-tenant branding
- [ ] Logo + colors

---

## 8. BACKLOG SUMMARY TABLE

| Priority | Item | Time | Cost | Blocked By | Owner |
|---|---|---|---|---|---|
| P0.1 | Audit & purge contaminated data | 4h | $0 | — | Kimi |
| P0.2 | Verify 0.7c HF checkpoint | 30m | $0 | — | Kimi |
| P0.3 | Lock training base model policy | 15m | $0 | — | Kimi + Owner |
| P1.1 | SFT identity from 0.7c | 1d | ~$5 | P0.1, P0.2 | Kimi / RunPod |
| P1.2 | Convert GGUF + deploy 0.8-clean | 4h | $0 | P1.1 | Kimi |
| P1.3 | Identity eval gate (no SOUL) | 2h | $0 | P1.2 | Kimi |
| P2.1 | Fix PENDING completer worker | 1d | $0 | — | Kimi |
| P2.2 | Owner data endpoints | 1d | $0 | — | Kimi |
| P2.3 | CAI auto-loop 100% | 0.5d | $0 | — | Kimi |
| P2.4 | Teacher distillation continuous | 0.5d | $5/day | — | Kimi |
| P3.1 | SFT trainer refactor | 1d | $0 | — | Kimi |
| P3.2 | DPO trainer | 1d | $0 | — | Kimi |
| P3.3 | KTO trainer | 1d | $0 | — | Kimi |
| P3.4 | Training trigger service | 0.5d | $0 | — | Kimi |
| P4.1 | Cycle 8 dataset assembly | 0.5d | $0 | P1-P3 | Kimi |
| P4.2 | Cycle 8 train (SFT→DPO) | 1d | ~$8 | P4.1 | RunPod |
| P4.3 | Cycle 8 eval + promote | 4h | $0 | P4.2 | Kimi |
| P5.1 | Frontend feedback hardening | 0.5d | $0 | — | Kimi |
| P5.2 | Beta launch + data collection | 1w | $0 | P4.3 | Owner + Kimi |
| P6.1 | Clone mechanism | 3-5d | $0 | P4.3 | Kimi |
| P6.2 | License enforcement | 2d | $0 | P4.3 | Kimi |
| P6.3 | White-label naming | 2d | $0 | P4.3 | Kimi |

**Total P0-P4 (foundation):** ~10-12 days, ~$13 compute  
**Total P5 (beta):** ~1 week, $0 compute  
**Total P6 (revenue):** ~1-2 weeks, $0 compute  
**Grand total:** ~4-5 weeks to first paying client

---

## 9. ROLLBACK PLAN (Every Phase)

**If any eval fails:**
1. Do NOT deploy
2. Document failure in `LESSONS_LEARNED.md`
3. ROLLBACK to `migancore:0.7c`
4. Analyze: wrong base? contaminated data? wrong loss? mixed objectives?
5. Fix root cause, retry

**If production degrades post-deploy:**
1. Auto-rollback via `docker compose up -d api` with previous image
2. Alert owner
3. Preserve conversation logs for analysis

---

## 10. DECISIONS AWAITING OWNER

| ID | Decision | Default | Impact |
|---|---|---|---|
| D11 | GO Phase 0 (data audit)? | — | Blocks everything |
| D12 | GO Phase 1 (SFT identity)? | — | Blocks Cycle 8 |
| D13 | Budget for RunPod training? | $20/mo | Cycle 8 + retries |
| D14 | Beta launch target date? | Day 80 | Revenue timing |
| D15 | First client target? | Day 101-130 | Resource allocation |

---

*BACKLOG_ALIGNMENT.md — owned by Kimi, reviewed by Owner, executed by Kimi/Claude.*  
*Update after each phase completion. Strike through completed items.*
