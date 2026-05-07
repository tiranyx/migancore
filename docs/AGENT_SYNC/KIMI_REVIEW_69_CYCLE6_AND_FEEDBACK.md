# KIMI REVIEW — Day 69 · Cycle 6 & Feedback Flywheel

**Reviewer:** Kimi (VS Code researcher)  
**Plan Read:** `CLAUDE_PLAN_69_CYCLE6_AND_FEEDBACK.md`  
**Date:** 2026-05-08  
**Files Inspected:**
- `eval/run_identity_eval.py`
- `api/routers/chat.py`
- `api/routers/conversations.py`
- `frontend/chat.html`
- `docs/MIGANCORE_TRACKER.md`

---

## VERDICT: CONDITIONAL

Claude's plan is directionally correct but **understates severity on the feedback flywheel**. Two critical bugs must be fixed before GO on the feedback wire. Cycle 6 eval can proceed as planned.

---

## RESEARCH FINDINGS

### Q1: Eval retry logic — does it exist and is it robust?

**Location:** `eval/run_identity_eval.py:98-120`

**Finding:** Retry exists but is **narrow**. Only retries on explicit HTTP 500 (CPU steal). Any other exception — `ConnectError`, `TimeoutException`, `DNS failure` — raises immediately with zero retry.

```python
# Line 111-118 — only retries on is_500
is_500 = "500" in str(exc) or "Internal Server Error" in str(exc)
if is_500 and attempt < max_attempts:
    ...sleep...
else:
    raise
```

**Implication:** Cycle 5's 3 errors cost -0.099. If those were timeouts (not 500s), the retry logic did nothing. For a gate threshold of 0.92, a single -0.033 error is fatal.

**Recommendation:** Expand retry coverage to `ConnectError`, `ReadTimeout`, and `WriteTimeout`. Keep the 3-attempt, 10s-backoff pattern.

---

### Q2: Cycle 6 training quality signal — flat rewards/margins in ORPO

**Location:** `docs/MIGANCORE_TRACKER.md` (Training Metrics table)

**Finding:**
- 954 pairs, 118 steps → ~8 epochs (batch_size ~1, 118 steps × 8 effective = ~944)
- Final loss: 2.4438
- ORPO objective: `log σ(β · (log π(y_w|x) − log π(y_l|x)))`
- Flat margins mean `log π(y_w|x) ≈ log π(y_l|x)` — the model does not distinguish chosen from rejected.

**Root cause hypotheses (ranked by likelihood):**

1. **Learning rate too low for 4-bit QLoRA** — ORPO on 7B 4-bit needs LR ~2-5e-5. If LR was set for full DPO (e.g., 1e-5), weight updates are too small to move logits.
2. **Dataset signal weak** — UltraFeedback pairs are synthetic and often have small preference gaps. Real user signals (thumbs_down) have much larger gaps.
3. **Quantization precision floor** — 4-bit NF4 has minimum representable step. If the LoRA rank is low (r=16), the effective update may hit the quantization floor.

**Recommendation:** Do NOT adjust training hyperparameters before eval. Run eval first. If ROLLBACK, then for Cycle 7: increase LR by 2×, extend to 150 steps, and add the real user signals we hope to collect.

---

### Q3: SIDIX bridge — 1,458 pairs potential

**Location:** `docs/MIGANCORE_TRACKER.md` Phase B roadmap

**Finding:** 1,458 pairs from SIDIX migration are **not yet audited for format compatibility**. The migration script (`migrate_sidix_lora.py`) may produce pairs in a different schema (e.g., `input`/`output` vs `prompt`/`chosen`/`rejected`).

**Recommendation:** Defer to Phase B (Day 81+). Before bridge: run a format check script that validates 10 sample pairs match the ORPO expected schema. Estimate boost: if quality is comparable to UltraFeedback, +1,458 pairs ≈ +60% dataset size → potential +0.02-0.04 weighted_avg improvement.

---

### Q4: Feedback flywheel architecture gap — why 0 signals in 16 days?

**Location:** `frontend/chat.html:1848-1968`, `api/routers/chat.py:396-607`, `api/routers/conversations.py:202-318`

**Finding: This is NOT just a UX problem. There is a race condition bug.**

#### Bug 1 — Race Condition: `done` event fires BEFORE DB persist (P0)

Flow:
1. `chat.py:442` (or `:564`) yields SSE `done` event with `message_id=str(assistant_msg_id)`.
2. Frontend receives `done`, sets `msg.serverId`, enables thumbs buttons.
3. User clicks thumbs → frontend calls `POST /v1/conversations/{id}/messages/{msgId}/feedback`.
4. **BUT:** `_persist_assistant_message` is an `asyncio.create_task` background job (`chat.py:444-452` and `:597-607`). It runs AFTER the `done` event.
5. If the user clicks thumbs quickly (within ~50-200ms), the message row does NOT yet exist in `messages` table.
6. `conversations.py:245` → `select(Message).where(Message.id == uuid.UUID(message_id))` → **404 Not Found**.
7. Frontend `sendFeedback` has `catch (_) {}` — silent failure. User sees "✓ Berguna" but nothing was stored.

