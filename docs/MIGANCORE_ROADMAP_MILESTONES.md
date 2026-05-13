# MIGANCORE — ROADMAP & MILESTONES 2026
**Living Document | Update Setiap Minggu**
**Versi:** 1.0 | **Tanggal:** 2026-05-08

---

## Current North Star Ping - M1.6 Dev Organ

As of 2026-05-14, roadmap execution must include Dev Organ self-improvement:
observe -> diagnose -> propose -> sandbox patch -> test -> iterate -> validate
-> promote -> monitor -> learn.

Canonical references:

- `docs/SELF_IMPROVEMENT_NORTHSTAR.md`
- `docs/M16_DEV_ORGAN_PROGRESS_2026-05-14.md`
- `api/services/dev_organ.py`

Milestones touching tools, training, deployment, memory, auth, license, tenant
isolation, or agent behavior must define risk level, validation gates, and
rollback plan before promotion.

---

## VISUAL ROADMAP

```
2026 ──────────────────────────────────────────────────────────────►
     Q2 (Apr-Jun)          Q3 (Jul-Sep)          Q4 (Oct-Dec)
     ├─ Foundation ─┤      ├─ Scale ─┤           ├─ Grow ─┤
     │              │      │         │           │        │
  ┌──┴──┐ ┌──┴──┐ ┌─┴─┐  ┌┴┐ ┌─┴─┐ ┌┴┐        ┌┴┐ ┌─┴─┐ ┌┴┐
  │P0   │ │P1   │ │P2 │  │P3│ │P4 │ │P5│        │P6│ │P7 │ │P8│
  │Infra │ │Data │ │ID │  │β │ │Clone│ │Rev│        │Open│ │Mkt │ │Int │
  │Harden│ │Pipe │ │Anchor│ │  │     │ │    │        │Src │ │plce│ │l  │
  └─────┘ └─────┘ └───┘  └──┘ └───┘ └──┘        └──┘ └───┘ └──┘
  
  P0 = Foundation Hardening      (Minggu 1-2)
  P1 = Data Pipeline             (Minggu 2-3)
  P2 = Identity Anchor SFT       (Minggu 4)
  P3 = Beta Data Collection      (Minggu 5-6)
  P4 = Clone & White-Label       (Minggu 7-8)
  P5 = Revenue Path              (Minggu 9-12)
  P6 = Open Source Core          (Q4 2026)
  P7 = Marketplace MVP           (Q4 2026)
  P8 = International (EN/ZH)     (Q4 2026)
```

---

## MILESTONE DEFINITIONS

Setiap milestone punya **Definition of Done (DoD)** yang jelas. Tidak boleh celebrate sebelum DoD tercapai.

---

### 🏁 MILESTONE 0: FOUNDATION HARDENING
**Target:** 2026-05-22 (2 minggu)
**Budget:** $0 (local development only)

| # | Deliverable | DoD | Owner | Status |
|---|---|---|---|---|
| M0.1 | Alembic migrations | `alembic upgrade head` pass, all patches converted | Backend Agent | ⬜ |
| M0.2 | Test suite v1 | ≥ 50 tests, pytest pass 100%, coverage ≥ 40% | QA Agent | ⬜ |
| M0.3 | CI/CD pipeline | GitHub Actions: test → build → deploy staging | DevOps Agent | ⬜ |
| M0.4 | Context preservation protocol | Daily log template, agent handoff template, CONTEXT.md auto-update | Docs Agent | ⬜ |
| M0.5 | Observability stack | Prometheus metrics + Grafana dashboard + alerting | DevOps Agent | ⬜ |

**Success Criteria:**
- [ ] Setiap PR ke main otomatis tested dan deployed ke staging
- [ ] Tidak ada schema change tanpa migration
- [ ] Context loss = 0 incident

**Blockers:** None

---

### 🏁 MILESTONE 1: DATA PIPELINE (4 Pathways)
**Target:** 2026-05-29 (1 minggu)
**Budget:** $35 (teacher distillation: $5/day × 7 hari)

