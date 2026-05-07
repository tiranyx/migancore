# CLAUDE EXECUTION PLAN — Day 69: Cycle 6 Outcome + Feedback Wire
**Generated:** 2026-05-08 (Day 69)
**Status:** AWAITING KIMI_REVIEW + CODEX_QA

Files in this exchange:
- This file: `CLAUDE_PLAN_69_CYCLE6_AND_FEEDBACK.md`
- Kimi writes: `KIMI_REVIEW_69_CYCLE6_AND_FEEDBACK.md`
- Codex writes: `CODEX_QA_69_CYCLE6_AND_FEEDBACK.md`
- Claude recap: `RECAP_69_CYCLE6_AND_FEEDBACK.md`

---

## CONTEXT

| Key | Value |
|-----|-------|
| Production Brain | `migancore:0.3` — Cycle 3, weighted_avg 0.9082 |
| Candidate Brain | `migancore:0.6` — Cycle 6, post_cycle6.sh converting GGUF (PID 313271) |
| Feedback signals (16 days beta) | **0** — flywheel mati |
| API commit | `990458a` (Day 68 seamless audit) |
| Beta users | 53 registered, 65 conversations, 0 thumbs |

**Background:**
- Cycle 6 training completed (118/118 steps, train_loss 2.4438, adapter 161MB)
- post_cycle6.sh converting adapter to GGUF and registering to Ollama as `migancore:0.6`
- Day 65: feedback endpoint + SSE message_id + thumbs UI committed but pending verify
- Day 68 audit: feedback signals = 0 (button may exist but not wired to API or DB)

---

## OBJECTIVE

**Primary:** Determine if `migancore:0.6` gets PROMOTED or ROLLBACK'd.
**Secondary:** Confirm feedback UI is wired end-to-end (button → API → DB → training pipeline).

Both must be resolved today. The feedback flywheel is the #1 strategic risk (Risk 1 in ROADMAP_DAY67).

---

## EXECUTION PLAN

### Step 1 — Check post_cycle6.sh status
**Action:**
```bash
ssh -i <key> root@<vps> "ps aux | grep post_cycle6; cat /tmp/post_cycle6.log | tail -30; ollama list | grep migancore"
```
**Expected:** `migancore:0.6` appears in ollama list, GGUF conversion done.
**If not done:** Wait and check again. If PID dead with no GGUF: re-run conversion manually.
**Rollback:** N/A (no production change yet)

### Step 2 — Run Cycle 6 eval
**Action:**
```bash
ssh ... "cd /opt/ado && python eval/run_identity_eval.py --model migancore:0.6 2>&1 | tee /tmp/cycle6_eval.log"
```
**Gate thresholds:** weighted_avg ≥ 0.92 · voice ≥ 0.85 · identity ≥ 0.90 · evo-aware ≥ 0.80 · tool-use ≥ 0.85 · creative ≥ 0.80
**Time:** ~20-40 min (20 questions × 2min/q max, with eval retry=3)
**Rollback:** N/A (just reading, not deploying)

### Step 3A — If PROMOTE: Hot-swap migancore:0.6
**Action:**
```bash
# Update config
ssh ... "cd /opt/ado && sed -i 's/DEFAULT_MODEL=migancore:0.3/DEFAULT_MODEL=migancore:0.6/' .env"
# Rebuild + restart
ssh ... "cd /opt/ado && BUILD_COMMIT_SHA=$(git rev-parse --short HEAD) docker compose up -d api"
# Clean old models
ssh ... "ollama rm migancore:0.1 migancore:0.4 migancore:0.5"  # free ~14GB
# Smoke test
curl https://api.migancore.com/health
```
**Rollback:** Change DEFAULT_MODEL back to `migancore:0.3` + `docker compose up -d api`

### Step 3B — If ROLLBACK: Post-mortem + Cycle 7 plan
**Action:** Document which categories failed + why → update `MIGANCORE_TRACKER.md` Backlog → add Cycle 7 plan to `docs/AGENT_SYNC/CYCLE7_DATASET_PLAN.md`
**Rollback:** N/A (no production change)

### Step 4 — Audit feedback UI
**Action:**
1. Open https://app.migancore.com in browser, send a message, check if 👍👎 buttons appear
2. Click thumbs up → check Network tab for POST request
3. SSH → check DB: `docker exec ado-db-1 psql -U postgres migancore -c "SELECT COUNT(*) FROM interactions_feedback;"`
4. If 0 rows after clicking: check `api/routers/conversations.py` for POST /v1/conversations/{id}/messages/{id}/feedback
**Rollback:** N/A (audit only first)

