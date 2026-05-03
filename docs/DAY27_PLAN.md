# DAY 27 — Long-Lived API Keys + MCP Resources + TTS + Memory Pruning + `migan` CLI
**Date:** 2026-05-04
**Agent:** Claude Opus 4.7 (1m context)
**Type:** Implementation Plan with Hypothesis + Risk + Benefit + Adaptation

---

## VISION ANCHOR

User feedback Day 26: setup MCP terlalu ribet (`curl` token + `claude mcp add` setiap 15 menit). Visi: **ekosistem distribution layer untuk MiganCore tools**. Setelah Day 27, user (Fahmi atau siapa pun di marketplace nanti) bisa:
1. **Sekali setup** (one-line install) → MiganCore tools tersedia di Claude Code/Desktop/Cursor selamanya
2. **`@migancore:resource`** mention untuk attach context (conversation history, workspace files, persona)
3. **Voice output** untuk creative agents (TTS demo dengan ElevenLabs free tier)
4. **Self-cleaning memory** — Qdrant tidak bloat infinitely

Ini adalah Day 27 — **fondasi distribution + UX polish**. Day 28 = Admin Dashboard + handoff.

---

## OBJECTIVES

**Primary (User-pain blockers):**
1. **Long-lived API keys** — `mgn_live_<id>_<secret>` format, hashed via HMAC-SHA256, supports revoke/expire/scopes
2. **`migan` CLI installer** — one-liner: `curl -sL get.migancore.com/setup.sh | bash` → done

**Secondary (capability expansion):**
3. **MCP Resources** — expose conversations + workspace files + agent SOUL as resources
4. **TTS tool** — ElevenLabs `eleven_flash_v2_5`, returns audio bytes/URL
5. **Memory pruning daemon** — daily Qdrant cleanup of points >30 days + low importance score

**Non-goals (defer):**
- OAuth 2.1 dynamic client registration (Week 4)
- Resource subscriptions (live updates) — too complex for Day 27
- Voice cloning / Pro Voice features

---

## KPI / SUCCESS METRICS

| Metric | Target | How to measure |
|--------|--------|----------------|
| API key generated | `POST /v1/api-keys` returns `mgn_live_*` once, hash stored | curl test |
| API key auth works | MCP request with `Authorization: Bearer mgn_live_*` succeeds | E2E |
| API key revoke works | Revoked key → 401 within 1s (Redis hot-path) | timing test |
| Setup script | `curl ... | bash` → claude mcp add invoked successfully | manual run |
| MCP Resources listed | `resources/list` JSON-RPC returns ≥3 resource templates | curl |
| Resource read works | `resources/read` of `migancore://workspace/{file}` returns content | curl |
| TTS tool callable | `tools/call text_to_speech` → audio data returned | E2E |
| Memory prune cron | Daily task runs, logs `qdrant.prune.done count=N` | log inspection |
| All previous E2E pass | Day 24-26 tests still green | regression |

**Exit criteria for Day 27:** API keys + setup script + at least 1 resource template + TTS tool + prune daemon. All E2E PASS.

---

## HYPOTHESIS (with adaptation triggers)

**H1: HMAC-SHA256 verification < 5ms — fast enough for hot path**
Adaptation: if benchmark > 20ms, add Redis cache `apikey:<hash>:verified` with 60s TTL.

**H2: FastMCP `@mcp.resource()` decorator works for templated URIs**
Adaptation: if URI templates fail with current SDK version, fall back to enumerated `resources/list` with concrete URIs (less elegant but works).

**H3: ElevenLabs returns mp3 bytes directly (no signed URL)**
Adaptation: if mp3 bytes too large for MCP response, upload to fal.ai-style hosting OR base64-encode (with 4MB cap warning).

**H4: Qdrant payload index on `timestamp` makes delete-by-filter < 1s for our scale**
Adaptation: if scale grows beyond what filter handles, switch to scroll+batch-delete pattern.

