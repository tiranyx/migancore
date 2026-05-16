# Day 75 Wrap-Up — MiganCore Organic Growth Sprint

## Summary
Full iteration cycle completed: commit → push → pull → deploy → validate → test → document.

## Changes Deployed (commit 159475f)

### 1. Feedback Pipeline Fix
- **Bug**: `get_feedback_stats` query used `PreferencePair.tenant_id` which does not exist (global table, no RLS)
- **Fix**: JOIN via `FeedbackEvent` to scope awaiting count per tenant
- **Impact**: Feedback stats endpoint now works correctly

### 2. Backfill Script
- `api/scripts/backfill_preference_pairs.py` — reusable script for future migrations
- Backfilled 46 existing feedback events → 48 total preference pairs

### 3. Identity Dataset Expansion
- `training_data/identity_sft_200_ORGANIC.jsonl` → 200 pairs (was 182)
- New categories: `identity_ecosystem` (5), `identity_growth` (5), `identity_capabilities` (3)
- Reinforced: `identity_anti_marker` (+5)

## Production Metrics (Post-Deploy)
| Metric | Value |
|--------|-------|
| API Version | v0.5.16 |
| Model | migancore:0.8 |
| Health | ✅ healthy |
| Preference Pairs | 48 |
| KG Entities | 110 |
| KG Relations | 126 |
| Feedback Events | 47 |
| AWAITING Pairs | 0 (all processed by worker) |

## Validation Performed
- [x] API health check passed
- [x] `get_feedback_stats` returns correct data without error
- [x] 48 pairs confirmed in DB
- [x] KG activation confirmed: 110 entities, 126 relations
- [x] Feedback worker running (logs show `feedback.worker.started`)

## Backlog & Next Steps
1. **CPU LoRA Training** — Run `cpu_train_lora.py` with 200 SFT + 48 DPO pairs (6-12h, 20-28GB RAM)
2. **Eval Gate v2** — Run identity eval on migancore:0.8 to verify post-deploy identity strength
3. **Test Suite Runner** — Setup isolated test DB container + run full pytest suite
4. **Auto-Training Watchdog** — Currently 46 real pairs (need 80 to trigger proposal)
5. **RLS Audit** — Review all `get_admin_db()` queries for missing tenant context
6. **Identity Dataset → 300** — Add multi-turn, emotional, debugging scenarios
7. **Daily Harvest** — Verify `daily_harvest.sh` and `distill_cron.sh` are functional

## Lessons Learned
- RLS on `interactions_feedback`/`conversations`/`messages` requires explicit `set_config('app.current_tenant')` for `ado_app` user. Queries without context return 0 rows silently.
- Container rootfs read-only means scripts must be baked into image or run via stdin pipe.
- `asyncpg` + `ON CONFLICT` via heredoc = escape hell. Prefer SQLAlchemy Core `text()` with named params inside container, or `psycopg2` from host.

## Commits
- `159475f` fix(feedback): correct get_feedback_stats JOIN on global preference_pairs

## Incident Log
- **03:22 UTC**: Accidental `docker compose down --remove-orphans` stopped all production containers (API, Postgres, Ollama, Redis, Qdrant). Letta remained running.
- **03:22 UTC**: Immediate `docker compose up -d` recovered all services within 30 seconds.
- **Impact**: Zero data loss (Postgres data persisted in Docker volume). API downtime ~30 seconds.
- **Lesson**: Never run `down --remove-orphans` on production without explicit service list. Use `docker compose rm` for specific orphans only.

## Post-Deploy Optimizations
- **Cron scripts**: Fixed executable permissions on `daily_harvest.sh` and `daily_iteration.sh`
- **DPO path fix**: Corrected `dpo_export.jsonl` path from `training_data/` to `data/training_new/` (1002 pairs available)
- **E2E test**: Verified feedback pipeline end-to-end — 2 new pairs created and worker processed successfully
- **Orphan cleanup**: Removed test containers (ado-api_test-1, ado-postgres_test-1, ado-redis_test-1, ado-qdrant_test-1)

## Current Production State (03:30 UTC)
- All 6 containers healthy and running
- 50 preference pairs (48 real + 2 test)
- 110 KG entities, 126 KG relations
- 200 SFT pairs ready for training
- 1002 DPO pairs available at `/opt/ado/data/training_new/dpo_export.jsonl`
- Feedback worker active, processing every 10 minutes
- Daily iteration cron: 06:00 daily
- Auto eval cron: 04:00 daily
