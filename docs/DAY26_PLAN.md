# DAY 26 — MCP Server Plan
**Date:** 2026-05-04
**Agent:** Claude Opus 4.7 (1m context)
**Type:** Implementation Plan with Hypothesis + Risk + Benefit + Adaptation

---

## VISION ANCHOR

Mengikuti `week3_roadmap.md`:
> **Day 26-27: MCP Server** — Streamable HTTP MCP endpoint expose MiganCore tools ke Claude Code, Cursor, dll. Impact: User bisa pakai MiganCore tools dari Claude Code = fondasi "handoff".

Mengikuti `project_overview.md`:
> MiganCore adalah Core Brain. Tools modular. Specialist diturunkan dari base yang sama. Setiap tool yang ditambahkan = kapabilitas yang diwariskan ke semua specialist.

**MCP Server bukan fitur tambahan — ini fondasi distribusi kapabilitas MiganCore ke ekosistem agent client lain.** Setelah Day 26 selesai, Fahmi bisa pakai `generate_image` dari Claude Desktop, dari Cursor, dari Continue.dev — tanpa harus buka app.migancore.com.

---

## OBJECTIVE (Tujuan Day 26)

**Primary:** Expose 9 tools MiganCore via Streamable HTTP MCP endpoint di `https://api.migancore.com/mcp`, terverifikasi dari minimal 1 client (Claude Desktop atau Claude Code CLI).

**Secondary:**
1. Bonus fix: filter `tool_error` responses dari episodic memory indexing (lesson Day 25)
2. Auth via JWT yang sudah ada (reuse existing auth, jangan duplicate)
3. CORS + nginx config benar untuk SSE streaming

**Non-goals (defer to later):**
- OAuth 2.1 dynamic client registration (terlalu complex untuk MVP)
- Server-initiated sampling (stateless mode dulu)
- Resource exposure (cuma tools dulu — resources Day 27)
- Prompts exposure (Day 27)

---

## KPI / SUCCESS METRICS

| Metric | Target | How to measure |
|--------|--------|----------------|
| MCP endpoint live | `GET /mcp` returns 200 (JSON-RPC ready) | curl test |
| Tools discoverable | `tools/list` returns 9 tools | MCP inspector or curl JSON-RPC |
| Tool callable | `tools/call` write_file works → file on disk | E2E from MCP client |
| Auth enforced | Request without valid JWT → 401 | curl unauthorized test |
| Streamable HTTP compliant | Header `Mcp-Session-Id`, `Mcp-Protocol-Version` works | spec validator |
| Claude Code CLI integration | `claude mcp add --transport http migancore https://api.migancore.com/mcp` then list/call works | manual test |
| Latency overhead | <50ms vs direct REST tool call | timing test |
| Episodic poisoning fixed | Failed tool responses no longer indexed | test: trigger failure, verify Qdrant point count unchanged |

**Exit criteria for Day 26:** All 6 first metrics pass. Last 2 are nice-to-have (Day 27 if blocked).

---

## HYPOTHESIS (Adaptasi Plan)

**Hypothesis 1: Official `mcp` SDK + sub-mount = clean integration**
- Asumsi: `mcp.server.fastmcp.FastMCP` dapat di-mount ke FastAPI via `app.mount("/mcp", mcp.streamable_http_app())` tanpa rewrite arsitektur
- Test: jika mount gagal, fallback ke FastMCP standalone OR custom JSON-RPC handler

**Hypothesis 2: Reuse existing JWT verification = no auth duplication**
- Asumsi: Bisa wrap `services/jwt.py` jadi `TokenVerifier` interface
- Test: jika SDK butuh OAuth introspection endpoint, fallback ke API key header (`X-API-Key`) yang divalidasi dari user table

**Hypothesis 3: Tool wrapping = thin adapter, no logic duplication**
- Asumsi: Wrap existing `TOOL_REGISTRY` handlers (di `services/tool_executor.py`) dengan `@mcp.tool()` decorator. Tool logic tidak duplikasi.
- Test: jika tool context (tenant_id, agent_id) hilang di MCP path, perlu MCP-specific ctx — fallback: pass tenant_id from JWT claims