**H5: Setup script wraps `claude mcp add` cleanly across platforms**
Adaptation: if Windows compatibility fails, ship two scripts (`setup.sh` for Mac/Linux/WSL, `setup.ps1` for Windows).

---

## RISK ASSESSMENT

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| API key leak in logs | High | Critical | Redact `Authorization` header in structlog middleware (universal) |
| API key brute force | Low | High | 256-bit entropy + DB index → infeasible. Monitor rate limit alerts. |
| ElevenLabs free tier exhausted mid-demo | Medium | Low | Show remaining quota in tool response. 10k chars = ~3000 short demos. |
| Memory pruning deletes important data | Low | High | Importance threshold default 0.7, conservative. Audit log every prune run. |
| MCP resources URI traversal | Medium | High | Same `_resolve_workspace_path()` pattern as Day 24. Tested. |
| Setup script breaks on Windows | High | Medium | Ship .ps1 alternative + clear "Windows users see X" docs |
| API key migration breaks existing JWT | Low | Critical | Keep both JWT + API key paths in auth middleware (parallel) |
| `migancore://` URI scheme not recognized by clients | Medium | Medium | Test with Claude Code first; if rejected, switch to standard `file://` style |

---

## BENEFIT ANALYSIS

**User-visible (Day 27):**
- Setup time: 3 commands → 1 command (90s → 10s)
- No re-login every 15 min — token is permanent until revoked
- Voice output enables new use cases (audio summary, accessibility)
- Workspace + conversations attachable via `@` mentions in Claude Code

**Strategic:**
- API key infrastructure = foundation for marketplace billing (per-key usage tracking)
- MCP Resources = MiganCore content becomes citeable in any MCP client
- TTS = entry to multimodal output (text → image → audio = full creative stack)
- Memory pruning = production-ready scaling (no infinite growth)

**Cost:**
- API keys: $0 (existing infra)
- ElevenLabs: $0 (free tier 10k chars/month — sufficient for testing, paid only if scale)
- Memory prune: $0 (background task)
- CLI hosting: $0 (just a shell script in repo, fetched via raw GitHub URL)

---

## EXECUTION PLAN (8 phases, ~5 hours total)

### Phase 1: API Keys — Schema + Service (~45 min)
1. Migration `025_api_keys.sql`: `api_keys` table with `tenant_id`, `prefix`, `key_hash`, `scopes[]`, `expires_at`, `revoked_at`
2. `services/api_keys.py`: `generate_key()`, `verify_key()`, `revoke_key()`
3. Add `API_KEY_PEPPER` to `config.py` (env var)
4. Index `key_hash` + `prefix` in DB

### Phase 2: API Keys — REST endpoints + auth integration (~45 min)
1. `routers/api_keys.py`: `POST /v1/api-keys` (create), `GET /v1/api-keys` (list), `DELETE /v1/api-keys/{id}` (revoke)
2. Update `services/jwt.py` decode → also accept `mgn_live_*` keys (try API key first, fallback JWT)
3. Update `mcp_server.py` JWT middleware → try both JWT and API key
4. Test: create key, use it for `/mcp/` request, verify works

### Phase 3: `migan` CLI Setup Script (~30 min)
1. `scripts/migan-setup.sh` — bash script with email/password prompt, registers API key, runs `claude mcp add`
2. `scripts/migan-setup.ps1` — Windows PowerShell equivalent
3. Document on `docs/MCP_USAGE.md`: one-liner install
4. Test on Linux/WSL

### Phase 4: MCP Resources (~45 min)
1. Add `@mcp.resource("migancore://soul/{agent}")` — agent persona (SOUL.md)
2. Add `@mcp.resource("migancore://workspace/{path}")` — sandboxed file read
3. Add `@mcp.resource("migancore://conversations/{id}")` — conversation transcript
4. Test: `resources/list`, `resources/read` from MCP

