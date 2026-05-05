# RESUME CHECKPOINT — Day 49 Pre-Flight Complete → Day 50 Onwards
**Created:** 2026-05-05 (end Day 49 pre-flight session)
**For:** Any agent or engineer resuming this project
**Read-time:** 5 minutes
**Version anchor:** API **v0.5.16**, last commit `d2cb0f5`

> **ONE-PARAGRAPH TL;DR.** MiganCore is at v0.5.16, fully QA-clean (Day 48 closed all 6 known bugs), with `services/contracts.py` boot validator + watchdog active (Day 47 meta-pattern). The original 30-day blueprint promised "Seed Alive + Self-Improving v1" — Seed is alive, but **Cycle 1 SimPO has never actually run**. Day 49 staged it: 596 DPO pairs exported, 3 research-validated hyperparameter refinements applied to `training/train_simpo.py`, identity eval baseline ready, hot-swap framework ready. **The single next action is user GO/NO-GO for triggering Cycle 1 on RunPod ($0.15-0.50, ~25 min, $7 hard cap).** Once PROMOTED, MiganCore becomes the first ADO with a self-improved checkpoint that survives a model swap — proves the entire vision.

---

## 🟢 IF YOU'RE RESUMING COLD — DO THESE 4 THINGS FIRST

1. **Read this file (you're here).** Skip the rest below if you only need TL;DR.
2. **Read `docs/VISION_DISTINCTIVENESS_2026.md`** (3 real moats, STOP/DOUBLE DOWN, Bold Move). The strategic compass.
3. **Read `docs/AGENT_HANDOFF_MASTER.md`** (530 lines, comprehensive single source of truth Day 1-47).
4. **Read `docs/DAY49_PREFLIGHT_RETRO.md`** (full pre-flight report + USER ASK).

After those 4, run `git log --oneline -20` to see latest commits and `curl https://api.migancore.com/health` to verify production state matches what's documented here.

---

## 🎯 THE ONE IMMEDIATE NEXT ACTION

**A2 — Trigger Cycle 1 SimPO on RunPod**

| Field | Value |
|-------|-------|
| Cost | $0.15-0.50 (Unsloth Docker on RTX 4090 spot) |
| Time | 15-25 min wall-clock |
| Output | `migancore-7b-soul-v0.1` adapter |
| Validates | "Self-Improving" half of original 30-day vision |
| Failure mode | Identity drift >0.85 → ROLLBACK, no production change |
| Pre-reqs | ✅ ALL READY (see "Pre-Flight Status" below) |
| Blocker | User explicit GO (financial decision — RunPod credit) |

**Trigger command (when GO):**
```bash
# 1. SSH to VPS
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6

# 2. Verify dataset still exists in container
docker exec ado-api-1 ls -la /app/workspace/cycle1_dataset.jsonl
# expected: ~1.24MB, 596 lines

# 3. Spawn RunPod pod via API (replace POD_ID)
# Use credentials from memory/credentials_private.md (RunPod API key)
# Image: unslothai/unsloth:latest (or runpod/pytorch:2.4.0-py3.11-cuda12.1.1)
# GPU: RTX 4090 spot (~$0.34/hr)

# 4. Upload dataset + run training
runpodctl send <local_dataset> POD_ID:/workspace/
ssh root@POD_IP "
cd /workspace && \
pip install unsloth trl transformers datasets peft accelerate bitsandbytes && \
git clone https://github.com/tiranyx/migancore.git && \
python migancore/training/train_simpo.py \
  --dataset /workspace/cycle1_dataset.jsonl \
  --base-model Qwen/Qwen2.5-7B-Instruct \
  --output-dir /workspace/migancore-7b-soul-v0.1 \
  --use-apo --anchor-dataset migancore/eval/persona_consistency_v1.jsonl \
  --padding-free --use-liger-kernel
"

# 5. Download adapter + identity eval
runpodctl send POD_ID:/workspace/migancore-7b-soul-v0.1 ./
python eval/run_identity_eval.py --adapter ./migancore-7b-soul-v0.1 \
  --baseline eval/baseline_day39.json --embedding bge-m3

# 6. PROMOTE if mean ≥0.85 AND min ≥0.75 → GGUF + Ollama hot-swap
```

---

## 📊 CURRENT STATE SNAPSHOT (verified end Day 49)

| Item | Value |
|------|-------|
| API version | **v0.5.16** healthy |
| Last commit | `d2cb0f5` (docs/DAY49_PREFLIGHT_RETRO) |
| Containers | 6/6 UP (api, ollama, postgres, qdrant, redis, letta) |
| **DPO pool** | **601** (passed 500 gate by 101) |
| Synthetic gen | Running (autonomous-resume verified Day 45) |
| Cycle 1 status | **STAGED — awaiting user GO** |
| RunPod saldo | $16.17 intact ($7 hard cap for Cycle 1) |
| Bulan 2 spend | **$1.44 / $30 (4.8%)** |
| Tools live | 21 (registered) / 13 (assigned to core_brain) |
| Contracts boot | `boot.ok handlers=19 schemas=19` ✓ balanced |
| Lessons cumulative | **53** |
| Strategic docs | 12 (in `docs/`) |
| Day-progress notes | 13 (in `memory/`) |

---

## ✅ PRE-FLIGHT STATUS (Day 49 A1) — All GREEN

| Check | Status | Detail |
|-------|--------|--------|
| `docs/DAY49_PLAN.md` | ✅ | Research-validated H/R/B + KPIs |
| `docs/DAY49_PREFLIGHT_RETRO.md` | ✅ | Full pre-flight report + USER ASK |
| `training/train_simpo.py` refinements | ✅ | lr 8e-7→**5e-7**, +`--padding-free`, +`--use-liger-kernel` (graceful degrade if older TRL) |
| DPO export | ✅ | 596 pairs at `/app/workspace/cycle1_dataset.jsonl` (1.24MB, TRL-compatible) |
| Identity baseline | ✅ | `eval/baseline_day39.json` 15524 lines |
| Persona probes | ✅ | `eval/persona_consistency_v1.jsonl` 20 prompts × 8 categories |
| Hot-swap framework | ✅ | `training/convert_gguf.py` + `scripts/adoctl` |
| RunPod creds | ✅ | In `memory/credentials_private.md` (PRIVATE) |
| Budget cap | ✅ | $7 Cycle 1 hard cap; estimated $0.15-0.50 actual |

---

## 🗺️ FORWARD MAPPING (Day 50-65) — Per Vision Compass

### Branch A — IF user gives GO + Cycle 1 PROMOTES
**Day 50 (immediate):** GGUF convert + Ollama hot-swap to `migancore:0.1` + A/B 10% traffic.
**Day 51-52:** 24h A/B win-rate eval vs base Qwen. Decide PROMOTE/ROLLBACK to 100%.
**Day 53-55:** Hot-swap public eval demo (DD-2 from VISION compass — unfakeable proof of "modular brain"). Same SOUL.md, 3 different base models preserving identity benchmarks. Public GitHub eval harness.
**Day 56-58:** Sleep-time consolidator (Letta v0.5 pattern). Cron 03:00 daily: pull last 24h messages → CAI quorum extracts durable facts → semantic_memory Qdrant collection.
**Day 59-65:** ⭐ **Dream Cycle prototype (Innovation #4 — bold move).** Adversarial self-critique generates counterfactual episodes; SimPO trains on synthetic experience the model never lived. **No public 2026 ADO does this.** All components exist already.

### Branch B — IF user gives GO + Cycle 1 ROLLS BACK
**Day 50:** Post-mortem (likely culprits: lr too high, dataset too noisy, anchor too weak).
**Day 51:** Cycle 1.1 with lr=3e-7 + cleaned dataset (drop synthetic with judge_score <2). Re-trigger.
**Day 52+:** Same as Branch A from this point.

### Branch C — IF user says WAIT
**Day 50:** No state change. Standby preserved. Possible Day 50 work:
- QA Sprint 3 (refresh-token cookie [H3], X-FF nginx [H6]) — defense-in-depth
- Sleep-time consolidator scaffolding (no Cycle 1 dependency for substrate)
- Beta DM template polish

---

## 🔑 KEY FILES TO READ (priority order)

### Strategic compass
1. `docs/VISION_DISTINCTIVENESS_2026.md` — THE one-sentence positioning + 3 moats + STOP/DOUBLE DOWN + Dream Cycle bold move
2. `docs/ROADMAP_BULAN2_BULAN3.md` — Day 41-95 day-by-day mapping
3. `docs/RECAP_DAY36-41.md` — cumulative recap with REPEAT/AVOID lessons

### Latest sprint state (Day 47-49)
4. `docs/AGENT_HANDOFF_MASTER.md` — comprehensive single source of truth (530 lines)
5. `docs/DAY49_PLAN.md` — Cycle 1 plan with H/R/B
6. `docs/DAY49_PREFLIGHT_RETRO.md` — pre-flight report + USER ASK
7. `docs/DAY48_QA_CLOSEOUT.md` — 6 fixes for seamless production
8. `docs/DAY47_RETRO.md` — meta-pattern Contract Assertions + 5-dim QA
9. `docs/QA_FULLREVIEW_2026-05-05.md` — 65-issue catalog (Sprint 2 backlog)

### Per-day memory (anti-context-loss)
10. `~/.claude/projects/C--migancore/memory/MEMORY.md` — index of all day progress
11. `~/.claude/projects/C--migancore/memory/day{36-49}_progress.md` — per-day notes

### Original IDE (vision source)
12. `C:\migancore\compass_artifact_wf-...md` — full ID-Bahasa blueprint
13. `C:\migancore\Autonomous Digital Organism_ 30-Day Blueprint...pdf` — original PDF
14. `C:\migancore\migancore-kickoff.html` — original kickoff doc

---

## 🧠 CRITICAL LESSONS (53 cumulative — top 5 to internalize before resuming)

**#48 — Tool-registration drift between layers is silent and lethal.** `skills.json` (executor) vs `agents.json` (per-agent) sync drifted over Day 41-44. Fixed Day 46 + Day 47 contracts module. Every new tool/handler MUST be checked against ALL agent assignments.

**#51 — Design by Contract for LLM Agents.** ONE module (`services/contracts.py`) addresses 4 historical bug classes (Day 39/44/45/46) via runtime invariant assertions. Pattern: boot-time validators + safe_task wrapper + TaskRegistry watchdog + output contracts. Caught its own regression in <60s on first deploy.

**#45 — In-process background tasks die with container.** EVERY async task that should outlive deploy needs (a) state persistence in Redis/DB, (b) auto-resume in lifespan, (c) deploy-checklist entry. Day 44 deploy silently killed DPO flywheel for 14h.

**#50 — Brain confusion = empty output (worst failure mode).** Qwen2.5-7B emits ZERO when tool description references unavailable alternative. Tool descriptions must NEVER reference unavailable alternatives. Either both exist OR drop the deprecation note.

**#47 — Vision doc as compass beats roadmap as schedule.** `VISION_DISTINCTIVENESS_2026.md` gives STOP list + DOUBLE DOWN + Dream Cycle bold move. Roadmap derives from vision, not parallel.

---

## 🛡️ ANTI-PATTERNS (DON'T)

1. **Don't add more wrapper tools** (Cline ships these weekly — STOP per VISION compass)
2. **Don't polish chat UI further** (Open WebUI 50k stars — STOP)
3. **Don't add generic memory features** (mem0 raised $25M — STOP)
4. **Don't deploy without `git pull` + commit-log-scan first** (parallel session coordination — Lesson #53)
5. **Don't skip mandatory protocol** (research-first → H/R/B → KPIs → execute → retro → memory close-out)
6. **Don't run `docker compose up -d --build api` while synthetic gen running** without verifying auto-resume fires (Lesson #45)

---

## 🎯 RESUME CHECKLIST

When you resume next session, in this order:

```
[ ] curl https://api.migancore.com/health  → expect "v0.5.16"
[ ] curl https://api.migancore.com/v1/public/stats  → expect total_pairs ≥601
[ ] git pull origin main  → check for new commits since d2cb0f5
[ ] git log --oneline -20  → see what's happened (parallel sessions)
[ ] Read this file (RESUME_DAY49_TO_DAY50.md)
[ ] Read VISION_DISTINCTIVENESS_2026.md (3 moats refresh)
[ ] Check user message for GO/WAIT signal on Cycle 1
[ ] If GO → execute A2 trigger sequence above + update todos
[ ] If WAIT → pick from Branch C alternative work
[ ] Update day-progress + retro at session end
```

---

## 💰 BUDGET STATE (anti-overspend guardrail)

| Pool | Cap | Spent | Remaining |
|------|-----|-------|-----------|
| Bulan 2 API costs | $30 | $1.44 | $28.56 (95%) |
| RunPod Cycle 1 | $7 | $0 | $7 |
| RunPod Cycle 2 | $7 | $0 | $7 |
| RunPod emergency | $2 | $0 | $2 |
| RunPod total saldo | $16.17 | $0 | $16.17 |

**Cycle 1 estimated $0.15-0.50.** Even worst case = 7% of Cycle 1 cap, 3% of total saldo.

---

## 📞 USER PROFILE QUICK REFERENCE

- **Fahmi Wol** (tiranyx.id@gmail.com) — non-technical founder/visioner
- **Concept:** iterasi → kognitif → optimasi → inovasi
- **Wants:** comprehensive docs, no context loss across multi-agent sessions, partner-honest assessment, research-first execution, mandatory protocol always
- **Other projects on same VPS:** SIDIX, Ixonomic, Mighantect3D
- **Communication style:** Bahasa Indonesia primary, English for technical context

---

## 🏁 BREAK STATE — END Day 49 PRE-FLIGHT

**Everything is committed + pushed. Production stable v0.5.16. Synthetic gen running. DPO 601 + growing. Cycle 1 STAGED. Awaiting user GO.**

**The Aha Moment is one user GO away.**

> *"Treat every async boundary, every LLM output, and every config relationship as a contract — and assert the contract at runtime, not in code review."* — Lesson #51, validated by Day 47 contracts module catching its own regression in <60s.
