# MEMORY.md — MiganCore Context Index
**Version:** 1.0 | **Date:** 2026-05-07 | **Updated by:** Kimi Code CLI

> **Purpose:** Anti-context-loss index. Setiap agent baru membaca ini untuk memahami
> history dan menemukan detail per-hari tanpa tersesat di 140+ dokumen.

---

## QUICK STATE (Day 67)

| Item | Value |
|------|-------|
| Day | 67 |
| Phase | Cycle 6 training on Vast.ai (ORPO, 954 pairs) → PROMOTE/ROLLBACK pending |
| Production Brain | migancore:0.3 (Cycle 3, weighted_avg 0.9082) |
| Cycle 6 Status | Training complete → post_cycle6.sh auto-trigger pending |
| API Version | v0.5.16 LIVE (Day 67 fixes in GitHub, deploy pending SSH) |
| Beta Status | 53 users, 65 conversations, 0 feedback signals (fixing now) |
| DPO/ORPO Pairs | 3,004 |
| Lessons Documented | 144 (#138-144 today) |
| GPU Budget | Vast.ai total ~$0.80, RunPod $6.80 spent |
| VPS Main | 72.62.125.6 — MiganCore + Ixonomic + SIDIX (merged) |
| SSH Status | SSH port 22 blocked from Windows env — use VPS terminal |
| GitHub | Commit f80bb58 — deploy cmd: cd /opt/ado && git pull && docker compose build api && docker compose up -d api |

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
| 65 | Cycle 5 PROMOTE (0.8453) → migancore:0.5 candidate | — | — | MEMORY.md |
| 67 | Cycle 6 training launched + frontend fixes | `docs/DAY67_MANDATORY_PROTOCOL.md` | — | `docs/ACHIEVEMENT_WRAP.md` |

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
| 121–130 | License system, clone mechanism, gate thresholds single source |
| 131–144 | Voice/evo seed dedup, SSH timeout, break vs continue monitoring loop |

---

## WHERE TO FIND CURRENT WORK

| Need | File |
|------|------|
| Today's plan | `docs/DAY67_MANDATORY_PROTOCOL.md` |
| Current status | `docs/ACHIEVEMENT_WRAP.md` (milestone-based, Day 1-67) |
| All lessons | `docs/AGENT_ONBOARDING.md` (lessons #1-137) |
| VPS safety | `docs/ENVIRONMENT_MAP.md` |
| Vision compass | `docs/VISION_2026_2027_COGNITIVE_TRENDS.md` |
| Resource audit | `docs/RESOURCE_AUDIT_DAY67.md` |
| Qwen3 upgrade | `docs/QWEN3_UPGRADE_PLAN.md` |

### New Lessons Day 67 (#138-144)
- **#138**: nohup fork verification — `ps aux | grep [script]` after every nohup launch, kill duplicate
- **#139**: Vast.ai duplicate instance = ganda cost. Kill dalam <5 menit = $0 wasted
- **#140**: Gate thresholds single source of truth — mismatch = false rollback atau false promote
- **#141**: dry_run=True pattern mandatory untuk setiap deploy script yang touch client VPS
- **#142**: Baca function signature sebelum integrate, jangan asumsi class interface
- **#143**: SSH timeout harus melebihi training time (training 3.5hr → timeout ≥ 7200s minimum)
- **#144**: `break` vs `continue` di monitoring loop — `break` = silent stop, audit setiap exit point
- **#145 (Day 67 frontend)**: thumbs_up feedback was no-op (returned 200 but stored nothing) — always verify DB write with a SELECT after first feedback test
- **#146 (Day 67 frontend)**: Hardcoded static strings in React (model label, streaming status) = invisible bugs. Always use state vars fetched from API

### New Lessons Day 65 (#131-133)
- **#131**: Voice/evo seed dedup — seed pool size must ≥ target pairs (30 seeds × 4 repeats = 30 unique only)
- **#132**: NEVER `scp -r` full adapter dir — only SCP adapter_model.safetensors + adapter_config.json (checkpoints = 700MB+)
- **#133**: Ollama using all 8 cores → hypervisor throttle → 93.8% steal → inference 16x slower than expected. Fix: `OLLAMA_NUM_THREAD: "4"` + `cpus: "4.0"` in docker-compose. 4 dedicated cores faster than 8 throttled.
- **#134**: Never assume CPU hog = external tenant. Always trace PID → parent → container. MiganCore container Ollama (ado-ollama-1) was 349% CPU, not SIDIX. Investigation: `ps -ef` → `docker ps --no-trunc | grep <container-id>` → confirm ownership.

### Day 65 Events
- **Cycle 5 ORPO training COMPLETE** on Vast.ai (877 pairs, 17.9min, RTX 5880 Ada, train_loss 2.5103)
- **Cycle 5 EVAL PROMOTE** — weighted_avg 0.8453 (threshold 0.8), identity 0.938, voice 0.895 ✅
- **3× Ollama 500 errors** discovered during eval (prompts #3, #7, #12) — LoRA compatibility issue
- **SIDIX CPU contention investigation** — ternyata BUKAN SIDIX, tapi MiganCore container Ollama (349% CPU)
- **Hostinger KVM 4 DEPLOYED** (187.77.116.139) — SIDIX stack live
- **SIDIX migrated** dari VPS existing → VPS baru — host Ollama stopped & disabled
- **sidix-lora model** recreated & tested di VPS baru — inference responding
- **Migration scripts**: `vps-sidix-setup.sh`, `docker-compose.sidix.yml`, `SIDIX_MIGRATION_PLAN.md`
- SCP timeout bug FIXED in cycle5_orpo_vast.py (Lesson #132)
- Stuck Ollama runner (692% CPU) discovered and killed → VPS recovered
- Ollama 4-core cap deployed (OLLAMA_NUM_THREAD=4, cpus:4.0) → steal 93.8%→29%
- Cycle 5 adapter uploaded to HF: `Tiranyx/migancore-7b-soul-v0.5`
- Vision doc written: `docs/VISION_2026_2027_COGNITIVE_TRENDS.md`
- Ollama runner watchdog cron created (`*/15 * * * *`)

---

## PROTOCOL REMINDER

Setiap akhir sesi, update file ini jika ada perubahan signifikan:
- Day baru selesai → tambahkan ke Per-Day Index
- Lesson baru → tambahkan ke Lesson Clusters
- Milestone tercapai → update Quick State

---

*This file is LIVING. Update it. Don't let it rot.*
