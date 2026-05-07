# DAY 67 PLAN — MiganCore
**Date:** 2026-05-09 (Saturday)
**Author:** Claude Sonnet 4.6 (Day 67 handoff)
**Production Brain:** migancore:0.3 (weighted_avg 0.9082, Cycle 3)
**Cycle 6 Training:** RUNNING (Vast.ai Q RTX 8000, step 54/118 at checkpoint, ETA ~17:30 UTC)

---

## CONTEXT DARI DAY 67

### Selesai Di Day 67:
1. ✅ Cycle 6 training LAUNCHED (Vast.ai instance 36295755, Q RTX 8000 48GB @ $0.255/hr, 954 pairs, ORPO apo_zero)
2. ✅ GAP-01 Clone mechanism: `api/services/clone_manager.py` (618 lines) + `/v1/admin/clone` endpoint — E2E dry-run PASS
3. ✅ `post_cycle6.sh` automation script: GGUF convert → Ollama create → eval → promote/rollback
4. ✅ SSL certbot: tiranyx.co.id + sidixlab.com + galantara.io
5. ✅ VISION_ADO_2026_2027_COMPREHENSIVE.md created (517 lines, 7 cognitive trends, 5-sprint roadmap, ADO v2 architecture)
6. ✅ Old Ollama models deleted (0.1, 0.2, 0.4, 0.5) = ~19GB freed; only 0.3 + qwen2.5 base remain
7. ✅ VPS git pulled (HEAD `5d4d9e7` before rebase; local push `6d206e1` includes vision doc + memory updates)

### Resource Audit Day 67 (Key Findings):
- `interactions_feedback`: 0 rows — thumbs flywheel not tested by real users (65 convs, 53 users mostly test accounts)
- `preference_pairs`: 3,007 total — only 954 used Cycle 6 (32%) — SIDIX 1,458 pairs = free data!
- Ollama disk after cleanup: 4 models × 4.8GB deleted = ~19GB freed
- Vast.ai credit remaining: ~$6.60 after Cycle 6 (~$0.25 est)
- RunPod credit: $16.69 (backup)

---

## PRIORITAS DAY 67

### CRITICAL (setelah Cycle 6 selesai ~17:30 UTC)

#### 1. Run post_cycle6.sh — Automated Post-Training Pipeline
```bash
# SSH ke VPS
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6

# Jalankan post pipeline (otomatis: GGUF convert + Ollama register + eval + promote/rollback)
bash /opt/ado/scripts/post_cycle6.sh
# Logs: /tmp/post_cycle6.log + /tmp/cycle6_eval_stdout.log
# Eval result: /opt/ado/data/workspace/eval_result_migancore-7b-soul-cycle6.json
```

**Gate targets (all must pass):**
| Category | Gate | Fix Applied |
|----------|------|-------------|
| weighted_avg | ≥ 0.92 | Eval retry fix (max 3, 10s sleep) est. +0.099 |
| identity | ≥ 0.90 | 194 curated pairs ✅ |
| voice | ≥ 0.85 | 31 maintenance pairs ✅ |
| tool-use | ≥ 0.85 | 29 targeted pairs |
| creative | ≥ 0.80 | 28 targeted pairs |
| evolution-aware | ≥ 0.80 | 20 targeted pairs |

**If PROMOTE:** Update `DEFAULT_MODEL=migancore:0.6`, restart API, update TASK_BOARD.md

**If ROLLBACK:** Plan Cycle 7 — SIDIX data injection + Qwen3-8B eval baseline

---

### HIGH (Day 67-68)

#### 2. Test Feedback Flywheel E2E
Goal: verify `interactions_feedback` table actually captures user feedback.

```sql
-- Before: check 0 rows
SELECT COUNT(*) FROM interactions_feedback;

-- Steps:
-- 1. Login app.migancore.com dengan akun real
-- 2. Chat → klik 👎 pada satu respons
-- 3. After: verify row added
SELECT id, user_id, message_id, feedback_type, created_at
FROM interactions_feedback
ORDER BY created_at DESC LIMIT 1;
```

