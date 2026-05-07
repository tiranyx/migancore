# MEMORY.md — MiganCore Context Index
**Version:** 1.0 | **Date:** 2026-05-07 | **Updated by:** Kimi Code CLI

> **Purpose:** Anti-context-loss index. Setiap agent baru membaca ini untuk memahami
> history dan menemukan detail per-hari tanpa tersesat di 140+ dokumen.

---

## QUICK STATE (Day 65)

| Item | Value |
|------|-------|
| Day | 65 |
| Phase | Cycle 5 Eval (training done, eval running) |
| Production Brain | migancore:0.3 (Cycle 3, weighted_avg 0.9082) |
| Cycle 5 Candidate | migancore:0.5 (877 pairs ORPO, eval PENDING) |
| API Version | v0.5.19 LIVE |
| Beta Status | Launched Day 51, 3-5 testers |
| DPO/ORPO Pairs | ~2,390+ |
| Lessons Documented | 133 (see AGENT_ONBOARDING.md) |
| GPU Budget | Vast.ai ~$7.06 spent, RunPod $16.69 saldo |
| VPS Ollama | 4-core cap added (OLLAMA_NUM_THREAD=4, cpus:4.0) — Lesson #133 |

---

## PER-DAY INDEX (Sparse — populate as needed)

| Day | Key Event | Plan File | Retro File | Progress File |
|-----|-----------|-----------|------------|---------------|
| 1–5 | VPS setup, scaffold, auth | `docs/DAY4_*` | `docs/DAY0-5_COMPREHENSIVE_REVIEW.md` | — |
| 6–10 | Docker stack, LangGraph, Letta | `docs/DAY*_PLAN.md` | `docs/DAY*_RETRO.md` | — |
| 11–20 | Memory, tools, multi-tenant | `docs/DAY*_PLAN.md` | `docs/DAY*_RETRO.md` | — |
| 21–30 | Self-learning pipeline, training | `docs/DAY*_PLAN.md` | `docs/DAY*_RETRO.md` | — |
| 31–40 | Cycle 1–2 attempts, eval framework | `docs/DAY36_PLAN.md` etc | `docs/DAY36_RETRO.md` etc | — |
| 41–50 | Cycle 3 success, hot-swap, beta prep | `docs/DAY50_PLAN.md` | `docs/DAY50_RETRO.md` | — |
| 51 | **BETA LAUNCH** | `docs/BETA_LAUNCHED_DAY51.md` | — | — |
| 52–55 | Beta iteration, frontend fixes | `docs/DAY5*_PLAN.md` | `docs/DAY5*_RETRO.md` | — |
| 56–60 | Cycle 3 promote, ORPO switch, identity eval | `docs/DAY60_MANDATORY_PROTOCOL.md` | `docs/DAY60_RETRO.md` | — |
| 61–63 | Cycle 4 attempt → ROLLBACK | `docs/DAY63_CYCLE4_ROLLBACK.md` | `docs/DAY62_MANDATORY_PROTOCOL.md` | — |
| 64 | **Cycle 5 prep + Kimi review** | `docs/DAY64_PLAN.md` | — | `docs/DAY64_STATUS_REVIEW_KIMI.md` |

---

## LESSON CLUSTERS (Refer to AGENT_ONBOARDING.md for full detail)

| Range | Theme |
|-------|-------|
| 39–48 | Async, contracts, boot validators |
| 49–53 | Context loss, coordination, parallel sessions |
| 54–56 | VPS shared environment, CPU contention |
| 57–58 | STOP adding tools, scope discipline |
| 59–63 | RunPod/Vast.ai training pipeline, cost discipline |
| 64–70 | Frontend/backend verification, indie launch tactics |
| 71–75 | Inference engine decisions, vendor audit |
| 76–83 | Timezone, RunPod serverless, network volumes |
| 84–88 | Production health > features, coordination |
| 89–93 | SLM revolution, self-improvement, agent economy |
| 94–104 | Identity preservation, eval gates, data curation |
| 105–120 | Training pipeline mastery, ORPO, GGUF LoRA deploy |

---

## WHERE TO FIND CURRENT WORK

| Need | File |
|------|------|
| Today's plan | `docs/DAY64_PLAN.md` (still valid, Day 65 continues) |
| Current status | `CONTEXT.md` (root) |
| Available tasks | `TASK_BOARD.md` (root) |
| Strategic review | `docs/DAY64_STATUS_REVIEW_KIMI.md` |
| All lessons | `docs/AGENT_ONBOARDING.md` |
| VPS safety | `docs/ENVIRONMENT_MAP.md` |
| Vision compass | `docs/VISION_2026_2027_COGNITIVE_TRENDS.md` ← NEWEST (Day 65) |
| Previous vision | `docs/VISION_DISTINCTIVENESS_2026.md` (Day 45) |

### New Lessons Day 65 (#131-133)
- **#131**: Voice/evo seed dedup — seed pool size must ≥ target pairs (30 seeds × 4 repeats = 30 unique only)
- **#132**: NEVER `scp -r` full adapter dir — only SCP adapter_model.safetensors + adapter_config.json (checkpoints = 700MB+)
- **#133**: Ollama using all 8 cores → hypervisor throttle → 93.8% steal → inference 16x slower than expected. Fix: `OLLAMA_NUM_THREAD: "4"` + `cpus: "4.0"` in docker-compose. 4 dedicated cores faster than 8 throttled.

### Day 65 Events
- Cycle 5 ORPO training COMPLETE on Vast.ai (877 pairs, 17.9min, RTX 5880 Ada, train_loss 2.5103)
- SCP timeout bug FIXED in cycle5_orpo_vast.py (Lesson #132)
- Stuck Ollama runner (692% CPU since 04:56) discovered and killed → VPS recovered
- Ollama 4-core cap deployed (OLLAMA_NUM_THREAD=4, cpus:4.0) → steal 93.8%→29%
- Cycle 5 adapter uploaded to HF: `Tiranyx/migancore-7b-soul-v0.5`
- Eval running against 20 prompts with 600s timeout (PENDING result)
- Vision doc written: `docs/VISION_2026_2027_COGNITIVE_TRENDS.md` (7 tren 2026-2027, Fahmi ideas structured)
- Ollama runner watchdog cron created (`*/15 * * * *`)

---

## PROTOCOL REMINDER

Setiap akhir sesi, update file ini jika ada perubahan signifikan:
- Day baru selesai → tambahkan ke Per-Day Index
- Lesson baru → tambahkan ke Lesson Clusters
- Milestone tercapai → update Quick State

---

*This file is LIVING. Update it. Don't let it rot.*
