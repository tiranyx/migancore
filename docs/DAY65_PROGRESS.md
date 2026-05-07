# DAY 65 PROGRESS — MiganCore
**Date:** 2026-05-07 (Thursday)
**Status:** Cycle 5 eval RUNNING → PENDING result
**Production Brain:** migancore:0.3 (weighted_avg 0.9082, Cycle 3)
**Candidate Brain:** migancore:0.5 (877 pairs ORPO, eval in progress)

---

## RINGKASAN HARI INI

Day 65 adalah hari pasca-training Cycle 5. Fokus: fix infrastruktur VPS yang rusak akibat
Ollama CPU steal, lalu re-run eval yang gagal timeout, sambil bikin vision doc 2026-2027.

---

## COMPLETED TODAY

### 1. Cycle 5 ORPO Training — SUKSES ✅
- **Vast.ai instance**: RTX 5880 Ada 49GB, 17.9 min, $0.058
- **Data**: 877 pairs (base 737 + 140 supplement voice/evo)
- **Result**: train_loss 2.5103, 2 epochs, LR=6e-7
- **Script**: `training/cycle5_orpo_vast.py` (fixed SCP bug Lesson #132)
- **Output dir**: `/opt/ado/cycle5_output/`
  - `adapter_model.safetensors` (155MB)
  - `adapter_config.json`
  - `cycle5_lora.gguf` (78MB)
- **HF Upload**: `Tiranyx/migancore-7b-soul-v0.5` ✅

### 2. SCP Timeout Bug Fixed — Lesson #132 ✅
- **Root cause**: `scp -r adapter_dir/` = 155MB safetensors + 3 checkpoint dirs × 325MB = ~700MB total → exceeds 600s timeout
- **Fix**: Removed `-r` flag; download only 2 specific files: `adapter_model.safetensors` + `adapter_config.json`
- **File**: `training/cycle5_orpo_vast.py` → function `scp_from()`

### 3. Ollama Registered migancore:0.5 ✅
- Modelfile created using `cycle5_lora.gguf` (llama.cpp LoRA adapter)
- Registered: `ollama create migancore:0.5 -f Modelfile_cycle5`
- Model accessible for eval

### 4. Stuck Ollama Runner Discovered & Killed ✅
- **Discovery**: `top` showed PID 2305843 at 692% CPU since 04:56 UTC → CPU steal 92.8%
- **Impact**: All inference 16× slower than normal → eval timing out at 300s/question
- **Fix**: `kill -9 2305843` → steal dropped from 92.8% to ~30%

### 5. Ollama 4-Core Cap Deployed — Lesson #133 ✅
- **Problem**: Ollama using all 8 cores → hypervisor throttle → steal 93.8%
- **Fix**: Added to `/opt/ado/docker-compose.yml`:
  ```yaml
  OLLAMA_NUM_THREAD: "4"       # Limit inference threads
  deploy:
    resources:
      limits:
        cpus: "4.0"            # Hard CPU quota
  ```
- **Result**: steal dropped from 93.8% → 29% (still ~40-60% post-fix during load)
- **Lesson**: 4 dedicated cores faster than 8 throttled cores on shared hypervisor

### 6. Eval Timeout Increased ✅
- Old: `_httpx.Timeout(300.0, connect=5.0, read=300.0)`
- New: `_httpx.Timeout(600.0, connect=10.0, read=600.0)`
- File: `eval/run_identity_eval.py` (patched both local + VPS copy)

### 7. Stuck Runner Watchdog Cron ✅
- **Script**: `scripts/kill_stuck_ollama_runners.sh`
  - Kills Ollama runner subprocesses running >30 min
- **Cron**: `*/15 * * * *` on VPS root crontab
- **Purpose**: Prevent repeat of today's 692% CPU situation

### 8. Vision Doc 2026-2027 Written ✅
- **File**: `docs/VISION_2026_2027_COGNITIVE_TRENDS.md` (449 lines)
- **Content**: 7 cognitive trends for 2026-2027 with MiganCore action plans
  1. Reasoning-as-Default (semua model bernalar)
  2. Knowledge Specialization (domain SLM menang)
  3. Bahasa Lokal Moat (kita punya native edge)
  4. User Data Flywheel (data sendiri = moat)
  5. Enterprise Connectors Tier List
  6. Sleep-Time Consolidation (offline learning)
  7. A2A Peer Protocol (agent-to-agent)
- Fahmi ideas structured, competitor table, North Star 2027, investor pitch

### 9. AGENT_ONBOARDING.md Updated ✅
- Added lessons #121-133 (Day 61-65)
- VPS commit: `9447c1c`

### 10. HuggingFace Upload ✅
- `Tiranyx/migancore-7b-soul-v0.5` — cycle5 adapter uploaded
- Method: `hf upload` CLI (huggingface-cli deprecated)

---

## INFRASTRUCTURE CHANGES

### docker-compose.yml Changes (Committed to repo)
```yaml
ollama:
  environment:
    OLLAMA_NUM_THREAD: "4"          # Lesson #133 — prevent hypervisor throttle
  deploy:
    resources:
      limits:
        memory: 12G
        cpus: "4.0"                 # Hard CPU quota
```

### New Files on VPS
- `/opt/ado/scripts/kill_stuck_ollama_runners.sh` — Ollama watchdog
- Crontab entry: `*/15 * * * * /opt/ado/scripts/kill_stuck_ollama_runners.sh`

---

## CYCLE 5 EVAL — IN PROGRESS ⏳

### Eval Setup
- **Script**: `/opt/ado/data/workspace/run_identity_eval.py`
- **Mode**: `--mode eval`
- **Model**: `migancore:0.5`
- **Reference**: `/app/eval/baseline_day58.json`
- **Output**: `/opt/ado/data/workspace/eval_result_migancore-7b-soul-cycle5.json`
- **Log**: `/opt/ado/data/workspace/cycle5_eval_stdout.log`
- **Process**: Detached `docker exec ado-api-1 bash -c ...` (persists through session)

### Gates Required for PROMOTE
| Category | Gate | Cycle 3 (production) |
|----------|------|----------------------|
| weighted_avg | ≥ 0.92 | 0.9082 |
| identity | ≥ 0.90 | 0.953 |
| voice | ≥ 0.85 | 0.817 |
| evo-aware | ≥ 0.80 | ~~0.537~~ (fixed with 60 pairs) |
| tool-use | ≥ 0.85 | 0.768 |
| creative | ≥ 0.80 | 0.829 |

### Eval Issues Encountered Today
1. Task `bopmyo9it` killed when API container restarted (ExitCode=0, restart #1)
2. Re-launched as detached process (nohup docker exec) — survives API restarts
3. Synthetic gen auto-resumed on API restart → 60% CPU → stopped via admin API
4. CPU steal still 40-63% despite 4-core cap (shared hypervisor loads vary)

---

## LESSONS DAY 65 (#131-133)

### #131: Voice/Evo Seed Dedup
- **Problem**: seed pool must be ≥ target pairs
- **Rule**: 30 seeds × 4 repeats = 30 UNIQUE pairs (not 120) — dedup removes exact-match seeds
- **Fix**: use larger, more diverse seed pools

### #132: NEVER scp -r Full Adapter Directory
- **Problem**: `scp -r adapter_dir/` downloads checkpoints (3 dirs × 325MB) = 700MB → 600s timeout
- **Rule**: ALWAYS use `scp` on specific files: `adapter_model.safetensors` + `adapter_config.json`
- **Applies to**: cycle scripts, manual copy, any adapter retrieval

### #133: Ollama All-Cores = Hypervisor CPU Throttle
- **Problem**: Ollama default threads = all vCPUs → hypervisor sees 100% utilization → schedules steal
- **Symptom**: `%st` in top shoots to 85-93% → inference 16× slower than expected
- **Fix**: `OLLAMA_NUM_THREAD: "4"` + `cpus: "4.0"` in docker-compose
- **Result**: steal 93.8% → 29-40% on 8-vCPU shared host

---

## COSTS DAY 65

| Item | Cost |
|------|------|
| Cycle 5 ORPO training (Vast.ai RTX 5880 Ada, ~18 min) | ~$0.058 |
| VPS inference (CPU-only, no extra cost) | $0 |
| HuggingFace upload | $0 |
| **Total Day 65** | **~$0.06** |

Cumulative Vast.ai: ~$7.06 used of $7 credit (nearly depleted)
RunPod saldo: $16.69 remaining

---

## PENDING (CARRIES TO DAY 66)

### Critical
- [ ] **Eval result** — wait for cycle5 eval to complete
- [ ] **PROMOTE or ROLLBACK** based on eval gates
- [ ] After PROMOTE: update `DEFAULT_MODEL` env to `migancore:0.5`, restart API
- [ ] After ROLLBACK: analyze failed cats, plan Cycle 6 supplement

### Short-term (Day 66-67)
- [x] KB auto-update mechanism → `scripts/kb_auto_update.py` LIVE, cron installed 23:00 UTC
- [x] User input → training pairs → `POST /v1/conversations/{id}/messages/{id}/feedback` COMMITTED (not yet deployed — pending eval + restart)
- [x] Frontend 👍👎 thumbs buttons → `frontend/chat.html` COMMITTED (not yet deployed)
- [x] Teacher refinement cron → `scripts/refine_pending_pairs.py` COMMITTED
- [x] DAY66_PLAN.md + deploy_day65.sh COMMITTED
- [ ] Re-enable synthetic gen after eval completes (currently stopped)
- [x] Commit Day 65 progress to local repo + push (commits: eb5b114 → b28cd9b)

### Medium-term (Week 10+)
- [ ] Clone mechanism (GAP-01) — first paid client prerequisite
- [ ] Enterprise connectors tier list (per VISION doc Phase 4)
- [ ] Multi-language (Jawa/Sunda/Minang keyword detection + response)

---

## NEXT AGENT INSTRUCTIONS (Day 66 handoff)

**One-command handoff when eval completes:**
```bash
# 1. Check eval (should be done by 12:00 UTC or soon after)
cat /opt/ado/data/workspace/eval_result_migancore-7b-soul-cycle5.json

# 2. Auto PROMOTE or ROLLBACK based on gates
bash /opt/ado/scripts/promote_cycle5.sh

# 3. Deploy Day 65 changes (feedback endpoint + SSE message_id + thumbs UI)
# Run deploy_day65.sh from VPS (after git pull so it has the script):
git -C /opt/ado pull origin main
bash /opt/ado/scripts/deploy_day65.sh

# 4. Restart synthetic generation
curl -X POST http://localhost:18000/v1/admin/synthetic/start \
  -H 'X-Admin-Key: ado-admin-5eab08ff6453b160dd4908cab9ead9ef' \
  -H 'Content-Type: application/json' \
  -d '{"target_pairs": 1000}'
```

**See docs/DAY66_PLAN.md for full priority list.**

Key contexts:
- Eval stdout: `/opt/ado/data/workspace/cycle5_eval_stdout.log`
- Eval result: `/opt/ado/data/workspace/eval_result_migancore-7b-soul-cycle5.json`
- promote script: `/opt/ado/scripts/promote_cycle5.sh`
- deploy script: `scripts/deploy_day65.sh` (in repo, need git pull first)
- Lessons #134-136 in docs/DAY66_PLAN.md — add to AGENT_ONBOARDING.md