| # | Deliverable | DoD | Owner | Status |
|---|---|---|---|---|
| M1.1 | User feedback fix | Thumbs up/down → preference_pairs dalam < 1 jam | Backend Agent | ⬜ |
| M1.2 | Owner data pathway | 5 endpoints upload/annotate/convert/preview/list | Backend Agent | ⬜ |
| M1.3 | Self-growth pipeline | CAI auto-loop, 100% sample, ≥ 20 pairs/hari | Core Agent | ⬜ |
| M1.4 | Teacher distillation | Continuous 6h cycle, $5/day cap, ≥ 50 pairs/hari | Training Agent | ⬜ |
| M1.5 | Data curator | MTLD scoring, dedup, diversity filter | Core Agent | ⬜ |

**Success Criteria:**
- [ ] Real-data ratio ≥ 20% (dari 1% sekarang)
- [ ] 4 pathways semua punya dashboard status
- [ ] Data quality score (judge_avg) ≥ 0.7 untuk semua new pairs

**Blockers:** M0 complete

---

### 🏁 MILESTONE 2: MULTI-LOSS TRAINING ENGINE
**Target:** 2026-06-05 (1 minggu)
**Budget:** $0 (local script development)

| # | Deliverable | DoD | Owner | Status |
|---|---|---|---|---|
| M2.1 | SFT pipeline | `train_sft.py` runnable, support identity + voice | Training Agent | ⬜ |
| M2.2 | DPO pipeline | `train_dpo.py` runnable, clean preference pairs | Training Agent | ⬜ |
| M2.3 | KTO pipeline | `train_kto.py` runnable, user thumbs direct | Training Agent | ⬜ |
| M2.4 | SimPO/ORPO refactor | Batasi untuk chat general, remove from voice/identity | Training Agent | ⬜ |
| M2.5 | Dataset builder v2 | Replay 30/70, curriculum sort, anchor samples immutable | Training Agent | ⬜ |
| M2.6 | Eval gate automation | pytest suite: identity + tool-use + regression | QA Agent | ⬜ |

**Success Criteria:**
- [ ] Bisa pilih loss method dari single command: `python train.py --method sft`
- [ ] Eval gate deterministic: same input = same PASS/FAIL
- [ ] Dataset builder versioned: output hash identical for same seed

**Blockers:** M1 complete

---

### 🏁 MILESTONE 3: IDENTITY ANCHOR SFT
**Target:** 2026-06-12 (1 minggu)
**Budget:** $10 (VastAI RTX 4090, 5-8 jam training)

| # | Deliverable | DoD | Owner | Status |
|---|---|---|---|---|
| M3.1 | 200 identity pairs | Generated, reviewed, committed | Training Agent | ⬜ |
| M3.2 | SFT training | Rank 32, 5 epochs, converged | Training Agent | ⬜ |
| M3.3 | Eval without SOUL | 5 fingerprint prompts, cosine sim > 0.85 | QA Agent | ⬜ |
| M3.4 | Regression test | Tool-use ≥ 80%, chat ≥ Cycle 3 baseline | QA Agent | ⬜ |
| M3.5 | Production deploy | Hot-swap Ollama, monitor 24h, no rollback | DevOps Agent | ⬜ |

**Success Criteria:**
- [ ] Model tanpa system prompt jawab "Saya Mighan-Core"
- [ ] Cosine sim > 0.85 untuk semua 5 fingerprint prompts
- [ ] No regression in tool-use, chat quality, latency

**Blockers:** M2 complete

---

### 🏁 MILESTONE 4: BETA DATA COLLECTION
**Target:** 2026-06-26 (2 minggu)
**Budget:** $70 (teacher distillation: $5/day × 14 hari)

| # | Deliverable | DoD | Owner | Status |
|---|---|---|---|---|
| M4.1 | 10 beta users onboarded | Aktif, minimal 10 conversations/user | Owner | ⬜ |
| M4.2 | Data flow dashboard | Real-time: pairs/hari per pathway | Backend Agent | ⬜ |
| M4.3 | Weekly data review | Report: ratio, diversity, quality trend | Core Agent | ⬜ |
| M4.4 | Cycle 8 training | Mixed source, >50% real data, eval PASS | Training Agent | ⬜ |
| M4.5 | Brain quality improve | Weighted_avg > Cycle 3 (0.9082) | QA Agent | ⬜ |