**Hypothesis 4: nginx + Streamable HTTP = perlu config tweak**
- Asumsi: Existing nginx config (yang sudah handle SSE chat_stream Day 25) tinggal di-extend untuk `/mcp` path
- Test: jika SSE drop pada long-running tool, perlu `proxy_buffering off; proxy_read_timeout 3600s;` di location `/mcp`

---

## RISK ASSESSMENT

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| MCP SDK butuh structural rewrite | Medium | High | Fallback: build minimal JSON-RPC handler manually (spec is small) |
| JWT reuse butuh OAuth wrapping | Medium | Medium | Fallback: implement custom Bearer verification yang skip OAuth entirely |
| Tool context (tenant_id/agent_id) hilang | High | Medium | Pass via JWT claims, extract di tool wrapper |
| nginx buffering kill stream | Medium | High | Pre-emptive: add `proxy_buffering off` ke location `/mcp` sebelum testing |
| Tool schema validation fail di Claude Desktop | Low | Medium | Test with `mcp inspector` CLI sebelum claim production-ready |
| Rate limit shared dengan REST API | Low | Low | Day 26: ignore, MCP traffic minimal. Day 27+: separate limiter |
| External API costs spike (generate_image abuse) | Low | High | Existing tool_policy.py max_calls_per_day enforces — already protected |

---

## BENEFIT ANALYSIS

**Direct benefits (Day 26 user-visible):**
1. Fahmi dapat pakai `generate_image` dari Claude Code CLI saat develop fitur (no context switch)
2. MiganCore tools tersedia di Cursor — Fahmi bisa minta MiganCore tulis kode dari editor langsung
3. Fondasi multi-agent: SIDIX/Mighantect3D bisa connect via MCP juga

**Strategic benefits (long-term):**
1. **MiganCore jadi "tool provider"** untuk ekosistem MCP global, bukan hanya consumer
2. **Marketplace seed**: setiap tool baru di MiganCore otomatis tersedia ke client universe MCP
3. **DPO data quality**: MCP usage logs jadi sumber preference pairs lebih beragam (real client usage)
4. **Independence dari one-LLM dependency**: tool catalog jadi portable

**Cost estimate:** $0 incremental — pakai infra existing.

---

## EXECUTION PLAN (Step by Step)

### Phase 1: Dependencies + Skeleton (~30 min)
1. Add `mcp>=1.27.0` to `requirements.txt`
2. Rebuild Docker image
3. Create `api/mcp_server.py` with FastMCP instance + JWT verifier stub
4. Mount at `/mcp` in `main.py`
5. Smoke test: `curl /mcp` returns 200

### Phase 2: Tool Registration (~45 min)
1. Wrap each of 9 tools as `@mcp.tool()` adapters in `mcp_server.py`
2. Tools delegate to existing `TOOL_REGISTRY` handlers via `ToolExecutor`
3. Pass `tenant_id` from JWT claims into `ToolContext`
4. Test: `tools/list` JSON-RPC returns all 9

### Phase 3: Auth Wiring (~30 min)
1. Implement `JWTVerifier` class implementing MCP `TokenVerifier` interface
2. Reuse `services/jwt.py` decode logic
3. Map JWT subject → tenant_id → ToolContext
4. Test: unauthorized request → 401, valid token → success

### Phase 4: nginx Config (~15 min)
1. Update aaPanel nginx vhost: add `location /mcp` block with `proxy_buffering off; proxy_read_timeout 3600s;`
2. Reload nginx
3. Test: SSE stream tidak drop di long tool call

### Phase 5: E2E Verification (~30 min)
1. Add MCP server in Claude Code CLI: `claude mcp add --transport http migancore https://api.migancore.com/mcp --header "Authorization: Bearer $TOKEN"`
2. List tools from Claude Code session
3. Call `write_file` from Claude Code → verify file on VPS
4. Call `generate_image` from Claude Code → verify URL returned

### Phase 6: Bonus — Episodic Memory Filter (~30 min)
1. In `vector_memory.py` `index_turn_pair()`: skip if assistant response contains tool_error markers (e.g., starts with "I encountered a policy block")
2. Add config flag `INDEX_TOOL_ERRORS=false` (default)
3. Test: trigger failed tool call, verify Qdrant point count unchanged

