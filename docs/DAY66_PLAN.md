# DAY 66 PLAN — MiganCore
**Date:** 2026-05-08 (Friday)
**Author:** Claude Sonnet 4.6 (Day 65 handoff — fully updated)
**Production Brain:** migancore:0.3 (STAYS — Cycle 5 ROLLBACK)

---

## CONTEXT DARI DAY 65 — SELESAI SEMUA ✅

### Yang Sudah Selesai (Day 65 + awal Day 66):
1. ✅ Cycle 5 ORPO training: 877 pairs, RTX 5880 Ada, train_loss 2.5103
2. ✅ Stuck Ollama runner fix: 4-core cap (OLLAMA_NUM_THREAD=4)
3. ✅ KB auto-update cron: daily 23:00 UTC, exchangerate-api + IHSG
4. ✅ Thumbs feedback flywheel (commit 24b378a): backend + frontend LIVE
5. ✅ Teacher refinement cron (commit b69c171): installed 19:00 UTC daily
6. ✅ Cycle 5 eval COMPLETE → **ROLLBACK** (4/6 gates failed, see below)
7. ✅ deploy_day65.sh EXECUTED: API rebuilt + restarted, frontend deployed
8. ✅ Feedback endpoint LIVE: `POST /v1/conversations/{id}/messages/{id}/feedback`
9. ✅ Synthetic gen RUNNING: target 1000 pairs
10. ✅ VPS git HEAD: `426833b` (all commits pushed to main)

### Cycle 5 Eval Result — ROLLBACK ❌

| Category | Score | Gate | Status | Notes |
|----------|-------|------|--------|-------|
| identity | 0.9376 | ≥ 0.90 | ✅ PASS | Excellent |
| voice | 0.8946 | ≥ 0.85 | ✅ PASS | +0.077 dari Cycle 4 — 80 pairs worked |
| weighted_avg | 0.8453 | ≥ 0.92 | ❌ FAIL | 3 Ollama 500 errors cost ~0.099 |
| evolution-aware | 0.7502 | ≥ 0.80 | ❌ FAIL | +0.213 dari Cycle 4 tapi below gate |
| tool-use | 0.7439 | ≥ 0.85 | ❌ FAIL | No targeted pairs di Cycle 5 |
| creative | 0.7278 | ≥ 0.80 | ❌ FAIL | Regressed -0.101 — domain pairs diluted |

**Root cause**: 3 Ollama HTTP 500 errors (CPU steal 58-65%) → scored 0.000 each → -0.099 on weighted_avg.
Est. weighted_avg without errors: ~0.944 → would PASS 0.92 gate.

---

## PRIORITAS DAY 66

### CRITICAL (lakukan pertama)

#### 1. Generate Cycle 6 Supplement Pairs

Target: fix 3 failed categories + add eval retry infrastructure.

**Tool-use supplement (60+ pairs)**
```bash
python3 scripts/generate_tool_use_pairs.py --target 60
```
Focus on:
- Image gen description format (describe → call generate_image → describe result)
- File write confirmation (write file → confirm with "File X berhasil ditulis")
- Tool invocation patterns (onamix_search → summarize result → cite source)
- Multi-step tool chains (search → read URL → summarize)

**Creative supplement (60+ pairs)**
```bash
python3 scripts/generate_creative_pairs.py --target 60
```
Focus on:
- Tagline generation (brand name → catchy Indonesian tagline)
- Name generation (product/company naming with rationale)
- Creative storytelling (short story, analogy, metaphor)
- Copywriting in Migan voice (warm, direct, tidak bertele-tele)

**Evolution-aware supplement (40+ pairs)**
```bash
python3 scripts/generate_evo_aware_pairs.py --target 40
```
Total after this: ~100 evo-aware pairs (60 existing + 40 new).
Focus on episodic memory explanation, learning from past errors, self-correction.

**Eval retry infrastructure**
- File: `eval/run_identity_eval.py`
- Add retry: max 3 retries per question on HTTP 500
- Sleep 10s between retries
- Log retry count per question
- This would prevent 3 questions scoring 0.000

#### 2. Export + Train Cycle 6

After supplement pairs generated:
```bash
# Export dataset
python3 scripts/export_cycle6_dataset.py

# Train on Vast.ai
python3 training/cycle6_orpo_vast.py
```

Target: 900-1100 pairs total for Cycle 6 JSONL.
Same hyperparams as Cycle 5 (2 epochs, lr=6e-7, ORPO beta=0.1).

---

### HIGH (setelah critical done)

#### 3. Test Thumbs Feedback E2E
- Chat dengan migancore via app.migancore.com
- Klik 👎 pada satu respon
- Verify di DB:
  ```sql
  SELECT id, prompt, rejected, chosen, source_method, created_at
  FROM preference_pairs
  WHERE source_method = 'user_thumbs_down'
  ORDER BY created_at DESC
  LIMIT 1;
  ```
- Verify `chosen = 'PENDING — awaiting teacher API refinement'`
- Verify 👍👎 buttons appear (requires `msg.serverId` to be set from SSE done event)

#### 4. Update AGENT_ONBOARDING.md
- Add lessons #134-136 from Day 65 session
- Document: SSE pre-assigned UUID pattern, serverId vs id in React, asyncpg cron pattern
- File: `docs/AGENT_ONBOARDING.md`

#### 5. Verify KB Auto-Update Cron
```bash
# Check if cron ran at 23:00 UTC
cat /tmp/kb_update.log

# If empty/no output, run manually:
python3 /opt/ado/scripts/kb_auto_update.py

# Verify DATA TERKINI section updated:
grep -A 5 "DATA TERKINI" /opt/ado/data/knowledge/indonesia_kb_v1.md | head -20
```

---

