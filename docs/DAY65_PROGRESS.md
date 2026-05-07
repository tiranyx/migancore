# DAY 65 PROGRESS — MiganCore
**Date:** 2026-05-07 (Thursday)
**Status:** Cycle 5 eval COMPLETE → ROLLBACK
**Production Brain:** migancore:0.3 (weighted_avg 0.9082, Cycle 3) — STAYS
**Candidate Brain:** migancore:0.5 — ROLLBACK (4/6 gates failed)

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

## CYCLE 5 EVAL — COMPLETE ✅ → ROLLBACK ❌

### Eval Result (eval_result_migancore-7b-soul-cycle5.json)
- **simple_avg**: 0.735 | **weighted_avg**: 0.8453
- **Passed**: 12/20 | **Failed**: 8/20 (3 from Ollama 500 errors!)

| Category | Score | Gate | Status | Notes |
|----------|-------|------|--------|-------|
| identity | 0.9376 | ≥ 0.90 | ✅ PASS | Excellent |
| voice | 0.8946 | ≥ 0.85 | ✅ PASS | Improved from 0.817 (80 pairs worked!) |
| weighted_avg | 0.8453 | ≥ 0.92 | ❌ FAIL | 3 Ollama 500 errors cost ~0.099 |
| evolution-aware | 0.7502 | ≥ 0.80 | ❌ FAIL | Improved from 0.537 (+0.213) but below gate |
| tool-use | 0.7439 | ≥ 0.85 | ❌ FAIL | No targeted pairs added |
| creative | 0.7278 | ≥ 0.80 | ❌ FAIL | Regressed from 0.829 (Cycle 4) |

### Root Cause Analysis
- **Ollama 500 errors** (Q3 values, Q7 anti-pattern, Q12 reasoning): caused by CPU steal (58-65%). Each 500 → 0.000 score. Combined impact: -0.099 on weighted_avg. Without 500 errors: est. weighted_avg ~0.944 → PASS 0.92 gate.
- **Tool-use**: No tool-use pairs in Cycle 5 supplement (only voice+evo-aware). Score similar to Cycle 4 (0.768). Q10 "write notes.md" failed because model wrote only the file content, not the "file written" confirmation sentence.
- **Creative**: Regressed 0.829→0.728. Domain pairs (engineering, UMKM, etc.) diluted creative style.
- **Evolution-aware**: Improved (+0.213) but 60 pairs not enough for gate.

### Cycle 6 Plan
1. Tool-use supplement: 60+ pairs (image gen description, file write confirmation format, tool invocation patterns)
2. Creative supplement: 60+ pairs (restore tagline, name generation, creative writing style)
3. Evolution-aware: 40+ more pairs (total 100)
4. Eval infrastructure: add retry on 500 errors (max 3 retries per question)

### Eval Infrastructure Issues
1. Eval task `bopmyo9it` killed when API container restarted
2. Re-launched as detached nohup process (persists through SSH disconnect)
3. Synthetic gen auto-resumed on API restart → stopped via admin API
4. CPU steal 58-65% → 3 Ollama 500 errors → score 0.000 on 3 questions

---

## LESSONS DAY 65 (#131-136)

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

### #134: SSE message_id — Pre-Generate UUID Before Stream
- **Problem**: Feedback endpoint needs server DB UUID, but SSE `done` fires BEFORE `_persist_assistant_message` task completes
- **Solution**: `assistant_msg_id = uuid.uuid4()` at top of `generate()` → include in all `done` events → pass `message_id=assistant_msg_id` to persist function → Message ORM uses it
- **Pattern**: pre-assign UUID → stream → pass UUID to persist → no extra round-trip needed

### #135: Frontend Message serverId vs id
- **Problem**: Frontend messages use `Date.now()` as local `id` (React key). Replacing `id` with server UUID causes React key change → component re-mount (state reset = bad)
- **Solution**: Add `serverId` field (separate from `id`). `onDone(cid, serverMsgId)` sets `m.serverId`. Feedback buttons check `msg.serverId && convId`.
- **Applies to**: any pattern where frontend needs server-assigned ID post-stream

### #136: promote_cycle5.sh JSON Key Bug — Always Validate Against Actual Schema
- **Problem**: Script read `d.get('eval_summary', {}).get('weighted_avg')` but eval JSON uses flat structure: `d['weighted_avg_cosine_sim']` and `d['category_means']`
- **Fix**: Support both formats (nested eval_summary + flat) with fallback
- **Lesson**: When writing gate scripts, always run against sample output JSON first. "Written against spec" ≠ "matches actual JSON output"

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

---

## CYCLE 5 EVAL — FINAL RESULT (Day 67 resolution)

**Eval completed:** 2026-05-07 11:25 UTC  
**Decision: ROLLBACK ❌**  
**Production brain stays: migancore:0.3** (Cycle 3, weighted_avg 0.9082)

### Gate Results

| Gate | Required | Actual | Status |
|------|----------|--------|--------|
| weighted_avg | ≥ 0.92 | 0.8453 | ❌ FAIL |
| identity | ≥ 0.90 | 0.9376 | ✅ PASS |
| voice | ≥ 0.85 | 0.8946 | ✅ PASS |
| evo-aware | ≥ 0.80 | 0.7502 | ❌ FAIL |
| tool-use | ≥ 0.85 | 0.7439 | ❌ FAIL |
| creative | ≥ 0.80 | 0.7278 | ❌ FAIL |

**Note:** Eval script reported PROMOTE (threshold=0.80 ≠ real gate 0.92) — Lesson #140 mismatch.

### Root Cause Analysis

- **3 Ollama 500 errors** during eval (Q3 values, Q7 anti-pattern, Q12 reasoning):
  - CPU steal 65%+ caused transient Ollama crashes
  - Each error → cosine_sim = 0.000 → unfair penalty
  - Estimated true weighted_avg without errors: ~0.916 (still < 0.92)
- **evo-aware 0.750** — only 20 pairs in Cycle 5 supplement (insufficient)
- **tool-use 0.744** — write_file confirm pattern not represented
- **creative 0.728** — creative pairs lacked voice-anchored style

### Fix Applied in Cycle 6

Dataset 954 pairs (already training on Vast.ai):
- tool-use: +29 unique pairs (write_file confirm pattern)
- creative: +28 creative voice pairs
- evo-aware: +20 additional pairs
- Retry logic added to eval script (Lesson #137)
- CPU cap reduced: OLLAMA_NUM_THREAD=4, cpus=4.0

### Deployment Actions (Day 67)

- ✅ API rebuilt + redeployed: feedback endpoint + message_id SSE active
- ✅ Frontend: thumbs feedback UI already live (Day 65 commit)
- ✅ nginx reloaded (aaPanel)
- ✅ Cycle 6 training: Vast.ai Q RTX 8000, 954 pairs, ETA ~18:00 UTC