#### 3. Pull VPS git → Sync Vision Doc
```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 '
cd /opt/ado
git pull origin main
echo "HEAD: $(git rev-parse --short HEAD)"
'
# Verify VISION_ADO_2026_2027_COMPREHENSIVE.md ada di /opt/ado/docs/
```

#### 4. Verify KB Auto-Update Ran
```bash
# Kalau sudah lewat 23:00 UTC
cat /tmp/kb_update.log | tail -20
# Should show: exchangerate-api + IHSG update, new DATA TERKINI section
```

---

### NORMAL (Day 68-70)

#### 5. SIDIX Training Pairs → ADO Cycle 7 Format
- Source: `/opt/sidix/brain/datasets/` (1,458 pairs SIDIX DPO format)
- Target: convert ke ORPO JSONL (prompt/chosen/rejected columns)
- Script: `training/convert_sidix_to_ado.py`
- Expected impact: +1,458 diverse Indonesian pairs for Cycle 7

#### 6. Qwen3-8B Baseline Eval (Research Decision)
```bash
# Download Qwen3:8b (5.2GB) — if disk space allows
docker exec ado-ollama-1 ollama pull qwen3:8b-q4_K_M

# Quick 5-question eval vs qwen2.5:7b
# Questions: 1 Indonesia KB, 1 tool-use, 1 creative, 1 evo-aware, 1 coding
# Compare latency + quality
```
Purpose: decide if Cycle 7 base model upgrade to Qwen3-8B is worthwhile.

#### 7. Update AGENT_ONBOARDING.md — Day 67 Lessons
Add lessons #138-142 (see Lessons section below):
- File: `docs/AGENT_ONBOARDING.md`
- VPS path: `/opt/ado/docs/AGENT_ONBOARDING.md`

---

## CYCLE 7 PRELIMINARY PLAN (post Cycle 6 result)

### If Cycle 6 PROMOTE → Cycle 7 = Qwen3 + SIDIX

**Upgrade Track:**
1. Pull Qwen3:8b-q4_K_M as new base
2. Merge SIDIX 1,458 pairs (Indonesian conversation dataset)
3. Run GRPO supplement for reasoning category (new gate: reasoning ≥ 0.80)
4. Target: 1,200-1,500 total pairs, 3 epochs

**New Gates Cycle 7:**
| Category | Cycle 6 Gate | Cycle 7 Gate (raised) |
|----------|-------------|----------------------|
| weighted_avg | ≥ 0.92 | ≥ 0.94 |
| identity | ≥ 0.90 | ≥ 0.92 |
| voice | ≥ 0.85 | ≥ 0.88 |
| tool-use | ≥ 0.85 | ≥ 0.88 |
| creative | ≥ 0.80 | ≥ 0.83 |
| evolution-aware | ≥ 0.80 | ≥ 0.83 |
| reasoning (new) | N/A | ≥ 0.80 |

### If Cycle 6 ROLLBACK → Cycle 7 = Deep Fix

