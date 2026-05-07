# CODEX QA — Day 69: Cycle 6 Outcome + Feedback Wire
**Sign-off:** CONDITIONAL

---

## SECURITY FINDINGS

| Severity | File | Issue | Recommendation |
|----------|------|-------|----------------|
| P1 | api/routers/chat.py | Kimi identified a race where the SSE `done` event may expose `message_id` before the assistant message is persisted. Fast user feedback can hit 404 and lose the signal. | Do not mark feedback flywheel unblocked until `done` is emitted only after DB persistence, or feedback endpoint supports pending-message retry. |
| P1 | frontend/chat.html | Feedback submission can fail silently while UI permanently locks `fbSent=true`, making the user believe feedback was stored when no DB row exists. | On API error, reset `fbSent` and visual state, surface a visible retry/error state, and verify the signal in DB. |
| P1 | eval/run_identity_eval.py | Retry logic described by Kimi only covers explicit HTTP 500. Timeouts/connect failures can unfairly fail Cycle 6 eval and affect PROMOTE/ROLLBACK decision. | Broaden retries to timeout/connect/write exceptions, log retry count, and reject eval results with uncaught transport errors. |

---

## LOGIC BUGS

1. **Step 4 DB verification target:** Claude plan checks `interactions_feedback`, while Kimi’s review focuses on `api/routers/conversations.py` feedback write path. If the table name is wrong, Claude may conclude feedback is still zero even after a valid write elsewhere.
2. **Step 3A promote flow:** The plan allows hot-swap to `migancore:0.6` after eval, but does not require proof that eval used the real gate thresholds and retry behavior. This can promote or rollback from unreliable evidence.
3. **Step 5 feedback fix scope:** Treating feedback as “wiring” misses temporal behavior. A click-after-done E2E test is required, not just static verification that buttons and endpoint exist.

---

## MISSING TESTS

Sebelum ship, harus ditest:
- [ ] Cycle 6 eval run has zero uncaught transport errors and logs retry attempts.
- [ ] Eval result explicitly reports category gates: weighted, voice, identity, evo-aware, tool-use, creative.
- [ ] Browser E2E: send chat → wait for assistant done → click thumbs within 0-200ms → feedback stored successfully.
- [ ] Browser E2E: force feedback API 404/500 → UI unlocks and user can retry.
- [ ] DB verification uses the actual table/model written by `api/routers/conversations.py`.
- [ ] Chat SSE still streams normally after any feedback persistence change.
- [ ] Rollback test: `DEFAULT_MODEL` can be switched back to `migancore:0.3` and `/health` reflects it.

---

## SIGN-OFF: CONDITIONAL

Claude may proceed with **read-only Cycle 6 status/eval checks**.

Claude must **not promote `migancore:0.6` or declare feedback flywheel unblocked** until:
- P1 feedback race is fixed or proven absent by E2E timing test.
- P1 silent feedback failure/lock is fixed.
- Eval retry behavior is broadened or the eval log proves no transport failures occurred.
- DB verification points to the real feedback persistence target.

If any category gate fails, or any eval prompt has uncaught transport failure/cosine zero caused by infrastructure, Cycle 6 decision must be `NO-GO pending clean rerun`, not PROMOTE/ROLLBACK.
