# MIGANCORE — CONTEXT.md (Project RAM)
**Last Updated:** 2026-05-03 | **Last Agent:** Claude Sonnet 4.6 (Day 12 Handoff + Stabilize)
**API Version:** 0.3.2 (stable, Day 11)
**Git Commit:** `c8a066b`

> Ini adalah "project RAM" — sumber kebenaran tunggal untuk state proyek saat ini.
> **Setiap agent WAJIB baca ini sebelum mulai kerja. Update setelah setiap sesi.**
> Jika ada konflik antara CONTEXT.md dan kode: **percayai kode, update CONTEXT.md**.
>
> Dokumen pendukung: `MASTER_CONTEXT.md` | `SPRINT_LOG.md` | `CHANGELOG.md` | `HANDOFF_DAY11_KIMI_TO_CLAUDE.md`

---

## CURRENT STATUS

| Field | Value |
|-------|-------|
| Phase | Week 2 — Safety + Intelligence |
| Sprint Day | Day 11 (COMPLETE) → Day 12 (NEXT) |
| API Version | 0.3.2 |
| Git Commit | `c8a066b` (VPS + GitHub + Local = SYNCED) |
| VPS | Ubuntu 22.04, 32GB RAM, 8 core, 400GB |
| External URL | **https://api.migancore.com** (Let's Encrypt SSL ✅) |
| Stack Status | Postgres ✅ Redis ✅ Qdrant ✅ Ollama ✅ API ✅ Letta ✅ (running, not yet wired) |

---

## WORKING COMPONENTS (VERIFIED END-TO-END)

### Auth System (Day 1–5, Kimi)
- ✅ `POST /v1/auth/register` — Argon2id hash, tenant auto-create, scope assignment
- ✅ `POST /v1/auth/login` — RS256 JWT, access (15m) + refresh (7d) token pair
- ✅ `POST /v1/auth/refresh` — atomic token rotation, session family termination
- ✅ `POST /v1/auth/logout` — token revocation
- ✅ `GET /v1/auth/me` — current user info
- ✅ Rate limiting: 5/min login, 10/min register
- ✅ Audit logging: events ke Postgres (async, no rollback risk)
- ✅ RLS: cross-tenant isolation verified, ado_app non-superuser

### Agent System (Day 6 + Day 10–11)
- ✅ `POST /v1/agents` — create agent, tenant-scoped + **max_agents enforcement** (Day 11)
- ✅ `GET /v1/agents/{id}` — get agent by ID
- ✅ `POST /v1/agents/{id}/spawn` — spawn child agent dengan:
  - Inherited: model_version, visibility, system_prompt, description
  - Persona merge: parent persona_blob + persona_overrides
  - Generation: parent.generation + 1
  - **MAX_GENERATION_DEPTH=5** (Day 11)
  - **persona_locked gate** — blok overrides jika parent locked (Day 11)
  - **max_agents enforcement** juga berlaku untuk spawn (Day 11)
- ✅ `GET /v1/agents/{id}/children` — list direct children

### Chat System (Day 6–11)
- ✅ `POST /v1/agents/{id}/chat` — sync chat via LangGraph director
  - Rate limited: 30/min per IP
  - Context window: last 5 messages
  - Memory injection: Redis K-V summary injected ke system prompt
  - Tool calling: MAX_TOOL_ITERATIONS=5 via LangGraph StateGraph
  - **Tenant message quota check** (Day 11): max_messages_per_day, auto-reset UTC midnight
  - **Tool policy enforcement** via ToolPolicyChecker (Day 11)
  - Response: `ChatResponse` dengan `tool_calls_made` + `reasoning_trace`
- ✅ `POST /v1/agents/{id}/chat/stream` — SSE streaming (no tool calling)
- ✅ `GET /v1/agents/{id}/conversations` — list conversations