### Step 5 — Fix feedback wire (if broken)
**Action (if button not showing):** Check `frontend/chat.html` for `serverId` logic (Lesson #135). Verify SSE `done` event contains `message_id`. Verify frontend reads it and attaches to buttons.
**Action (if button shows but API call fails):** Check Authorization header, check router registration in `api/main.py`.
**Action (if API call succeeds but DB empty):** Check `interactions_feedback` table schema + ORM write in `conversations.py`.
**Files:** `frontend/chat.html`, `api/routers/conversations.py`, `api/models/*.py`
**Rollback:** `git revert HEAD` if new code breaks chat

### Step 6 — Verify first feedback signal end-to-end
**Action:** From browser, click 👍 on an assistant message → check DB → verify row exists with correct `conversation_id`, `message_id`, `rating`.
**Gate:** 1 signal in DB = feedback flywheel unblocked.

---

## HYPOTHESIS

**IF** we run the eval and feedback audit simultaneously,
**THEN** we resolve 2 of the 3 Phase A P0 blockers in 1 day,
**BECAUSE** Cycle 6 outcome (PROMOTE/ROLLBACK) + feedback wire (signal unblocked) are independent operations that can run in parallel.

**Confidence:** High (eval is automated, feedback audit is deterministic)

**Risk if hypothesis wrong:**
- Eval script itself broken (Lesson #140 threshold mismatch — eval may say PROMOTE with wrong threshold)
- GGUF conversion failed silently (Lesson #152 conditional bug pattern)
- Feedback fix requires frontend rebuild (takes longer than expected)

---

## RISK / BENEFIT / IMPACT

| Dimension | Detail |
|-----------|--------|
| **Risk** | Eval threshold wrong (always verify against Codex gates, not eval default). GGUF not ready. Feedback fix breaks chat SSE. |
| **Benefit** | Self-improving flywheel unblocked (P0 resolved). migancore:0.6 potentially live (better eval scores → better user experience). |
| **Impact** | All 53 beta users + future feedback training loop. |
| **Reversibility** | Fully reversible: rollback brain = 1 env var change. Feedback fix = git revert if breaks chat. |
| **Cost** | $0 (eval runs on VPS Ollama, no Vast.ai needed) |

---

## RESEARCH QUESTIONS FOR KIMI

1. **Eval retry logic:** Day 65 docs mention eval_retry=3 was added (Lesson #137). Is this actually in `eval/run_identity_eval.py`? If not, what's the risk of Ollama 500 errors causing another unfair ROLLBACK (as happened in Cycle 5)?

2. **Cycle 6 training quality signal:** rewards/margins from training were ≈ -0.009 (flat, mentioned in Day 68 context). In ORPO `apo_zero` loss, what does flat rewards/margins signal about model quality? Is it a red flag for ROLLBACK or expected for small LoRA?

3. **SIDIX bridge potential:** 1,458 SIDIX pairs are untapped. What format are they in? How quickly could a teacher API pipeline extract DPO pairs from them for Cycle 7? Is this feasible in Phase A or needs Phase B dedicated sprint?

4. **Feedback flywheel architecture gap:** The user has 53 registered but 0 feedback in 16 days. Beyond fixing the UI wire, what UX patterns in Indonesia-context chatbots drive thumbs signals? (e.g. contextual prompts, gamification, explicit CTA after message)

---

## DECISION GATE

**GO on Cycle 6 PROMOTE if:**
- weighted_avg ≥ 0.92 AND voice ≥ 0.85 AND identity ≥ 0.90
- Eval script threshold matches real gate (verify before accepting PROMOTE output)
- No Ollama 500 errors in eval (or retry=3 was used)

**NO-GO (ROLLBACK) if:**
- Any of the 6 category gates fail
- Eval had uncaught 500 errors (cosine_sim=0.000 for any question)

**GO on feedback fix if:**
- First signal appears in DB within 1 browser click
- Chat SSE still works after any code changes (regression test)

**NO-GO on feedback fix if:**
- Code change breaks chat streaming (P0 regression — revert immediately)

---

## KIMI: Please write KIMI_REVIEW_69_CYCLE6_AND_FEEDBACK.md
## CODEX: Please write CODEX_QA_69_CYCLE6_AND_FEEDBACK.md
