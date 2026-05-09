# SPRINT Day 71-90: BRAIN UNSTUCK — Identity Anchor + Data Pipeline
**Status:** ACTIVE SPRINT  
**Start:** Day 71 (2026-05-09)  
**End:** Day 90 (2026-05-28)  
**Goal:** Brain tidak lagi stuck. Identity terbentuk. Data pipeline mengalir otomatis.

---

## I. OBJECTIVE UTAMA

1. **Identity Anchor SFT** — 200 pairs, rank 32, cosine sim > 0.85
2. **Data Pipeline Auto** — 4 pathways jalan tanpa trigger manual
3. **Eval Gate Automated** — PASS/FAIL deterministic, no human in loop
4. **Anti-Regression** — Test suite > 60%, no deploy tanpa test pass

---

## II. DAY-BY-DAY BREAKDOWN

### Week 1: Foundation Hardening (Day 71-77)

| Day | Task | Owner | Done Criteria | Status |
|---|---|---|---|---|
| 71 | Generate 200 identity SFT pairs | Chief Engineer | `identity_sft_200.jsonl` valid, 200 examples | ✅ DONE |
| 71 | Write `train_sft_identity.py` | Chief Engineer | Script ready, verified syntax | ✅ DONE |
| 71 | Commit docs: Brain Stuck Analysis + Sprint Plan | Chief Engineer | 4 files committed, pushed | ✅ DONE |
| 72 | Run SFT training (Identity Anchor) | Training Agent | Adapter output, eval report | ⬜ PENDING |
| 72 | Identity eval: cosine sim test | QA Agent | Score > 0.85? | ⬜ PENDING |
| 73 | If pass: convert GGUF, deploy to Ollama staging | DevOps Agent | Staging model serves | ⬜ PENDING |
| 73 | If fail: adjust rank/epochs, retrain | Training Agent | New adapter, re-eval | ⬜ PENDING |
| 74 | A/B test: 10% traffic to new model | Backend Agent | Metrics logged, no error spike | ⬜ PENDING |
| 75 | Monitor 24h: latency, error rate, identity consistency | QA Agent | No regression vs baseline | ⬜ PENDING |
| 76 | If 24h OK: promote to 100% | DevOps Agent | Production model updated | ⬜ PENDING |
| 77 | Week 1 retro: document lessons, update ADR | Docs Agent | Retro doc committed | ⬜ PENDING |

### Week 2: Data Pipeline + Voice (Day 78-84)

| Day | Task | Owner | Done Criteria | Status |
|---|---|---|---|---|
| 78 | Fix self-growth pipeline (CAI critique auto-loop) | Core Agent | 20+ pairs/hari generated | ⬜ PENDING |
| 79 | Build owner data pathway (5 endpoints) | Backend Agent | Upload/annotate/convert working | ⬜ PENDING |
| 80 | Automate teacher distillation (cron, $5/day cap) | Training Agent | 50+ pairs/hari, cost tracked | ⬜ PENDING |
| 81 | Data curator engine (MTLD + dedup) | Core Agent | Diversity score, duplicate detection | ⬜ PENDING |
| 82 | Generate 200 voice SFT pairs | Chief Engineer | `voice_sft_200.jsonl` ready | ⬜ PENDING |
| 83 | Run voice SFT training | Training Agent | Voice match > 0.80 | ⬜ PENDING |
| 84 | Week 2 retro + data quality review | Docs Agent | Real-data ratio reported | ⬜ PENDING |

### Week 3: Tool Mastery + General Quality (Day 85-90)

| Day | Task | Owner | Done Criteria | Status |
|---|---|---|---|---|
| 85 | Generate 100 tool SFT + 200 tool DPO pairs | Chief Engineer | Dataset ready | ⬜ PENDING |
| 86 | Run tool training (SFT + DPO) | Training Agent | Tool accuracy > 80% | ⬜ PENDING |
| 87 | Build 500 general chat SimPO pairs (real data ≥ 50%) | Core Agent | Dataset curated | ⬜ PENDING |
| 88 | Run SimPO training | Training Agent | Judge score improve vs baseline | ⬜ PENDING |
| 89 | Full regression test + identity check | QA Agent | All gates pass | ⬜ PENDING |
| 90 | Sprint retro + Day 90 demo | Project Owner | Demo recorded, metrics presented | ⬜ PENDING |

---

## III. BENCHMARKS PER DAY

| Metric | Day 71 | Day 77 | Day 84 | Day 90 | Target |
|---|---|---|---|---|---|
| Identity cosine sim | N/A | > 0.85 | > 0.85 | > 0.85 | ✅ |
| Real-data ratio | 1% | 10% | 20% | 35% | ⬆️ |
| Pairs/day (total) | 0.5 | 20 | 50 | 70 | ⬆️ |
| Test coverage | 5% | 30% | 50% | 60% | ⬆️ |
| Tool-use accuracy | 60% | 60% | 75% | 80% | ⬆️ |
| API uptime | 99.5% | 99.5% | 99.5% | 99.5% | ✅ |

---

## IV. RISK & MITIGATION

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| SFT identity < 0.85 | Medium | High | Increase rank to 64, or full fine-tune |
| Real-data still low | Medium | High | Increase teacher budget, recruit beta users |
| Tool training unstable | Low | Medium | More SFT patterns, fix schema |
| Voice training overfits | Low | Medium | Reduce epochs, add general data 5% |

---

## V. DAILY PROTOCOL

**Setiap hari pukul 08:00 WIB:**
1. Baca `CONTEXT.md` + `SPRINT_DAY71_90.md`
2. Cek dashboard: API health, data pipeline metrics
3. Jalankan task hari ini
4. Commit dengan message jelas (WHY, not just WHAT)
5. Update `docs/logs/daily/DAY_XXX.md`

**Setiap hari pukul 20:00 WIB:**
1. Review progress vs plan
2. Blocker? → escalate ke owner
3. Update benchmark metrics
4. Push ke GitHub

---

*Gas. Lanjut. Jangan re-pivot.*