### Conversation Management (Day 7, Claude)
- ✅ `GET /v1/conversations` — list semua conversations user
- ✅ `GET /v1/conversations/{id}` — get conversation dengan messages
- ✅ `DELETE /v1/conversations/{id}` — soft delete (status → archived)

### Safety Gates (Day 11, Kimi)
- ✅ `services/tool_policy.py` — 6-class tool policy taxonomy:
  - `read_only` | `write` | `destructive` | `open_world` | `requires_approval` | `sandbox_required`
  - Plan tier enforcement (free/pro/enterprise)
  - Approval gate (hard block)
  - Sandbox gate (log warning)
  - Per-tenant per-tool daily counters (Redis)
- ✅ Python REPL import blacklist: os, sys, subprocess, socket, urllib, pickle, ctypes...
- ✅ `deps/rate_limit.py` — RedisStorage backend (multi-worker safe), hybrid key (tenant-id → IP fallback)
- ✅ `models/tool.py` — Tool ORM model (risk_level, policy JSONB, max_calls_per_day)
- ✅ `migrations/011_day11_safety_gates.sql` — applied to live DB

### Memory Service (Day 7, Claude)
- ✅ `services/memory.py` — Redis K-V Tier 1
  - Key pattern: `mem:{tenant_id}:{agent_id}:{namespace}:{key}`, 30d TTL
  - `memory_write` / `memory_read` / `memory_list` / `memory_summary`

### Tool Executor (Day 8, Claude + Day 11 update)
- ✅ `services/tool_executor.py`
  - `ToolContext(tenant_id, agent_id, tenant_plan, tool_policies)` — diperluas Day 11
  - `_web_search` → DuckDuckGo Instant Answers
  - `_memory_write` / `_memory_search` → Redis K-V
  - `_python_repl` → subprocess.run + import blacklist + policy check
  - Policy check via `ToolPolicyChecker.check()` sebelum dispatch

### LangGraph Director (Day 9, Claude + Kimi)
- ✅ `services/director.py` — StateGraph: reason_node → execute_tools_node
  - Circuit breaker: MAX_TOOL_ITERATIONS=5
  - Fallback: plain chat jika tool calling unsupported

### Infrastructure
- ✅ Docker Compose `/opt/ado/docker-compose.yml`:
  - **Running**: postgres, redis, qdrant, ollama, api
  - **Running (unintegrated)**: letta 0.6.0 (port 8083) — scheduled Day 13
  - **Disabled**: celery (Week 4), langfuse (Week 3), caddy (nginx handles 80/443)