**Success Criteria:**
- [ ] Real-data ratio ≥ 50%
- [ ] Brain quality > Cycle 3 baseline (0.9082)
- [ ] User retention ≥ 70% (7 dari 10 aktif)
- [ ] Zero critical bugs reported by beta users

**Blockers:** M3 complete

---

### 🏁 MILESTONE 5: CLONE & WHITE-LABEL
**Target:** 2026-07-10 (2 minggu)
**Budget:** $0 (local development)

| # | Deliverable | DoD | Owner | Status |
|---|---|---|---|---|
| M5.1 | Clone mechanism E2E | `POST /v1/admin/clone` → instance live < 10 menit | Backend Agent | ⬜ |
| M5.2 | Per-org Docker template | Production-ready, configurable via env | DevOps Agent | ⬜ |
| M5.3 | White-label layer | display_name, logo, persona, language configurable | Backend Agent | ⬜ |
| M5.4 | License enforcement | Startup validator, expired → read-only, revoke → grace 7d | Backend Agent | ⬜ |
| M5.5 | Trilingual base | EN + ZH prompts working, language switcher | Backend Agent | ⬜ |

**Success Criteria:**
- [ ] Clone ADO baru untuk client dalam < 10 menit
- [ ] Client bisa rename jadi "SARI" tanpa merusak license
- [ ] License tidak bisa dihapus/di-circumvent
- [ ] ADO respond dalam EN dan ZH (minimum basic)

**Blockers:** M4 complete

---

### 🏁 MILESTONE 6: REVENUE PATH (First Paying Client)
**Target:** 2026-08-07 (4 minggu)
**Budget:** $200 (marketing, demo, setup fee)

| # | Deliverable | DoD | Owner | Status |
|---|---|---|---|---|
| M6.1 | Landing page trilingual | migancore.com live, ID/EN/ZH, pricing clear | Frontend Agent | ⬜ |
| M6.2 | First client onboarding | Deployed, trained, signed contract | Owner | ⬜ |
| M6.3 | Billing system | Stripe/x402, invoice, tier management | Backend Agent | ⬜ |
| M6.4 | Support system | Ticket, KB, SLA tracking | Backend Agent | ⬜ |
| M6.5 | Case study v1 | Testimonial + metrics dari client pertama | Owner | ⬜ |

**Success Criteria:**
- [ ] 1 client paying ≥ Rp 5 jt/bulan
- [ ] Deployment 100% self-hosted di VPS client
- [ ] Client data tidak pernah keluar dari infrastruktur mereka
- [ ] Testimonial + metrics untuk marketing

**Blockers:** M5 complete

---

## QUARTERLY TARGETS

### Q2 2026 (Apr-Jun): FOUNDATION
**Theme:** Solid infrastructure, identity fixed, beta live.

| Target | Metric | Current | Target Q2 |
|---|---|---|---|
| Brain quality | weighted_avg | 0.9082 (Day 60) | > 0.92 |
| Identity stability | cosine sim (no SOUL) | ~0.3 ("Qwen") | > 0.85 |
| Real-data ratio | % real vs synthetic | 1% | ≥ 50% |
| Test coverage | pytest coverage | ~5% | ≥ 40% |
| Beta users | active users | 0 | 10 |
| Training cycles | successful promotes | 0 since Day 60 | ≥ 1 |

### Q3 2026 (Jul-Sep): SCALE
**Theme:** Clone economy, first revenue, marketplace prep.

| Target | Metric | Target Q3 |
|---|---|---|
| Paying clients | # clients | 3 |
| MRR | Rupiah | ≥ Rp 15 jt |
| ADO instances | # deployed | 10 |
| White-label | # renamed ADOs | 5 |
| Trilingual | languages working | ID + EN + ZH |
| Self-improvement | auto cycles/week | 1 |

### Q4 2026 (Oct-Dec): GROW
**Theme:** Open source, marketplace, international.