### Phase 5: TTS Tool (~30 min)
1. Add `ELEVENLABS_KEY` to `config.py` + `docker-compose.yml`
2. `_text_to_speech()` handler in `tool_executor.py`
3. Returns: base64-encoded mp3 (max 4MB) + duration estimate
4. Add to `skills.json` + `agents.json` + `mcp_server.py`
5. Test: short text → audio bytes back

### Phase 6: Memory Pruning Daemon (~30 min)
1. Add `services/memory_pruner.py` — async loop, daily 03:00 UTC
2. Payload index on `timestamp` + `importance` (migration `026_qdrant_indexes.sql` — actually Python script since Qdrant)
3. Launch from `main.py` lifespan as `asyncio.create_task()`
4. Default: prune points >30 days AND importance < 0.7
5. Test: insert old test points, run prune, verify deleted

### Phase 7: E2E Verification (~30 min)
1. Create API key → use it for `/mcp/` request → success
2. Revoke key → next request → 401
3. `resources/list` → 3 templates returned
4. `resources/read migancore://workspace/hello_day24.py` → content returned
5. `tools/call text_to_speech` → audio bytes
6. Memory prune log shows count of deleted points
7. Day 24-26 regression: chat UI, fal.ai, write_file all still work

### Phase 8: Documentation + Deploy (~45 min)
1. `day27_progress.md` (memory)
2. CHANGELOG v0.4.5 entry
3. SPRINT_LOG Day 27 entry
4. CONTEXT.md update (v0.4.5)
5. `docs/MCP_USAGE.md` major update — show one-line install + API key flow + resources
6. Single commit + push + deploy + final verify

---

## ADAPTATION PROTOCOL (per phase)

| Phase | If fail | Fallback |
|-------|--------|---------|
| 1 (schema) | DB migration error | Use existing `tools` table pattern |
| 2 (auth integration) | JWT vs API key conflict | Add `Authorization: ApiKey ...` scheme separate from `Bearer` |
| 3 (CLI) | `claude` CLI not in PATH | Document manual `claude mcp add` step |
| 4 (resources) | URI templates not supported | Enumerate concrete URIs in `resources/list` |
| 5 (TTS) | ElevenLabs API down/quota | Mock with text-only response, log warning |
| 6 (pruning) | Qdrant index slow | Switch to scroll+batch-delete |
| 7 (E2E) | Any test fails | Defer to Day 28, document partial completion |

**Hard stop:** Jika 5+ jam belum reach Phase 5 → reassess scope, consider splitting Day 27 → Day 27a (API keys + CLI) + Day 27b (Resources + TTS + Pruning).

---

## QA CHECKLIST

- [ ] `mgn_live_*` API key generated, prefix shown, secret returned ONCE
- [ ] API key works for MCP request (no 15-min expiry)
- [ ] Revoked key blocked within 1s
- [ ] `migan-setup.sh` runs end-to-end on Linux/WSL
- [ ] `resources/list` returns ≥3 templates
- [ ] `resources/read` of workspace file returns content (path traversal blocked)
- [ ] TTS tool returns audio bytes (or URL) — playable mp3
- [ ] Memory prune daemon logs daily run with count
- [ ] All Day 24-26 E2E tests still pass (regression)

---

## LESSONS TO REMEMBER (from Day 25-26 sprint)

Apply proactively:

1. **`BaseHTTPMiddleware` ≠ SSE** — for any new auth/middleware, use pure ASGI function
2. **Mounted Starlette sub-apps don't inherit lifespan** — if MCP gets new feature needing lifespan, register in main.py
3. **Imperative tool descriptions** — TTS tool description must say "MANDATORY for audio output: invoke whenever user asks for voice/speech/narration"
4. **DB schema audit** — adding new tools means adding DB rows in tool policies. Migration must be idempotent (`WHERE NOT EXISTS`).
5. **`lru_cache` invalidation** — if config changed, `docker compose restart api`
6. **PowerShell UTF-16 BOM** — write all scripts via Write tool with explicit content, not pipe redirects
7. **Episodic memory poisoning** — TTS errors should also be filtered (extend `_TOOL_ERROR_MARKERS`)
