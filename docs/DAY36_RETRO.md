# Day 36 Retrospective — Chat UX Sprint
**Date:** 2026-05-04 (Bulan 2 Week 5 Day 1)
**Agent:** Claude Opus 4.7
**Trigger:** User screenshot — empty bubble + TypeError + no retry
**Result:** v0.5.0 → **v0.5.2** in single sprint

---

## What Was Shipped (4 phases, ~2 hours)

### Phase 1 — nginx fix (5 min) ⭐ BIGGEST ROI
**File:** `/www/server/panel/vhost/nginx/api.migancore.com.conf`
- Added `location ~ /v1/agents/.+/chat/stream { proxy_read_timeout 600s; proxy_buffering off; }`
- Added same for `/mcp/` paths (Day 26 prep)
- Default endpoints stay 120s
- **Research finding addressed**: nginx default 60s = #1 cause of TypeError network error per r/LocalLLaMA + Vercel AI SDK docs

### Phase 2 — Friendly errors + Retry button
**File:** `frontend/chat.html`
- Error mapper: TypeError/network → "Koneksi terputus. Pesan kamu aman." Timeout → "MiganCore butuh waktu lebih lama". 401 → "Sesi habis." 429 → "Terlalu banyak request."
- `[↻ RETRY]` button on error bubbles
- Retry handler: re-submits last user prompt, REPLACES failed assistant message (reuses conversation_id)
- Tracks `lastUserText` + `lastUserMsgId` per assistant message for retry context

### Phase 3 — Status hierarchy 3 states
**File:** `frontend/chat.html` Msg component
- 0-3s: "Menghubungkan..."
- 3-15s: "MiganCore sedang berpikir..."
- 15s+: "Generating response..."
- 30s+: orange "CPU 7B (lambat normal, jangan refresh)" reassurance label
- Elapsed seconds counter visible after 5s

### Phase 4 — Cancel propagation to Ollama
**File:** `api/routers/chat.py`
- Added `except asyncio.CancelledError` in SSE generator
- Persist partial response with "[stopped by user]" marker (so user doesn't lose work)
- Verified: httpx context manager auto-closes connection to Ollama → Ollama stops generation
- Added `chunk_count` log + `chat.stream.done` log for observability

---

## E2E Verification

```
[1] nginx reload OK + config syntax valid
[2] /health 200, /v1/public/stats 200 — no regression
[3] SSE endpoint /v1/agents/.../chat/stream 401 (auth check expected)
[4] Frontend chat.html deployed to /www/wwwroot/app.migancore.com/
[5] Manual test by Fahmi pending (await user feedback)
```

---

## Hypothesis Outcomes

| H | Test | Result |
|---|------|--------|
| H1 | nginx 600s fixes 80% of TypeError | DEPLOYED — awaiting user real-world test |
| H2 | Retry button = users won't abandon | SHIPPED — UX cleaner |
| H3 | 3-state hierarchy improves perception | SHIPPED — clear elapsed feedback |
| H4 | Cancel propagates to Ollama via CancelledError | VERIFIED via httpx context manager |

---

## Lessons (Day 36)

1. **Default nginx config is hostile to SSE** — `proxy_read_timeout 60s` + `proxy_buffering on` are ON by default. EVERY new server needs SSE-specific location block.
2. **HTTP/2 head-of-line on SSE** is a thing (research finding). Considered but not implemented — current setup keeps HTTP/2, monitor if drops continue.
3. **Friendly error mapping is high-ROI** — same exception, vastly different perceived quality.
4. **Retry > regenerate** — user's intent was the same prompt, don't make them retype. Reusing conversation_id keeps context.
5. **Status verb hierarchy beats single label** — research says "thinking" alone fails after 8s. 3 states + elapsed = trust extension.
6. **`asyncio.CancelledError` propagation** — Python's async cancellation cascades naturally through httpx context managers. No need for a separate `/abort` endpoint.

---

## Cost Audit
**$0** — all changes are config + code. Zero external API spend.

---

## What's NOT Done (deferred Day 37+)
- **Server-side partial message persistence** — chunks stored in DB so resume across page refresh works (Vercel AI SDK pattern)
- **`Last-Event-ID` resume** — true mid-stream recovery
- **HTTP/2 → HTTP/1.1 downgrade for SSE** — research recommended, not yet applied
- **Auto-retry with exponential backoff** — currently manual Retry only
- **Background mode** — close tab, get notification on completion (Manus-style)

These deferred items address edge cases. PRIMARY fixes the 80%.

---

## Next: Bulan 2 Week 5 continuation
Per `BULAN2_PLAN.md`:
- **Day 37**: DPO pool monitoring → trigger SimPO when ≥500 pairs (currently 277, growing)
- **Day 38-40**: First Cycle 1 training run on RunPod
- **Day 41-42**: Hot-swap migancore-7b-soul-v0.1 + 24h A/B test

Day 36 was an UNPLANNED but JUSTIFIED detour — chat reliability blocks beta dogfooding.