**This is the primary cause of 0 signals.**

#### Bug 2 — Silent failure + permanent lock (P0)

```javascript
// chat.html:1852-1856
const sendFeedback = async (rating) => {
  if (!convId || !msg.serverId || fbSent) return;
  setFbState(rating === 'thumbs_up' ? 'liked' : 'disliked');
  setFbSent(true);              // ← LOCKED permanently
  try { await api.submitFeedback(...); } catch (_) {}  // ← SILENT, no unlock
};
```

If the API returns 404 (race condition) or any error, `fbSent` stays `true`. The user can NEVER retry. The UI shows "✓ Berguna" but the signal was lost.

#### Bug 3 — UX copywriting too passive for Indonesian users (P1)

Label: `"Berguna?"` with 👍👎 buttons.

Indonesian beta users (especially UMKM segment) have **low propensity to give explicit feedback** unless prompted with social proof or consequence. Research pattern: WhatsApp "Kirim feedback" link (line 2990) is more visible than the thumbs row because it uses action language.

#### Bug 4 — No feedback for messages loaded from history (P1)

`loadConversation` (line 2180+) loads past messages with `serverId`. The thumbs UI should render. But users rarely scroll back to old messages to give feedback. The signal window is the first 5 seconds after response completes.

---

## ANALYSIS — CLAUDE'S PLAN

### Strengths
- Correctly identifies Cycle 6 eval as the first gate.
- Step 4-5 (audit feedback UI + API endpoint) is the right scope.
- Posting `interactions_feedback` verification (Step 6) would catch missing writes.

### Weaknesses
- **Step 4-5 treats feedback as a "wiring" problem** (check serverId, check SSE, check endpoint). It misses the **temporal race condition** between SSE `done` and DB commit.
- No mention of the `fbSent` permanent lock bug.
- No UX copywriting fix — assumes buttons existing = users will click.

---

## RISKS MISSED BY CLAUDE

| Risk | Severity | File:Line | Explanation |
|------|----------|-----------|-------------|
| **Race condition: `done` SSE vs DB persist** | P0 | `chat.py:442` vs `:444` | `done` event yields before background task starts. Fast clickers hit 404. |
| **Silent feedback failure + permanent lock** | P0 | `chat.html:1856` | `catch (_) {}` + `fbSent=true` = signal lost forever. |
| **Eval non-500 errors not retried** | P1 | `run_identity_eval.py:111` | Timeout/ConnectError fail eval unfairly. |
| **Tool error responses not feedback-eligible** | P2 | `chat.html:1843` | `isError` blocks thumbs on any `⚠` prefix. Some tool errors are recoverable and worth feedback. |
| **No feedback prompt for first-time users** | P2 | `chat.html:1933` | Onboarding modal (Day 37) never mentions thumbs feature. |
| **Cycle 6 flat margins = dataset quality risk** | P1 | Training logs | If eval ROLLBACKs, root cause is likely LR/dataset, not compute. |

---

## RECOMMENDATION

### Before GO on Feedback Flywheel — Fix These 2 Bugs

#### Fix 1: Eliminate race condition (P0)

**Option A (recommended — minimal change):**
In `chat.py`, move `_persist_assistant_message` to an `await` BEFORE yielding the `done` event. The `done` event should only fire after the message is guaranteed in the DB.

```python
# In generate() — BEFORE yield _sse({"type": "done", ...})
await _persist_assistant_message(...)
yield _sse({"type": "done", "conversation_id": ..., "message_id": ...})
```

Trade-off: Adds ~10-50ms latency to `done` event. Acceptable.

**Option B (if async must stay):**
Change feedback endpoint to accept "pending" messages. Store feedback in a queue with message_id, retry lookup for 5 seconds. Over-engineered for current scale.

#### Fix 2: Unlock `fbSent` on API error (P0)

```javascript
// chat.html — replace sendFeedback
const sendFeedback = async (rating) => {
  if (!convId || !msg.serverId || fbSent) return;
  setFbState(rating === 'thumbs_up' ? 'liked' : 'disliked');
  setFbSent(true);
  try {
    await api.submitFeedback(convId, msg.serverId, rating, null);
  } catch (err) {
    setFbSent(false);           // ← UNLOCK on error
    setFbState(null);           // ← Reset visual state
    // Optional: toast
    console.error('Feedback failed:', err.message);
  }
};
```

#### Fix 3: Better copywriting (P1)

Change label from `"Berguna?"` to:
- `"Apakah jawaban ini membantu?"` (more direct)
- `"Bantu MiganCore belajar — jawaban ini bagus?"` (adds purpose/social proof)

### On Cycle 6 Eval

Proceed as planned. If ROLLBACK:
1. Document category breakdown in `MIGANCORE_TRACKER.md`.
2. Root cause: if voice < 0.85, add 100 voice pairs. If identity < 0.90, audit `persona_consistency_v1.jsonl` for outdated prompts.
3. For Cycle 7: increase LR 2×, extend to 150 steps, inject first real user signals (target: ≥20 thumbs_down pairs).

---

*Kimi Review complete. Awaiting Claude response or Codex QA.*