| Target | Metric | Target Q4 |
|---|---|---|
| Paying clients | # clients | 7 (break-even) |
| MRR | Rupiah | ≥ Rp 35 jt |
| Open source components | # repos open | 2 (core + memory) |
| Marketplace skills | # available | 10 |
| Community contributors | # active | 5 |
| ARR projection | Year 1 | Rp 500 jt |

---

## BACKLOG (Prioritized)

### 🔴 CRITICAL (M0-M3 blocker)
- [ ] M0.1 Alembic migrations
- [ ] M0.2 Test suite v1
- [ ] M0.3 CI/CD pipeline
- [ ] M1.1 Fix user feedback persistence
- [ ] M1.2 Owner data pathway endpoints
- [ ] M3.3 Identity anchor SFT (cosine > 0.85)

### 🟡 HIGH (M4-M5 blocker)
- [ ] M1.3 Self-growth pipeline auto-loop
- [ ] M1.4 Teacher distillation continuous
- [ ] M2.1 SFT pipeline code
- [ ] M2.6 Eval gate automation
- [ ] M4.1 Beta user onboarding
- [ ] M5.1 Clone mechanism E2E

### 🟢 NORMAL (M6+)
- [ ] M5.5 Trilingual base prompts
- [ ] M6.1 Landing page trilingual
- [ ] M6.3 Billing system
- [ ] Causal AI module (Phase 2+)
- [ ] Active Inference module (Phase 2+)
- [ ] x402 integration (Phase 3+)

### 🔵 IN PROGRESS
- [ ] MIGANCORE_ARCHITECTURE_REMAP_v2026.md (dokumen ini)
- [ ] CONTEXT.md update honest
- [ ] TASK_BOARD.md reorganization

### ✅ DONE (Recent)
- [x] Research 71E — Training Infrastructure Audit
- [x] SIDIX migration complete
- [x] Cycle 3 promote (migancore:0.3)
- [x] Beta launch (Day 51)
- [x] License system (Day 61)

---

## METRICS DASHBOARD (Track Weekly)

```
Week of: [DATE]

BRAIN HEALTH
├── Model version: [migancore:X.X]
├── Weighted avg: [0.XXXX]
├── Identity cosine: [0.XX] (no SOUL)
├── Tool-use accuracy: [XX%]
└── Latency p95: [X.Xs]

DATA PIPELINE
├── Total pairs: [XXXX]
├── Real-data ratio: [XX%]
├── Pairs/day (self): [XX]
├── Pairs/day (owner): [XX]
├── Pairs/day (user): [XX]
├── Pairs/day (teacher): [XX]
└── Avg judge score: [0.XX]

INFRASTRUCTURE
├── Test coverage: [XX%]
├── CI pass rate: [XX%]
├── Uptime: [XX.XX%]
├── API error rate: [X.X%]
└── Cost this week: [$X.XX]

BUSINESS
├── Beta users: [X/10]
├── Paying clients: [X]
├── MRR: [Rp X jt]
└── ADO instances: [X]
```

---

## SPRINT RHYTHM

**Weekly Cycle:**
- **Senin:** Sprint planning, review metrics, set priorities
- **Selasa-Rabu:** Development sprints (focus blocks)
- **Kamis:** Integration + testing
- **Jumat:** Deploy to staging, beta user feedback review
- **Sabtu:** Research + learning (read papers, experiment)
- **Minggu:** Training cycle trigger (02:00 WIB auto), rest

**Daily Protocol:**
1. Baca CONTEXT.md
2. Baca daily log hari ini
3. Cek metrics dashboard
4. Kerja sesuai TASK_BOARD
5. Catat progress di daily log
6. Update CONTEXT.md jika ada keputusan

**Monthly Review:**
1. Review milestone DoD — tercapai atau tidak?
2. Update roadmap jika perlu (dengan approval owner)
3. Budget review: RunPod/VastAI, API costs, VPS
4. Risk register update
5. Decision registry review

---

*Roadmap ini adalah LIVING DOCUMENT. Update setiap minggu. Jangan biarkan outdated seperti sprint roadmap lama yang berhenti di Day 30 padahal code sudah Day 71d.*
