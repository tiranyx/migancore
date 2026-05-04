# DAY 36 — Chat UX Sprint: "Trust That The System Isn't Broken"
**Date:** 2026-05-04 (Bulan 2 Week 5 Day 1)
**Agent:** Claude Opus 4.7
**Trigger:** User screenshot showed empty bubble + TypeError network error + no retry
**Approval status:** AWAITING

---

## 🎯 NORTH STAR

> **"Your bottleneck isn't model quality — it's trust that the system isn't broken. On a 7B-CPU stack, every silent second feels like a crash."** (research synthesis)

Day 36 = make MiganCore chat **feel reliable** even when Ollama takes 60s. No more silent waits, no more raw error messages.

---

## 📊 STATE — Audit (3 issues from screenshot)

| Issue | Status | Severity |
|-------|--------|----------|
| 1. Empty assistant bubble (no feedback) | ✅ FIXED v0.5.1 (just deployed) | Critical |
| 2. TypeError network error mid-response | ❌ Day 25 partial fix didn't hold | Critical |
| 3. No retry mechanism after error | ❌ Not implemented | High |

**Root cause Issue #2 (research finding):** nginx `proxy_read_timeout` default 60s — kills SSE on long Ollama responses. Day 25 backend heartbeat won't help if nginx already cut connection.

---

## 🎯 OBJECTIVES (Priority Order)

### PRIMARY (must-ship)
1. **nginx fix** — `proxy_read_timeout 600s` on `api.migancore.com` for SSE endpoints (1-line change, biggest ROI per research)
2. **Friendly error mapping** — replace "TypeError: network error" with "Koneksi terputus. Pesan kamu aman. [Retry]"
3. **Retry button** on failed assistant messages — re-submits same prompt
4. **Status hierarchy in indicator** — "Connecting..." → "Thinking..." → "Generating..." (currently just one state)
5. **Cancel button improvement** — current Stop only aborts client-side, doesn't kill Ollama. Add proper abort.

### SECONDARY (if time permits)
6. **HTTP/2 → HTTP/1.1 for SSE endpoint** (nginx config — research says HTTP/2 has head-of-line blocking on dropped frames)
7. **Server-side partial message persistence** — store assistant chunks in DB so resume is possible
8. **Resume mid-stream** — `Last-Event-ID` header pattern (Vercel AI SDK pattern)

### DEFERRED (Day 37+)
- ❌ Extended thinking trace (Claude.ai style)
- ❌ Status verb rotation ("Analyzing... Composing...")
- ❌ WebSocket fallback
- ❌ "Run in background" mode

---

## 📐 KPIs

| Metric | Day 36 baseline | Day 36 target |
|--------|----------------|---------------|
| TypeError network error rate | ~30% (recurring) | **<5%** |
| Time to visible feedback after submit | 30-90s (silent) | **<200ms** (placeholder) |
| User can recover from error without retyping | NO | **YES** (Retry button) |
| Cancel actually stops Ollama compute | NO (client-only) | **YES** |
| Status text matches actual state | NO (always "thinking") | **YES** (3 states) |

**Exit criteria:** All PRIMARY shipped + manual test passes from Fahmi's laptop.

---

## 🔬 HYPOTHESIS + ADAPTATION

### H1: nginx `proxy_read_timeout 600s` fixes 80% of TypeError
- Test: deploy + manual chat with long-response prompt
- Adapt fail: investigate Cloudflare-side timeout (not in our control if behind CF)

### H2: Retry button + friendly error = users won't abandon
- Test: Fahmi try error scenario, retries, gets success
- Adapt fail: add auto-retry with exponential backoff

### H3: Status hierarchy ("Connecting → Thinking → Generating") improves perception
- Test: Fahmi subjective assessment
- Adapt fail: revert to single state with elapsed timer only

---