Same dataset focus but:
1. Analyze which gates failed (likely tool-use or creative again)
2. Double the supplement count for failed categories (60 → 120 pairs)
3. Add diversity seeding (Lesson #138: unique scenarios per pair not repeat seeds)
4. Consider GRPO loss for reasoning specifically

---

## LESSONS DAY 67 (#139-142)

### #139: Kimi CAI Fallback — Graceful Degradation Pattern
- **Context**: Kimi API unreachable during Day 67 → CAI pipeline falling back to Gemini-only single teacher
- **Rule**: Quorum (2-teacher parallel) is IDEAL but single-teacher fallback is ACCEPTABLE. Both fail = Ollama fallback. Never block training on teacher availability.
- **Monitor**: Check CAI success/failure rate weekly — if Kimi consistently fails, swap to GPT-4o or Claude API as secondary

### #140: interactions_feedback = 0 Is Expected, Not A Bug
- **Context**: Day 67 audit found 0 rows in interactions_feedback despite 65 conversations + thumbs UI deployed
- **Root cause**: 53 registered users are mostly automated test accounts from early development (Day 1-30). Real beta users = minimal (~5-10 active). Frontend thumbs requires `msg.serverId && convId` which only works post-SSE-done-event.
- **Rule**: ZERO rows = "no real users triggered it yet", not "it's broken". E2E test flywheel with a real login account before declaring broken.
- **Action**: Test manually: login app.migancore.com → chat → 👎 → verify DB row

### #141: Old Model Cleanup = Always Delete After Rollback
- **Context**: Found migancore:0.1, 0.2, 0.4, 0.5 all still in Ollama = ~19GB wasted
- **Rule**: After ROLLBACK decision, delete candidate model within same session. Only keep: production model + base qwen2.5. Graveyard models waste disk (4.8GB each) on a shared VPS.
- **Protocol**: Post every ROLLBACK = `ollama rm migancore:0.X` immediately

### #142: Resource Audit Pattern — Run After Every Cycle
- **Context**: Day 67 RESOURCE_AUDIT.md revealed 3 actionable findings (interactions_feedback 0, 68% preference_pairs unused, SIDIX free data)
- **Rule**: Before planning next cycle, always run: `SELECT COUNT(*) FROM preference_pairs; SELECT COUNT(*) FROM interactions_feedback;` + `df -h` + `ollama list`. 30-second audit prevents planning blindness.
- **Template**: RESOURCE_AUDIT_DAY{N}.md = standard checkpoint doc every cycle

---

## ENVIRONMENT NOTES (Day 67)

```
VPS:     root@72.62.125.6, key ~/.ssh/sidix_session_key
Compose: /opt/ado/
Containers: ado-api-1 (v0.5.19, healthy), ado-ollama-1, ado-postgres-1, ado-redis-1, ado-qdrant-1, ado-letta-1
Frontend:   /www/wwwroot/app.migancore.com/chat.html
Ollama:     migancore:0.3 (production) + qwen2.5:7b-instruct-q4_K_M + qwen2.5:0.5b
Training:   Vast.ai instance 36295755 (Q RTX 8000 48GB, $0.255/hr)
            Status: RUNNING step 54/118, ETA ~17:30 UTC
Post script: /opt/ado/scripts/post_cycle6.sh
Eval result: /opt/ado/data/workspace/eval_result_migancore-7b-soul-cycle6.json
Crons:      kill_stuck_ollama (*/15), kb_auto_update (23:00 UTC), refine_pending (19:00 UTC)
Git HEAD:   local `6d206e1` (includes vision doc) — VPS needs `git pull`
```

---

## COSTS DAY 67

| Item | Cost |
|------|------|
| Cycle 6 training Vast.ai (ETA ~$0.20-0.30) | ~$0.25 |
| GGUF convert + eval (VPS CPU) | $0 |
| Gemini API (resource audit queries) | ~$0 |
| **Total Day 67** | **~$0.25** |

Remaining credits: Vast.ai ~$6.60, RunPod $16.69

---

## NEXT AGENT INSTRUCTIONS (Day 68 handoff)

**After post_cycle6.sh completes:**

1. If PROMOTE:
```bash
# On VPS:
# Update env
sed -i 's/DEFAULT_MODEL=.*/DEFAULT_MODEL=migancore:0.6/' /opt/ado/.env
docker compose -f /opt/ado/docker-compose.yml restart api
# Update TASK_BOARD.md
```

2. After promote/rollback — run feedback flywheel test:
```bash
# Manual: login app.migancore.com → chat → 👎 → check DB
psql -U ado -d ado_db -c "SELECT COUNT(*) FROM interactions_feedback;"
```

3. Pull vision doc to VPS:
```bash
cd /opt/ado && git pull origin main
ls docs/VISION_ADO_2026_2027_COMPREHENSIVE.md
```

**See DAY68_PLAN.md (create Day 68)**