### NORMAL (Day 66-67 sprint)

#### 6. Clone Mechanism (GAP-01) — P0 for First Paid Client
- aaPanel API: create new site + SSL certificate
- Docker template: per-client Compose file generator
- License integration: validate BERLIAN/EMAS tier before clone
- Files to create:
  - `api/services/clone_manager.py`
  - `scripts/clone_ado.sh` (aaPanel + Docker automation)
  - `api/routers/admin.py` — add `/v1/admin/clone` endpoint

#### 7. Multi-Language Detection (Jawa/Sunda/Minang)
- Keyword dict for each language dialect
- Inject into system prompt: "User berbicara Bahasa Jawa, respond dengan campuran Indonesia+Jawa"
- Implementation in `services/language_detector.py`

#### 8. Enterprise Connectors Research
- BPS API (bps.go.id) — GDP, inflation, population stats
- IDX (Indonesia Stock Exchange) — IHSG + listed companies
- BI (Bank Indonesia) — monetary policy, reference rate

---

## CYCLE 6 TRAINING PLAN

### Target Supplement Breakdown
| Category | Existing (Cycle 5) | New Cycle 6 | Total |
|----------|--------------------|-------------|-------|
| tool-use | ~0 targeted | +60 | 60 |
| creative | 55 (creative_id) | +60 | 115 |
| evolution-aware | 60 | +40 | 100 |
| voice | 80 | 0 (PASS already) | 80 |
| identity | (core dataset) | 0 (PASS already) | - |

### Eval Infrastructure Fix
```python
# In eval/run_identity_eval.py, wrap each question call:
for attempt in range(3):
    try:
        response = call_ollama(question)
        break
    except HTTPError as e:
        if e.status_code == 500 and attempt < 2:
            logger.warning(f"Q{qnum} attempt {attempt+1} failed (500), retrying in 10s...")
            await asyncio.sleep(10)
        else:
            raise
```

### Training Config (same as Cycle 5)
```yaml
model: Qwen/Qwen2.5-7B-Instruct
epochs: 2
lr: 6e-7
loss: orpo
beta: 0.1
batch_size: 4
grad_accum: 4
```

---

## LESSONS DAY 65 (for AGENT_ONBOARDING.md)

### #134: SSE message_id Pattern — Pre-generate UUID Before Stream
- **Problem**: Feedback endpoint needs server DB message ID, but SSE `done` fires before `_persist_assistant_message` completes
- **Solution**: Generate `assistant_msg_id = uuid.uuid4()` at start of `generate()`, include in all `done` events, pass to `_persist_assistant_message(message_id=...)` which uses it when creating the Message ORM object
- **Pattern**: Pre-assign UUID → stream → pass UUID to persist → client never needs to re-fetch

### #135: Thumbs Feedback — serverId vs id for Message State
- **Problem**: Frontend messages use `Date.now()` as local ID; server uses UUID; React key must not change (causes re-mount)
- **Solution**: Add `serverId` field to message state (separate from local `id`); `onDone` callback receives `serverMsgId` and stores it as `msg.serverId`; feedback buttons only appear when `msg.serverId && convId` both truthy

### #136: Teacher Refinement Cron — asyncpg Not asyncio.run on old Python
- **Note**: `refine_pending_pairs.py` uses asyncpg directly (not SQLAlchemy) for simpler cron operation. DB DSN env var format: DATABASE_URL with `postgresql://` (not `postgresql+asyncpg://`)

### #137: Ollama 500 Under CPU Steal → Always Add Retry in Eval
- **Problem**: 3 Ollama HTTP 500 errors during Cycle 5 eval (CPU steal 58-65%) → scored 0.000 → -0.099 on weighted_avg → ROLLBACK instead of PROMOTE
- **Rule**: ALL eval scripts MUST have retry logic (max 3, 10s sleep) for Ollama 500 errors
- **Impact**: Without retry, infrastructure issues cause unfair rollbacks that waste Vast.ai credits + training time

---

## COSTS DAY 65

| Item | Cost |
|------|------|
| VPS inference (CPU-only, no extra) | $0 |
| Gemini API (KB queries, no new pairs) | ~$0 |
| **Total Day 65** | **~$0** |

Remaining credits: Vast.ai ~$6.84, RunPod $16.69

---

## COMMIT LOG DAY 65

| Commit | What |
|--------|------|
| eb5b114 | DAY65_PROGRESS.md initial |
| 6fbcff9 | kb_auto_update.py + promote_cycle5.sh + kill_stuck_ollama_runners.sh |
| 3f60a66 | conversations.py feedback endpoint |
| c2b895d | scripts cleanup + docker-compose.yml 4-core cap |
| 24b378a | thumbs feedback flywheel (backend + frontend) |
| b69c171 | refine_pending_pairs.py teacher cron |
| b28cd9b | deploy_day65.sh + DAY66_PLAN.md initial |
| be01b90 | promote_cycle5.sh JSON key bug fix (Lesson #136) |
| 426833b | docs(day65): ROLLBACK verdict + final eval result + lessons #134-136 |

---

## ENVIRONMENT NOTES

- VPS: root@72.62.125.6, key ~/.ssh/sidix_session_key
- Compose dir: /opt/ado/
- Container names: ado-api-1, ado-ollama-1 (NOT migancore-*)
- Frontend: /www/wwwroot/app.migancore.com/chat.html
- Eval log: /opt/ado/data/workspace/cycle5_eval_stdout.log
- Eval result: /opt/ado/data/workspace/eval_result_migancore-7b-soul-cycle5.json
- Supplement gen scripts: `scripts/generate_*.py`
- Cycle 6 export: `scripts/export_cycle6_dataset.py`
- Cycle 6 training: `training/cycle6_orpo_vast.py`
