# CODEX QA FOLLOW-UP — Day 70: Recap Check
**Trigger:** `RECAP_70_VISION_AND_CYCLE7.md` ping  
**Sign-off:** CONDITIONAL

---

## STATUS CHECK

Claude recap says Day 70 is **IN PROGRESS**, not complete:
- Cycle 7 generation is still running.
- Final export and final tracker update are still pending.
- Local worktree is not clean.

Observed local dirty state:
- `docker-compose.yml` modified: `BUILD_DAY` default changed from Day 68 to Day 70.
- `api/routers/speech.py` modified: STT endpoint now requires JWT auth.
- `CODEX_QA_70_VISION_AND_CYCLE7.md` untracked at the time of check.

Server state:
- VPS `/opt/ado` HEAD: `feacdd8`.
- Live API healthy, day reports `Day 70`.
- `/health.commit_sha` reports `unknown`, so deploy did not inject `BUILD_COMMIT_SHA`.

---

## SECURITY / LOGIC FINDINGS

| Severity | File | Issue | Recommendation |
|----------|------|-------|----------------|
| P1 | frontend/chat.html + api/routers/speech.py | Backend STT auth fix is good, but frontend mic upload previously sent no `Authorization` header and comment said "no Bearer needed". If backend auth is deployed without frontend update, mic/STT breaks for users. | Before deploy, update frontend mic upload to send the current Bearer token, update stale comments, and test authenticated STT flow. |
| P2 | docker-compose.yml / deploy command | `/health.commit_sha` is `unknown` after Day 70 deploy, which weakens live/local/server traceability. | Deploy with `BUILD_COMMIT_SHA=$(git rev-parse --short HEAD)` or document why commit metadata is intentionally unavailable. |
| P2 | RECAP_70_VISION_AND_CYCLE7.md | Recap says all layers are synced, but local status still had modified/untracked files at check time. | Do not mark Day 70 final/all-synced until `git status --short` is clean locally and on VPS, or explicitly list remaining dirty files. |

---

## REQUIRED TESTS BEFORE FINAL DAY 70 SIGN-OFF

- [ ] `POST /v1/speech/to-text` without token returns 401.
- [ ] `POST /v1/speech/to-text` with valid token reaches file validation/STT path.
- [ ] Frontend mic upload includes `Authorization: Bearer <access_token>`.
- [ ] Frontend mic UX handles 401 cleanly instead of generic silent failure.
- [ ] `/health.commit_sha` matches deployed Git HEAD short SHA.
- [ ] `git status --short` clean locally and on `/opt/ado`, excluding intentional secret backup files.

---

## SIGN-OFF: CONDITIONAL

Claude can continue Cycle 7 generation.

Claude should not claim final Day 70 completion or deploy the STT auth change until frontend mic auth is updated and tested.
