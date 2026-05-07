# DAY 66 PLAN — MiganCore
**Date:** 2026-05-08 (Friday)
**Author:** Claude Sonnet 4.6 (Day 65 handoff)
**Production Brain:** TBD — pending Cycle 5 eval result

---

## CONTEXT DARI DAY 65

### Yang Sudah Selesai Hari Ini:
1. ✅ Cycle 5 ORPO training: 877 pairs, RTX 5880 Ada, train_loss 2.5103
2. ✅ Stuck Ollama runner fix: 4-core cap (OLLAMA_NUM_THREAD=4)
3. ✅ KB auto-update cron: daily 23:00 UTC, exchangerate-api + IHSG
4. ✅ Thumbs feedback flywheel (commit 24b378a): backend + frontend complete
5. ✅ Teacher refinement cron (commit b69c171): `scripts/refine_pending_pairs.py`
6. ✅ promote_cycle5.sh ready at `/opt/ado/scripts/`
7. ⏳ Cycle 5 eval IN PROGRESS — started 10:31 UTC, ~8/20 done

### Yang Perlu Deploy Day 66 (setelah eval selesai):
```bash
# On VPS:
bash /opt/ado/scripts/deploy_day65.sh
# Then restart synthetic gen:
curl -X POST http://localhost:18000/v1/admin/synthetic/start \
  -H 'X-Admin-Key: ado-admin-5eab08ff6453b160dd4908cab9ead9ef' \
  -H 'Content-Type: application/json' \
  -d '{"target_pairs": 1000}'
```

---

## PRIORITAS DAY 66

### CRITICAL (lakukan pertama)

#### 1. Resolve Cycle 5 Eval → PROMOTE or ROLLBACK

Check result:
```bash
cat /opt/ado/data/workspace/eval_result_migancore-7b-soul-cycle5.json
bash /opt/ado/scripts/promote_cycle5.sh
```

Gates:
| Category | Gate | Cycle 3 (prod) |
|----------|------|----------------|
| weighted_avg | ≥ 0.92 | 0.9082 |
| identity | ≥ 0.90 | 0.953 |
| voice | ≥ 0.85 | 0.817 |
| evo-aware | ≥ 0.80 | (failed) → fixed |
| tool-use | ≥ 0.85 | 0.768 |
| creative | ≥ 0.80 | 0.829 |

**IF PROMOTE:**
- promote_cycle5.sh handles docker-compose + restart automatically
- Update MEMORY.md, DAY65_PROGRESS.md with result + timestamp
- Commit PROMOTE to git

**IF ROLLBACK:**
- Identify failed categories from eval_result JSON
- Generate targeted supplement pairs for failed cats
- Plan Cycle 6 training

#### 2. Deploy Day 65 Changes

```bash
bash /opt/ado/scripts/deploy_day65.sh
```

Deploys:
- Feedback endpoint (POST /v1/conversations/{id}/messages/{id}/feedback)
- SSE done event includes message_id
- Frontend thumbs 👍👎 buttons

#### 3. Restart Synthetic Generation

```bash
curl -X POST http://localhost:18000/v1/admin/synthetic/start \
  -H 'X-Admin-Key: ado-admin-5eab08ff6453b160dd4908cab9ead9ef' \
  -H 'Content-Type: application/json' \
  -d '{"target_pairs": 1000}'
```

---

### HIGH (setelah critical done)

#### 4. Test Thumbs Feedback E2E
- Chat dengan migancore via app.migancore.com
- Klik 👎 pada satu respon
- Verify di DB: `SELECT * FROM preference_pairs WHERE source_method='user_thumbs_down' ORDER BY created_at DESC LIMIT 1;`
- Verify chosen="PENDING — awaiting teacher API refinement"

#### 5. Verify KB Auto-Update
- Check cron log: `cat /tmp/kb_update.log`
- If empty/failed: run manually: `python3 /opt/ado/scripts/kb_auto_update.py`
- Check that DATA TERKINI section updated in indonesia_kb_v1.md

#### 6. Install refine_pending_pairs.py Cron
```bash
# Already done by deploy_day65.sh, but verify:
crontab -l | grep refine_pending
```

#### 7. Update AGENT_ONBOARDING.md
- Add lessons #134+ from Day 65 session
- Document: SSE message_id pattern, PreferencePair user_thumbs_down flow, teacher refinement cron

---

### NORMAL (Day 66-67 sprint)

#### 8. Clone Mechanism (GAP-01) — P0 for First Paid Client
- aaPanel API: create new site + SSL certificate
- Docker template: per-client Compose file generator
- License integration: validate BERLIAN/EMAS tier before clone
- Files to create:
  - `api/services/clone_manager.py`
  - `scripts/clone_ado.sh` (aaPanel + Docker automation)
  - `api/routers/admin.py` — add `/v1/admin/clone` endpoint

#### 9. Multi-Language Detection (Jawa/Sunda/Minang)
- Keyword dict for each language dialect
- Inject into system prompt: "User berbicara Bahasa Jawa, respond dengan campuran Indonesia+Jawa"
- Implementation in `services/language_detector.py`

#### 10. Enterprise Connectors Research
- BPS API (bps.go.id) — GDP, inflation, population stats
- IDX (Indonesia Stock Exchange) — IHSG + listed companies
- BI (Bank Indonesia) — monetary policy, reference rate

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

---

## COSTS DAY 65

| Item | Cost |
|------|------|
| VPS inference (CPU-only, no extra) | $0 |
| Gemini API (KB queries, no new pairs today) | ~$0 |
| **Total Day 66** | **$0** |

Remaining credits: Vast.ai ~$6.84, RunPod $16.69

---

## COMMIT LOG DAY 65

| Commit | What |
|--------|------|
| eb5b114 | DAY65_PROGRESS.md |
| 6fbcff9 | kb_auto_update.py + promote_cycle5.sh + kill_stuck_ollama_runners.sh |
| 3f60a66 | conversations.py feedback endpoint |
| c2b895d | scripts cleanup + docker-compose.yml 4-core cap |
| 24b378a | thumbs feedback flywheel (backend + frontend) |
| b69c171 | refine_pending_pairs.py teacher cron |
| deploy_day65.sh | NOT YET COMMITTED — add to Day 66 commit |

---

## ENVIRONMENT NOTES

- VPS: root@72.62.125.6, key ~/.ssh/sidix_session_key
- Compose dir: /opt/ado/
- Container names: ado-api-1, ado-ollama-1 (NOT migancore-*)
- Frontend: /www/wwwroot/app.migancore.com/chat.html
- Eval log: /opt/ado/data/workspace/cycle5_eval_stdout.log
- Eval result: /opt/ado/data/workspace/eval_result_migancore-7b-soul-cycle5.json