## ⚠️ RISKS

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| nginx config breaks other endpoints | Low | High | Apply only to `/v1/agents/*/chat/stream` location, test other endpoints after reload |
| HTTP/1.1 downgrade slows non-SSE requests | Low | Low | Only on stream endpoint, REST stays HTTP/2 |
| Server-side partial persistence adds DB load | Medium | Medium | Defer to SECONDARY — only if PRIMARY done early |
| Retry button creates duplicate conversations | Medium | Medium | Reuse same conversation_id, mark old assistant_message as superseded |
| Auto-retry storms a degraded Ollama | High | High | Cap at 2 retries, exponential backoff (2s, 8s) |

---

## 💰 COST

**$0** — all changes are config + code. No new APIs, no RunPod, no infra spend.

---

## 📅 EXECUTION PLAN

### Phase 1 — nginx fix (5 min) ← BIGGEST ROI
1. SSH VPS, edit `/www/server/panel/vhost/nginx/api.migancore.com.conf`
2. Add `location ~ /v1/agents/.+/chat/stream { proxy_read_timeout 600s; proxy_buffering off; ... }`
3. Reload nginx, verify with curl

### Phase 2 — Friendly error + Retry (45 min)
1. Update chat.html error handling: map TypeError → "Koneksi terputus..."
2. Add `[Retry]` button on error bubbles
3. Retry handler: re-submit last user message with same conversation_id
4. Test: simulate network drop (DevTools) → verify Retry works

### Phase 3 — Status hierarchy (30 min)
1. Update ThinkingIndicator with 3 states based on event timing
   - 0-3s: "Connecting..." 
   - 3-15s: "MiganCore sedang berpikir..."
   - 15s+: "Generating response... ({elapsed}s)"
2. Maybe add subtle pulsing border color shift per state

### Phase 4 — Cancel improvement (30 min)
1. Backend: `POST /v1/agents/{id}/chat/abort` endpoint
2. Frontend: Stop button hits abort + abort fetch
3. Verify Ollama process stops (CPU returns to baseline)

### Phase 5 — E2E verification (15 min)
1. Manual test from Fahmi laptop:
   - Long-response prompt → no TypeError
   - Force-disconnect → Retry button works
   - Stop button → CPU drops immediately
   - Status text reflects actual state

### Phase 6 — Document + commit (15 min)
1. Update day36_progress.md, CHANGELOG, CONTEXT
2. Daily log
3. Single commit per phase OR bundled v0.5.2

**Total estimated:** ~2.5 hours

---

## 🛡️ ANTI-PATTERN COMPLIANCE

| Anti-pattern (research) | MiganCore guardrail |
|-------------------------|---------------------|
| Empty bubble | ✅ Fixed v0.5.1 — thinking indicator with dots |
| Raw error message | Phase 2 — friendly mapping |
| No retry mechanism | Phase 2 — visible Retry button |
| HTTP/2 head-of-line on SSE | Phase 6 (SECONDARY) |
| No abort signal to model | Phase 4 — proper abort endpoint |

---

## ❓ DECISIONS NEEDED

1. **Approve Day 36 plan?** (PRIMARY items are non-negotiable production fixes — recommend YES)
2. **OK pakai version 0.5.2** for this fix?
3. **Implement SECONDARY** items today (HTTP/2 downgrade, partial persistence) atau defer Day 37?
4. **Any additional UX issues** kamu lihat di chat yang aku belum catat?

---

## 📚 LESSONS APPLIED FROM PRIOR DAYS

- **Day 25 lesson re-validated:** SSE drops are systemic, not one-off. Backend heartbeat is necessary but NOT sufficient — also need nginx config + frontend recovery.
- **WEEK4_DECISIONS_LOG rule:** Don't add features until quality of existing features is solid. Chat reliability > new agent specialists.
- **"Win 1 thing completely":** Day 36 = chat feels solid. Then Day 37 onward = Cycle 1 SimPO + multimodal.

---

## 🎁 WHAT THIS UNLOCKS

After Day 36:
- Migancore chat looks **production-grade** (not "beta toy")
- Fahmi can confidently invite 5 beta users without "AI ngebug" complaints
- Foundation laid for Bulan 2 Week 6 (5-user dogfooding)
- Public landing trust strengthened ("if you click 'Chat' you'll have a smooth experience")

---

**Sambil kamu approve, distillation pipeline + synthetic gen tetap jalan di background.**