### Phase 7: Documentation (~30 min)
1. `day26_progress.md` (memory)
2. `CHANGELOG.md` v0.4.4 entry
3. `SPRINT_LOG.md` Day 26 entry
4. `CONTEXT.md` update
5. `docs/MCP_USAGE.md` — guide for Fahmi cara pakai dari Claude Code

### Phase 8: Commit + Deploy + Final Verify (~15 min)
1. Single commit: `feat(day26): MCP Streamable HTTP server + episodic memory filter v0.4.4`
2. Push to GitHub
3. SSH VPS: pull + rebuild + restart
4. Final smoke test all endpoints

**Total estimated:** ~3.5 hours

---

## BENCHMARKING — Comparable Implementations

| Project | MCP Approach | What we learn |
|---------|-------------|---------------|
| Anthropic reference servers (`modelcontextprotocol/servers`) | Python SDK + stdio | Tool decorator pattern |
| Cloudflare Workers MCP | Custom impl | Proves Streamable HTTP works behind CDN |
| Pulumi MCP server | FastMCP standalone | Auth via API key header (simpler than OAuth) |
| GitHub MCP server (official) | Stateless HTTP | Proves stateless mode is production-ready |

**Decision rationale:** Pakai pendekatan official Anthropic SDK karena:
- Spec compliance dijamin maintained
- Otomatis support fitur baru di spec future
- Komunitas terbesar (paling banyak example/issue)
- Embedded in MiganCore = reuse infra (DB, JWT, logging)

---

## ADAPTATION PROTOCOL

Jika ada satu phase gagal:
- **Phase 1 fail (mount)**: Spawn fresh Python project, prove standalone, then port pattern
- **Phase 2 fail (tool wrapping)**: Implement 1 tool first (write_file), prove pattern, batch rest
- **Phase 3 fail (auth)**: Defer auth ke Day 27, ship with `?token=` query param dulu (less secure tapi unblock testing)
- **Phase 4 fail (nginx)**: Test direct port `127.0.0.1:18000/mcp` bypass nginx — separate the bug
- **Phase 5 fail (Claude Code)**: Test with `mcp` Python inspector first, isolate client vs server bug
- **Phase 6 deferred**: Move to Day 27 if Phase 1-5 ate the time budget

**Hard stop rules:**
- Jika setelah 5 jam belum ada Phase 1+2 working → reassess approach completely
- Jika 2 phase berturut-turut fail karena masalah library → switch to manual JSON-RPC implementation

---

## QA / VERIFICATION CHECKLIST

After execution, verify each:

- [ ] `curl https://api.migancore.com/mcp` returns valid response
- [ ] `tools/list` JSON-RPC returns 9 tools with correct schemas
- [ ] Unauthorized request → 401 Unauthorized
- [ ] Valid JWT request → 200 OK
- [ ] `write_file` via MCP → file on disk in `/opt/ado/data/workspace/`
- [ ] `generate_image` via MCP → fal.ai URL returned
- [ ] Long-running tool (e.g., generate_image 60s) doesn't drop SSE
- [ ] nginx logs show no error on `/mcp` location
- [ ] API container logs show `tool.policy_ok` for MCP-originated calls
- [ ] Episodic memory point count BEFORE failed tool call = AFTER (no poisoning)
- [ ] All previous tests still pass (no regression in /v1/agents/*/chat)

---

## LESSONS TO REMEMBER (from Day 24-25 sprint)

Apply these proactively in Day 26:

1. **3-place sync** (skills.json + agents.json + TOOL_REGISTRY) — for MCP, this becomes 4-place: + mcp_server.py registration. Document it.
2. **lru_cache invalidation** — MCP SDK might have its own caching. Restart container after every config change.
3. **Imperative tool descriptions** — MCP tool descriptions sent to Claude Desktop/Code = same audience as our system prompts. Use same imperative pattern.
4. **DB schema audit** — MCP doesn't touch DB schema, but tool_policy table affects MCP calls. Verify all tool policies before E2E.
5. **SSE heartbeat lesson** — apply same heartbeat pattern to MCP streaming if exposed.