- ✅ nginx aaPanel: `https://api.migancore.com` → port 18000 (Let's Encrypt SSL)
- ✅ OllamaClient: timeouts, streaming, tool calling (stream=False hardcoded)
- ✅ Request tracing: X-Request-ID + structlog

---

## IN PROGRESS / NEXT SPRINT

### Day 12 — Qdrant RAG Tier 2
**Goal:** Semantic memory — agent ingat konteks dari percakapan lampau via vector search

**Keputusan arsitektur yang LOCKED (dari KIMI + GPT-5.5 consensus):**
- Embedding model: `paraphrase-multilingual-mpnet-base-v2` (768-dim, Bahasa Indonesia native)
  - BUKAN BGE-small-en (English only)
  - BUKAN BAAI/bge-m3 (compatibility issues)
- Collection naming: `episodic_{agent_id}` dan `semantic_{agent_id}`
- Chunking unit: turn-pair (user+assistant), bukan per-message
- Embedding library: `fastembed` (CPU, no GPU needed)

**Tasks:**
- [ ] `services/embedding.py` — fastembed wrapper, `paraphrase-multilingual-mpnet-base-v2`
- [ ] `services/vector_memory.py` — Qdrant CRUD per agent collection
  - `index_message_pair(agent_id, turn_pair)` — embed + upsert ke Qdrant
  - `search_semantic(agent_id, query, top_k=5)` — similarity search
- [ ] `routers/chat.py` — async background embed setelah message saved
- [ ] `services/tool_executor.py` — upgrade `_memory_search` ke query Qdrant terlebih dulu
- [ ] Test: "ingat bahwa company saya bernama X" → searchable 10 pesan kemudian

### Day 13 — Letta Tier 3 (PASSIVE STORAGE ONLY)
**CRITICAL CONSTRAINT:** Qwen2.5-7B Q4 tidak cukup untuk Letta tool calls.
Letta HANYA boleh digunakan sebagai storage (blocks.retrieve / blocks.update).
JANGAN invoke `agents.messages.create()`.

Letta sudah running di port 8083. Next: wire ke API untuk persona block persistence.

---

## BLOCKERS

Tidak ada blocker saat ini.

---

## KNOWN BUGS & TECH DEBT

| ID | Severity | Description | Fix |
|----|----------|-------------|-----|
| H4 | MEDIUM | `.venv` masih di-track git | `git rm -r --cached api/.venv` + `.gitignore` |
| H2 | LOW | Alembic belum setup, migrations raw SQL | Setup sebelum beta |
| H6 | LOW | `agent_tool_grants` tidak ada ORM model | Buat `models/agent_tool_grant.py` |
| C2 | LOW | `reasoning_trace` tidak ada di `ChatResponse` schema | Add field ke `schemas/chat.py` |
| C8 | LOW | JWT key rotation belum ada strategi | Defer sampai user base > 0 |
| T1 | LOW | `models/base.py` punya `get_db()` duplikat dari `deps/db.py` | Hapus dari base.py |
| M1 | INFO | Chat rate limit pakai IP, bukan JWT sub | Fix: pakai `request.state.user_id` |
| M4 | INFO | `_get_director()` global state potensial race condition | Add threading.Lock() |

---

## ARCHITECTURE DECISIONS (FINAL)

| Decision | Choice | Alasan |
|----------|--------|--------|
| Celery | DISABLED | RAM terlalu mahal untuk seed stage. asyncio.create_task cukup. |
| Letta | PASSIVE STORAGE ONLY | Qwen2.5-7B Q4 tidak support Letta tool calls. Use blocks API only. |
| Langfuse | DEFERRED (Week 3) | Belum ada yang perlu diobservasi. structlog sudah cukup. |
| Memory Tier 1 | Redis K-V | Fast, simple, TTL built-in |
| Memory Tier 2 | Qdrant + fastembed (Day 12) | Semantic similarity, multilingual |
| Memory Tier 3 | Letta blocks (Day 13) | Persona persistence only |
| Embedding model | paraphrase-multilingual-mpnet-base-v2 | Bahasa Indonesia native, 768-dim |
| MCP Transport | Streamable HTTP (spec 2025-03-26) | BUKAN HTTP+SSE (deprecated) |
| Training | DPO | Data ledger dulu (min 500 pairs), RunPod RTX 4090 $0.34/hr |
| Streaming | SSE via StreamingResponse | Simple, cukup untuk MVP |
| Tool Protocol | MCP-compatible schemas | Future-proof, declared di skills.json |
| Orchestration | LangGraph StateGraph | Controllable, stateful, circuit breaker |
| Python REPL sandbox | subprocess.run + import blacklist | subprocess = real process boundary |
| Tool calling | stream=False | Ollama tool calling tidak support streaming |

---

## WHAT NEXT AGENT MUST NOT DO

- ❌ Jangan aktifkan Celery — disabled intentionally, Week 4
- ❌ Jangan invoke `letta.agents.messages.create()` — Qwen2.5 Q4 tidak support
- ❌ Jangan tambah Langfuse ke default profile — defer Week 3
- ❌ Jangan commit `.venv/` ke git
- ❌ Jangan duplicate `get_db` — pakai `deps.db.get_db` exclusively
- ❌ Jangan skip `set_tenant_context` sebelum query tenant-scoped tables
- ❌ Jangan pakai BGE-small-en untuk embeddings — English only, salah pilihan
- ❌ Jangan gunakan HTTP+SSE untuk MCP transport — gunakan Streamable HTTP

---

## VPS ECOSYSTEM (JANGAN OVERLAP)

| Project | Path | Ports | Tujuan |
|---------|------|-------|--------|
| MiganCore (ADO) | `/opt/ado/` | 18000 | THIS PROJECT — Core Brain |
| SIDIX | `/opt/sidix/` | (separate) | Research Lab consumer, sidixlab.com |
| Ixonomic | `/var/www/ixonomic/` | 3000-3010+ | Business platform |
| nginx aaPanel | — | 80/443 | Routing semua domain |

**RAM Budget (dari 32GB):**
- Ollama 7B: ~6GB
- Postgres: ~500MB
- Qdrant: ~200MB
- Redis: ~100MB
- API: ~200MB
- Letta: ~500MB
- **Total ADO: ~7.5GB** dari 32GB — aman

---

## METRICS

| Metric | Value |
|--------|-------|
| API endpoints | 14 (5 auth + 4 agents + 3 chat + 3 conversations) |
| DB tables | 20 (includes papers, kg_entities, preference_pairs untuk Week 3-4) |
| Memory tier | Tier 1: Redis K-V ✅ | Tier 2: Qdrant (Day 12) | Tier 3: Letta blocks (Day 13) |
| Test coverage | E2E: 14/14 endpoints + 10/10 safety gates |
| Stack services | 6 running (postgres, redis, qdrant, ollama, api, letta) |
| External URL | https://api.migancore.com (Let's Encrypt SSL) |
| RunPod budget | $0 spent of $50 allocated |
| Git | VPS ↔ GitHub ↔ Local = SYNCED @ c8a066b |

---

## HANDOFF LOG

| Date | Agent | Session Summary |
|------|-------|-----------------|
| 2026-05-02 (Day 0) | Kimi | Buat 8 master docs, schema, architecture, sprint plan |
| 2026-05-02 (Day 1) | Kimi | VPS provisioning, Docker, swap, SSH, JWT keys |
| 2026-05-02 (Day 2) | Kimi | DNS + nginx reverse proxy, SSL |
| 2026-05-02 (Day 3) | Kimi | Ollama container, Qwen2.5-7B + 0.5B pulled, 7-14 tok/s |
| 2026-05-02 (Day 4) | Kimi | Auth system: RS256, Argon2id, refresh rotation, 5 endpoints |
| 2026-05-02 (Day 5) | Kimi | RLS, cross-tenant tests, audit logging, ado_app non-superuser |
| 2026-05-02 (Day 6) | Kimi | Agent CRUD, chat endpoint, SOUL.md injection, config system |
| 2026-05-03 (Day 7) | Claude Sonnet 4.6 | Memory service (Redis K-V), SSE streaming, conversation endpoints |
| 2026-05-03 (Day 8) | Claude Sonnet 4.6 | Tool executor (4 tools), ReAct agentic loop, OllamaClient tool calling |
| 2026-05-03 (Day 7-9) | Kimi Code CLI | Audit + fix Day 7-9, wire director.py, deploy v0.3.0, E2E all pass |
| 2026-05-03 (Day 10) | Kimi Code CLI | Schema sync, agent spawning endpoint, v0.3.1, E2E all pass |
| 2026-05-03 (Day 11) | Kimi Code CLI | Safety gates: tool policy 6-class, max_agents, spawn depth, persona lock, REPL blacklist, tenant quota, Redis rate limiter. v0.3.2. E2E 10/10 |
| 2026-05-03 (Day 12) | Claude Sonnet 4.6 | Full audit + handoff: sync all repos (VPS↔GitHub↔local @ c8a066b), fix version 0.3.0→0.3.2, setup api.migancore.com HTTPS (Let's Encrypt). CONTEXT.md updated. Ready for Qdrant RAG. |
