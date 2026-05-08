# RESEARCH 71E — TRAINING INFRASTRUCTURE & 4-PATHWAY GROWTH ARCHITECTURE
> Tanggal: 2026-05-08 (Day 71d EOD)
> Author: Claude Sonnet 4.6 (main implementor)
> Status: **RESEARCH PHASE — NOT YET BUILDING** (awaiting owner approval)
> Ref: VISION_PRINCIPLES_LOCKED · MIGANCORE-PROJECT-BRIEF · DAY60_RETRO · all rollback retros

---

## 0. CONTEXT & RESET

Owner Direction (Day 71d, post-rollback realization):
> "Bikin infrastruktur dan arsitektur solid dulu, supaya mudah ditrain, pastikan dapat menyimpan data. Pastikan dapat dilatih dan tumbuh dengan berbagai cara: tumbuh sendiri, tumbuh di input data oleh saya, tumbuh di input oleh user, dan diajakar oleh teacher API. Selebihnya kamu riset dulu dan analisa mendalam hal-hal lainnya. Tools, metode, orkestrasi dan lainnya."

Decision: **STOP brain training cycles.** Pivot to infrastructure-first.

**5 brain cycles failed in a row** (Cycle 4, 6, 7, 7b, 7c) since Day 60 promote of `migancore:0.3`.
Root cause per lessons (#170-185): wrong loss tool choice, signal density too low, eval baseline drift,
trying to fix multiple things per cycle, NO real production data flowing in (99% synthetic).

This document = the SOLID FOUNDATION before any more training.

---

## 1. VISION — 4-PATHWAY MULTI-SOURCE GROWTH

```
                    ┌──────────────────────────────┐
                    │   MIGANCORE BRAIN (ADO)      │
                    │  ┌──────┐ ┌──────┐ ┌──────┐  │
                    │  │ OTAK │ │SYARAF│ │ JIWA │  │
                    │  └──┬───┘ └──┬───┘ └──┬───┘  │
                    └────────────────────────────────┘
                             ▲
                             │ Hot-swap deploy
                             │
                    ┌────────┴───────────┐
                    │   TRAINING ENGINE  │
                    │  (multi-loss)      │
                    └────────▲───────────┘
                             │
                    ┌────────┴───────────┐
                    │  DATA CURATION     │
                    │  (quality + dedup) │
                    └────────▲───────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
        │ SELF    │   │ OWNER   │   │ USER    │   │ TEACHER │
        │ growth  │   │ growth  │   │ growth  │   │ growth  │
        │         │   │         │   │         │   │         │
        │self-play│   │uploads  │   │chats    │   │API gen  │
        │critic   │   │examples │   │feedback │   │critique │
        │revise   │   │correct  │   │retry    │   │distill  │
        └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

### 1.1 Definisi tiap pathway

**A. SELF-GROWTH** (autonomous, async)
- Brain mencerna percakapannya sendiri
- Self-critique loop (CAI pattern: critique → revise → score)
- Self-play: brain solve same problem multiple ways, picks best
- Data source: own conversation logs

**B. OWNER-GROWTH** (manual, deliberate)
- Owner upload dataset domain-specific (SOP, kebijakan, dokumen perusahaan)
- Owner input examples: "kalau ditanya X, jawab seperti Y"
- Owner input corrections: "response ini salah, harusnya begini"
- Data source: owner UI / CLI / file upload

**C. USER-GROWTH** (organic, scale)
- Beta user thumbs up/down
- Implicit signals: retry, edit, regenerate, time-on-message
- User-initiated correction ("bukan, maksud saya...")
- Data source: chat conversations + frontend feedback

**D. TEACHER-GROWTH** (offline, supervised)
- Teacher API (Kimi/Claude/GPT/Gemini) generate "what better answer would be"
- Multi-teacher quorum critique
- Distillation: teacher solves → brain learns
- Data source: async batch jobs against APIs

---

## 2. CURRENT STATE AUDIT (Day 71d, verified live)

### 2.1 Schema — GOOD (already designed)

```sql
-- Database tables existing (verified Day 71d):
agents              ✓
agent_tool_grants   ✓
api_keys            ✓
archival_memory     ✓ (UNUSED — Letta blocks idle)
audit_events        ✓
conversations       ✓ (72 rows)
datasets            ✓ (UNUSED — 0 rows!)
experiments         ✓ (UNUSED — 0 rows!)
interactions_feedback ✓ (UNUSED — 0 rows! despite frontend clicks)
kg_entities         ✓ (UNUSED — 0 rows!)
kg_relations        ✓ (UNUSED — 0 rows!)
memory_blocks       ✓
messages            ✓ (194 rows)
model_versions      ✓ (1 row)
papers              ✓
preference_pairs    ✓ (3,354 rows — but 99.7% synthetic/anchor)
refresh_tokens      ✓
tenants             ✓
tools               ✓ (29 rows after Day 71d seed)
training_runs       ✓ (UNUSED — 0 rows!)
users               ✓
```

**Verdict:** Schema sudah lengkap. **Yang missing: lifecycle wiring** — tabel-tabel critical (datasets, training_runs, kg_entities, interactions_feedback) tidak terisi karena no one writes to them.

### 2.2 Preference Pair Source Distribution (verified)

| Source | Count | % | Path |
|--------|-------|---|------|
| synthetic_seed_v1 | 1,672 | 49.9% | Auto-gen from 120 seeds |
| Anchor cycles (creative/tool/voice/evolution) | 1,653 | 49.3% | Targeted manual generation |
| **cai_pipeline** | **18** | **0.5%** | **Real conversation critique** |
| **distill_kimi_v1** | **10** | **0.3%** | **Teacher refinement** |
| **user_thumbs_up** | **1** | **0.03%** | **Real user signal** |
| **user_thumbs_down** | **0** | **0%** | **Not flowing!** |
| **owner uploads** | **0** | **0%** | **No pathway exists** |
| **TOTAL real-data** | **29** | **0.86%** | **vs 3,325 synthetic = 99.14%** |

**Konklusi keras:** Brain training kelaparan data NYATA. 99% synthetic = generic, no proprietary signal.

### 2.3 Pathway Status Audit

| Pathway | Endpoint exists? | Worker alive? | Data flowing? | Status |
|---------|------------------|---------------|---------------|--------|
| **A. Self** | CAI endpoint | 50% sample, mostly idle | Trickle (18 pairs) | 🟡 Partial |
| **B. Owner** | None | None | None | ❌ Not built |
| **C. User** | `/feedback` POST | No PENDING-completion worker | thumbs_up=1, thumbs_down=0 | ❌ Broken |
| **D. Teacher** | distillation.py | Manual trigger only | 10 pairs total | 🟡 Manual |

### 2.4 Loss Function Coverage

| Loss | Supported? | Used in? | Gap |
|------|-----------|----------|-----|
| **ORPO** (apo_zero) | ✅ | All cycles 1-7c | Wrong tool for length/style (Lesson #175) |
| **SFT** | ⚠️ Code exists not wired | Never | NEEDED for identity + voice |
| **DPO** | ⚠️ TRL has it | Never | Needed for clean preferences |
| **KTO** | ❌ Not implemented | Never | NEEDED — fits user thumbs directly |
| **SimPO** | ⚠️ TRL has it | Never | Length-normalized, good for chat |
| **APO** (anchor) | ⚠️ Mentioned in docs | Theoretical | Identity preservation |
| **GRPO** | ❌ Not impl | Never | Reasoning task option |

**Konklusi:** Cuma ORPO yang battle-tested. Kalau ORPO salah tool, kita tidak punya alternatif siap deploy.

---

## 3. RESEARCH — 2025-2026 SOTA

### 3.1 Loss Function Matrix (kapan pakai apa)

| Use case | Best loss | Why |
|----------|-----------|-----|
| **Identity reinforcement** (fix Lesson #170) | **SFT + APO regularization** | Direct supervision of "Saya adalah Mighan-Core" pattern. APO prevents drift. |
| **Voice/style targeting** (Q5 fail) | **SFT (focused) THEN DPO** | Lesson #175: ORPO wrong. SFT teaches pattern, DPO refines preferences. |
| **User thumbs feedback** | **KTO** | Single-label signal, no need for paired data. Perfect fit for thumbs_up/down. |
| **Tool-use accuracy** | **SFT + few-shot in SOUL** | Format conditioning via direct examples, not preference. |
| **Reasoning / multi-step** | **GRPO** (DeepSeek R1 method) | Group relative policy optimization. Multiple samples, no critic needed. |
| **Continual learning** (mix old + new) | **DPO with replay buffer** | Prevent catastrophic forgetting. |

**Key insight:** No single loss wins all categories. **Multi-loss arsenal needed.**

### 3.2 Memory Architecture Decision

| Option | Strength | Weakness | Fit for ADO? |
|--------|----------|----------|--------------|
| **Letta** (MemGPT) | 3-tier (core/recall/archival), self-editing | Lock-in to Letta runtime | ⭐⭐⭐ Best fit (we already use it) |
| **Mem0** | Personalization-focused, vector+KG | Not time-aware | ⭐⭐ Good for per-tenant |
| **Zep/Graphiti** | Temporal KG, multi-fact entity tracking | 3-5x cost, complex | ⭐⭐ Phase 3+ |
| **Cognee** | Privacy-first deep KG | Smaller community | ⭐⭐ Match brief P1 (privacy) |

**Decision: Keep Letta (already integrated)**, but actually USE it:
- Enable archival memory (currently 0 rows!)
- Per-tenant memory blocks
- Use core memory as identity anchor (Lesson #170 fix)

### 3.3 Orchestration Decision

| Option | Pattern | Fit |
|--------|---------|-----|
| **LangGraph** | State machine (outer) | ⭐⭐⭐ Already in use (`director.py`) |
| **Letta runtime** | Stateful agent | ⭐⭐ For future multi-agent spawn |
| **Dapr Agents** | Durable execution + K8s | ⭐ Overkill for solo founder |
| **Agno (AgentOS)** | Control plane | ⭐ Good if multi-agent fleet |

**Decision: LangGraph for stateful chat, custom Python for training pipeline** (simpler than overkill stack).

### 3.4 Active Learning + Curation

Not all preference pairs equal. **Active learning** = pick samples that MAX information gain.

| Method | Description | Fit |
|--------|-------------|-----|
| **Uncertainty sampling** | Where model is least confident → train there | ⭐⭐⭐ Easy to implement |
| **Query-by-committee** | Multiple judges disagree → high info | ⭐⭐ Need multi-teacher |
| **Diversity sampling** | Cluster prompts, sample per cluster | ⭐⭐ Prevent topic skew |
| **Coreset selection** | Optimal subset that covers distribution | ⭐ Complex |

**Decision: Implement uncertainty sampling first** (low cost, high value).

### 3.5 Continual Learning (prevent forgetting)

| Method | Description | Fit |
|--------|-------------|-----|
| **Replay buffer** | Mix old + new data per cycle | ⭐⭐⭐ MUST HAVE — prevents Cycle 4-style regression |
| **EWC** (Elastic Weight Consolidation) | Constrain weight changes | ⭐⭐ Complex but proven |
| **LoRA stacking** | Train new adapter, merge or chain | ⭐⭐⭐ Already supported by PEFT |
| **Knowledge distillation** | Old model teaches new | ⭐⭐ Use case: cycle migration |

**Decision: Replay buffer + LoRA stacking** = simple, proven, fits our infra.

---

## 4. PROPOSED ARCHITECTURE

### 4.1 Data Flow (end-to-end)

```
┌──────────────────────────────────────────────────────────────────┐
│ INGEST LAYER (4 pathways write here)                             │
├──────────────────────────────────────────────────────────────────┤
│  A. Self    : services/cai_critique.py (already exists)          │
│  B. Owner   : NEW api/routers/owner_data.py (BUILD THIS)         │
│  C. User    : conversations.py /feedback (FIX PENDING completion)│
│  D. Teacher : services/distillation.py (run continuously)        │
└─────────┬────────────────────────────────────────────────────────┘
          │ writes to:
          ▼
┌──────────────────────────────────────────────────────────────────┐
│ STORAGE LAYER (Postgres + Qdrant + Letta)                        │
├──────────────────────────────────────────────────────────────────┤
│  preference_pairs    : raw pairs from 4 sources                  │
│  interactions_feedback: thumbs/retry/edit signals (KTO-ready)    │
│  archival_memory     : Letta long-term per-tenant                │
│  kg_entities/relations: KG of entities mentioned (for context)   │
│  datasets            : versioned curated training sets           │
└─────────┬────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────┐
│ CURATION LAYER (NEW — services/curator.py)                       │
├──────────────────────────────────────────────────────────────────┤
│  - Quality scoring (judge_score threshold)                       │
│  - Dedup (hash on prompt+chosen)                                 │
│  - Active learning selection (uncertainty)                       │
│  - Source attribution (track self/owner/user/teacher mix)        │
│  - Diversity sampling (per source_method category)               │
│  - PENDING completion (user_thumbs_down → teacher refines)       │
└─────────┬────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────┐
│ DATASET ASSEMBLY (NEW — services/dataset_builder.py)             │
├──────────────────────────────────────────────────────────────────┤
│  - Replay buffer (mix N% prior cycle + N% new)                   │
│  - Source mix policy (owner > user > teacher > self)             │
│  - Train/val split                                                │
│  - JSONL export with format per loss type                        │
│  - INSERT into datasets table with lineage                       │
└─────────┬────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────┐
│ TRAINING TRIGGER (NEW — services/training_trigger.py)            │
├──────────────────────────────────────────────────────────────────┤
│  Triggers:                                                        │
│  - Threshold (≥200 NEW pairs accumulated)                        │
│  - Schedule (weekly batch, Sunday 02:00 UTC)                     │
│  - Event (owner uploads new dataset → kick off)                  │
│  - Manual (admin endpoint)                                        │
└─────────┬────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────┐
│ TRAINING ENGINE (multi-loss, REFACTOR existing)                  │
├──────────────────────────────────────────────────────────────────┤
│  training/train_sft.py     : SFT for identity, voice, format     │
│  training/train_dpo.py     : DPO for clean preference pairs      │
│  training/train_kto.py     : KTO for single-label thumbs         │
│  training/train_orpo.py    : ORPO (existing, keep)               │
│  training/train_simpo.py   : SimPO for length-balanced chat      │
│  Common: HF roundtrip (Lesson #173), config via dataset metadata │
└─────────┬────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────┐
│ EVAL GATE (NEW — formalize as service)                           │
├──────────────────────────────────────────────────────────────────┤
│  - Run identity_eval.py with FROZEN baseline (Day 60)            │
│  - Run regression eval (no category drops > -0.05)               │
│  - Run formal smoke (3 owner-defined sanity prompts)             │
│  - PROMOTE / CONDITIONAL / ROLLBACK decision                     │
│  - Auto-rollback if production degrades after promote            │
└─────────┬────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────┐
│ DEPLOYMENT + LINEAGE                                             │
├──────────────────────────────────────────────────────────────────┤
│  - INSERT training_runs row                                       │
│  - INSERT model_versions row                                      │
│  - Hot-swap migancore:N                                           │
│  - Tag dataset_id + parent_dataset_id (full lineage)             │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Storage Schema Additions Needed

**a. `preference_pairs` table** — sudah cukup, tambahkan:
```sql
ALTER TABLE preference_pairs ADD COLUMN source_pathway VARCHAR(16);
-- values: 'self', 'owner', 'user', 'teacher'
ALTER TABLE preference_pairs ADD COLUMN tenant_id UUID;
-- per-tenant data isolation (zero leak architecture)
ALTER TABLE preference_pairs ADD COLUMN status VARCHAR(16) DEFAULT 'pending';
-- 'pending', 'curated', 'training', 'used'
ALTER TABLE preference_pairs ADD COLUMN parent_pair_id UUID;
-- for refined PENDING pairs
```

**b. `datasets` table** — populate finally:
```sql
-- Insert per cycle:
{
  "name": "cycle8_mixed_v1",
  "source_type": "mixed",  -- self+owner+user+teacher
  "size_samples": 850,
  "parent_dataset_id": "cycle7_dataset_uuid",  -- replay lineage
  "domain": "indonesian_general",
  "language": "id",
  "metadata": {
    "source_pathway_mix": {"self": 100, "owner": 50, "user": 200, "teacher": 500},
    "loss_target": "sft+dpo",
    "replay_pct_from_parent": 30
  }
}
```

**c. `training_runs` table** — populate per training:
```sql
{
  "version_id": "migancore:0.4_uuid",
  "base_model": "Qwen/Qwen2.5-7B-Instruct",
  "method": "sft+dpo",
  "dataset_id": "cycle8_dataset_uuid",
  "hyperparameters": {"lr": 5e-7, "epochs": 3, "lora_r": 16},
  "cost_usd": 0.15,
  "status": "completed",
  "train_loss_final": 1.234,
  "eval_loss_final": 1.456,
  "promoted": true
}
```

**d. NEW `growth_signals` table** (proposed):
```sql
CREATE TABLE growth_signals (
  id UUID PRIMARY KEY,
  pathway VARCHAR(16),  -- 'self', 'owner', 'user', 'teacher'
  signal_type VARCHAR(32),  -- 'preference_pair', 'thumbs', 'edit', 'upload'
  source_id UUID,  -- FK to message, conversation, dataset
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  consumed_in_dataset_id UUID  -- track which dataset used this
);
-- Single source of truth for "what came in, where did it go"
```

### 4.3 Owner Data Ingestion (NEW pathway B)

Brief Section 2 says: *"ADO bisa di-training ulang dengan data bisnis & flow bisnis internal perusahaan"*.

**API endpoints needed:**
```
POST /v1/admin/owner-data/upload       # CSV/JSONL/PDF upload
POST /v1/admin/owner-data/example      # Manual prompt+answer pair
POST /v1/admin/owner-data/correction   # "Response X salah, harusnya Y"
POST /v1/admin/owner-data/batch        # Bulk JSON of pairs
GET  /v1/admin/owner-data              # List uploaded datasets
DELETE /v1/admin/owner-data/{id}       # Remove (with audit log)
```

**Data formats supported:**
1. CSV: prompt, chosen, rejected, category
2. JSONL: TRL DPO format
3. Plain text: bulk Q&A → auto-parse via teacher
4. Document: PDF/Markdown → chunk + generate Q&A pairs via teacher

### 4.4 User Feedback PENDING Completion (FIX pathway C)

Currently: thumbs_down stores `chosen=PENDING`. Never refined.

**Worker needed:** `services/pending_completer.py`
```python
async def complete_pending_pairs():
    """Background task: take PENDING preference pairs, refine via teacher."""
    pending = await db.query(PreferencePair).where(
        PreferencePair.chosen.startswith('PENDING')
        | PreferencePair.rejected.startswith('PENDING')
    ).limit(50)
    
    for pair in pending:
        if pair.chosen.startswith('PENDING'):
            # User said this response was bad — get teacher's better version
            better = await ask_teacher(
                pair.prompt, 
                rejected=pair.rejected,
                instruction="Generate better response for this prompt"
            )
            pair.chosen = better
            pair.judge_model = 'teacher_refinement'
            pair.status = 'curated'
        # ...
```

Run: every hour via cron, batch 50 pairs.

### 4.5 Self-Growth (REVIVE pathway A)

CAI pipeline exists but at 50% sample rate, mostly idle. Activate:

**Configuration:**
```python
CAI_SAMPLE_RATE = 1.0  # ALL conversations get critiqued (was 0.5)
CAI_QUORUM_SIZE = 2    # 2 judges agree (was 3 = expensive)
CAI_MIN_CONVERSATION_LEN = 4  # only critique meaningful exchanges
```

**Self-play addition** (NEW):
```python
async def self_play_loop():
    """Pick uncertain prompts, brain answers 3 ways, judge picks best."""
    seeds = await get_diverse_prompts(50)  # from existing kg_entities or curated
    for seed in seeds:
        responses = [await brain.answer(seed, temp=0.3+i*0.2) for i in range(3)]
        best, second = await judge.rank(seed, responses)
        store_pair(prompt=seed, chosen=best, rejected=second, source='self_play')
```

### 4.6 Teacher Distillation (FORMALIZE pathway D)

**Convert one-shot to continuous:**
- Worker every 6h: take 100 most uncertain conversations (from user signals)
- Multi-teacher quorum: 2 of 4 teachers agree → store
- Cost cap: $5/day distillation budget
- Track: `source_method='teacher_quorum_vN'` with `judge_model='kimi+gemini'`

---

## 5. PHASED BUILD PLAN

### Phase 0 — Foundation (THIS DOC + agent reviews) | 0.5 day
- [x] Audit current state (DONE, this section)
- [ ] Owner approval of architecture
- [ ] Kimi review of method/loss matrix
- [ ] Codex QA of schema additions

### Phase 1 — Data Pipeline Plumbing | 2 days
- [ ] Schema migrations (4 ALTER + 1 CREATE)
- [ ] PENDING completer worker (fix user-feedback pathway)
- [ ] services/curator.py (quality + dedup + uncertainty selection)
- [ ] services/dataset_builder.py (replay buffer + version + lineage)
- [ ] Populate training_runs + datasets retroactively (1 row per past cycle)

### Phase 2 — 4 Pathway Endpoints | 3 days
- [ ] **A:** services/self_play.py (revive CAI + add self-play loop)
- [ ] **B:** routers/owner_data.py (5 endpoints: upload/example/correction/batch/list)
- [ ] **C:** worker pending_completer.py (cron, batch 50/hour)
- [ ] **D:** services/distillation_continuous.py (6h cycle, $5/day cap)

### Phase 3 — Multi-Loss Training Engine | 3 days
- [ ] training/train_sft.py (Identity reinforcement, fix Lesson #170)
- [ ] training/train_dpo.py (clean preference pairs)
- [ ] training/train_kto.py (user thumbs direct)
- [ ] training/train_simpo.py (chat length-balanced)
- [ ] Refactor cycle launcher: pick loss based on dataset metadata
- [ ] Eval gate as service (formal SLA per cycle)

### Phase 4 — Identity Anchor Training | 1 day (BLOCKER for white-label)
- [ ] Generate 200 SFT identity pairs (single-cycle, no mixing)
- [ ] Cycle 8: SFT-only on identity → migancore:0.4
- [ ] Test: tanpa system prompt, model masih says "Mighan-Core" (Lesson #170 fix)

### Phase 5 — Beta Data Collection (Real Users) | 1 week
- [ ] Frontend: ensure thumbs_up/down click → POST /feedback (already works, verify)
- [ ] Frontend: add "edit response" button (collect corrections)
- [ ] Frontend: add "regenerate" tracker (implicit retry signal)
- [ ] Beta launch (per BETA_READY_71D.md)
- [ ] Daily preference pair count dashboard

### Phase 6 — Cycle 8 Mixed-Source Training | 2 days
- [ ] Dataset = 30% replay (Cycle 3) + 70% new (mixed sources):
  - 100 user thumbs_up (KTO-style)
  - 200 owner-uploaded examples
  - 300 teacher-distilled
  - 100 self-play
  - 200 from prior preference_pairs (replay)
- [ ] Multi-loss train: SFT (identity anchor) → DPO (preferences) sequential
- [ ] Eval gate, decide promote/rollback
- [ ] Document learnings

### Phase 7 — White-Label + Clone (Brief Phase 2) | 2 weeks
- Per brief Section 2A — only do this AFTER infrastructure solid
- GAP-01 Clone Mechanism, GAP-04 White-label, GAP-03 License enforcement

**Total estimate:** ~3 weeks for Phases 0-6 (foundation), then Phases 7+ for revenue path.

---

## 6. RISK MATRIX

| Risk | Likelihood | Severity | Mitigation |
|------|------------|----------|------------|
| Schema migrations break existing data | Low | Medium | Pre-flight backup + rollback SQL |
| PENDING completer floods teacher API | Medium | Low | Rate limit + cost cap |
| Owner data path = security hole (PII upload) | Medium | High | RLS + audit log + admin-only endpoint |
| KTO loss not implemented well first time | Medium | Medium | Smoke test on 10 pairs before full |
| Replay buffer dilutes new signal | Low | Medium | Tunable mix ratio, eval per ratio |
| Cycle 8 still fails like 4-7 | Medium | Medium | Different methodology (multi-loss + replay) breaks pattern |
| Beta users abandon = no real data | Medium | High | Active prompt during onboarding, "thumbs help me learn" |

---

## 7. DECISION POINTS (need owner input)

### D1: Pathway priority order
- Option A: Build all 4 pathways in parallel (fast but scattered)
- Option B: Sequential: Owner → User → Teacher → Self (deliberate)
- Option C: User + Owner first (immediate signal), Teacher continuous, Self last
- **Saya rekomendasi: C** — user feedback paling murah dan langsung beri sinyal

### D2: Loss function strategy
- Option A: Stick with ORPO, fix data quality (lessons say wrong tool)
- Option B: SFT-only for everything (simpler, slower convergence)
- Option C: **Multi-loss arsenal** — SFT for identity, DPO for prefs, KTO for thumbs
- **Saya rekomendasi: C** — different problem types need different tools

### D3: Replay buffer ratio
- Option A: 50/50 old/new (safe, slow progress)
- Option B: 30/70 old/new (balanced)
- Option C: 10/90 old/new (aggressive, regression risk)
- **Saya rekomendasi: B (30/70)** — Cycle 3 stable foundation + new signal

### D4: Identity reinforcement timing
- Option A: First (fix Lesson #170 BEFORE other work)
- Option B: After data pipeline (test new pipeline first)
- Option C: Skip until needed (white-label phase)
- **Saya rekomendasi: A** — without solid identity, white-label doesn't work

### D5: Phase 7 (white-label/clone) timing
- Option A: Right after Phase 4 (skip beta data collection)
- Option B: After Phase 6 (Cycle 8 success first)
- Option C: Parallel with Phase 5 (someone else builds while training)
- **Saya rekomendasi: B** — solid brain first, then clone confidently

---

## 8. WHAT THIS DELIVERS (vs current state)

| Capability | Day 71d | After Phase 1-6 |
|-----------|---------|-----------------|
| Real user signal flowing | 1 pair total | Continuous |
| Owner data ingestion | None | 4 endpoints + UI |
| Teacher distillation | One-shot | Continuous 6h cycles |
| Self-growth loop | 50% idle | 100% sample + self-play |
| Loss tools available | ORPO only | SFT, DPO, KTO, ORPO, SimPO |
| Dataset versioning | JSONL files | DB lineage tracked |
| Training run history | None | Full table |
| Replay buffer | None | 30/70 mix per cycle |
| Identity stability | Fragile (SOUL-dep) | Solid (SFT-trained) |
| Active learning | None | Uncertainty sampling |
| Auto-rollback | Manual | Service |

---

## 9. APAKAH INI SELARAS DENGAN VISI?

Cross-check against `VISION_PRINCIPLES_LOCKED.md`:

| Principle | This Plan | Aligned? |
|-----------|-----------|----------|
| 1. Migan = STANDING ALONE BRAIN | Multi-loss = own training, no API runtime dependency | ✅ |
| 2. Teacher API = MENTOR not RESPONDER | Teacher in distillation only, never live response | ✅ |
| 3. Own tools, not 3rd party SDK | Custom curator, custom dataset builder | ✅ |
| 4. Self-improving via closed loop | 4 pathways → curator → train = the FLYWHEEL | ✅ |
| 5. Speed via better local model, not wrapper | Multi-loss = better convergence per cycle | ✅ |

Cross-check against brief P1-P9:

| Brief Principle | This Plan |
|----------------|-----------|
| P1. Zero data leak | All pathways tenant-scoped, RLS, owner data stays in client DB | ✅ |
| P2. Self-hosted | All workers run in Docker, no SaaS dep | ✅ |
| P3. Modular clone | Per-tenant data → unique training per ADO instance | ✅ |
| P4. Retrain by owner | Pathway B = owner ingestion = retrain | ✅ |
| P5. Base skills pre-loaded | Cycle 3 baseline preserved via replay | ✅ |
| P6. White-label naming | Phase 7 (after solid foundation) | ⏳ |
| P7. License enforcement | Phase 7 | ⏳ |
| P8. Anti vendor lock-in | Open formats (JSONL, GGUF, HF Hub) | ✅ |
| P9. Trilingual | Schema supports `language` field, EN/ZH Phase 7+ | ⏳ |

---

## 10. RECOMMENDATION TO OWNER

**Saya tidak akan execute apa-apa sebelum kamu approve.** Tapi konkretnya:

1. **APPROVE arsitektur ini** sebagai foundation (4 pathway + multi-loss + lineage)
2. **DECIDE D1-D5** decision points di Section 7
3. **GO untuk Phase 1** (Data Pipeline Plumbing) — 2 hari, low-risk, foundation work
4. Kimi + Codex review document ini parallel

Kalau approve, saya mulai Phase 1 esok hari dengan disiplin:
- 1 commit per sub-phase
- Test setiap migration
- Document setiap design decision
- TIDAK iterasi training cycle baru sampai Phase 4

---

>> **Owner:** Decide on D1-D5 + APPROVE/REJECT/MODIFY architecture proposal.
>> **Kimi:** Review research + loss function matrix. Suggest improvements.
>> **Codex:** QA schema migrations + RLS + tenant isolation correctness.
>> **Claude:** Awaiting all reviews before executing Phase 1.
