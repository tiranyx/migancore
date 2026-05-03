# MiganCore — Handoff Documentation

**As of:** Day 28 (2026-05-04) | **Version:** 0.4.6 | **Status:** Production live, training pipeline ready

---

## TL;DR untuk Agent baru / lanjutan develop

MiganCore adalah **Autonomous Digital Organism platform** — AI agent dengan identitas permanen (SOUL.md), memori 3-tier (Redis/Qdrant/Letta), tool ecosystem, dan training data flywheel untuk fine-tune model sendiri (Week 4 SimPO).

**3 endpoint produksi:**
- API: `https://api.migancore.com` (FastAPI v0.4.6)
- Chat UI: `https://app.migancore.com` (React standalone)
- Admin Dashboard: `https://app.migancore.com/admin/` (React, X-Admin-Key gate)

**3 layer aliran data:**
1. **Inference layer**: chat UI → API → Ollama Qwen2.5-7B + tools (fal.ai, ElevenLabs, sandbox FS)
2. **Distribution layer**: MCP Streamable HTTP → external clients (Claude Desktop/Code, Cursor, Antigravity)
3. **Training data flywheel**: 3 sumber DPO pairs:
   - CAI self-critique (auto, real conversations)
   - Synthetic generator (auto, 120 seeds × N rounds, target 1000)
   - **Distillation pipeline** (4 teachers: Anthropic, Kimi, OpenAI, Gemini) ← NEW Day 28

---

## Quick Start untuk Develop dari Mana Saja

### Cara 1: Pakai MiganCore tools dari Claude Code (LANGSUNG MULAI DEVELOP)

```bash
# One-line setup (Linux/Mac/WSL)
curl -sL https://raw.githubusercontent.com/tiranyx/migancore/main/scripts/migan-setup.sh | bash

# Windows PowerShell
iwr https://raw.githubusercontent.com/tiranyx/migancore/main/scripts/migan-setup.ps1 | iex
```

Setelah setup:
- Buka Claude Code → minta "buatkan gambar logo MiganCore"
- Atau "tulis file `notes.md` isinya rangkuman" → file di workspace MiganCore
- Atau "convert paragraf ini jadi audio mp3" → ElevenLabs TTS

### Cara 2: Develop kode MiganCore sendiri

```bash
git clone https://github.com/tiranyx/migancore
cd migancore

# Kebutuhan: Docker, Docker Compose, Python 3.11
# Lihat docs/SETUP.md (ada di repo)

# Production deploy
ssh root@72.62.125.6
cd /opt/ado
git pull
docker compose up -d --build api  # IMPORTANT: --build flag mandatory
```

---

## Project Structure (essential paths)

```
migancore/
├── api/                          # FastAPI backend
│   ├── main.py                   # entry point + lifespan
│   ├── config.py                 # all settings
│   ├── mcp_server.py             # MCP Streamable HTTP server (Day 26-27)
│   ├── routers/
│   │   ├── auth.py               # /v1/auth (JWT)
│   │   ├── api_keys.py           # /v1/api-keys (Day 27)
│   │   ├── agents.py             # /v1/agents
│   │   ├── chat.py               # /v1/agents/{id}/chat (+stream)
│   │   ├── conversations.py      # /v1/conversations
│   │   └── admin.py              # /v1/admin/* (synthetic, distill, stats, export)
│   ├── services/
│   │   ├── tool_executor.py      # 8 tools dispatcher
│   │   ├── teacher_api.py        # 4 LLM provider wrappers (Day 28)
│   │   ├── distillation.py       # DPO pair distillation pipeline (Day 28)
│   │   ├── synthetic_pipeline.py # 120-seed synthetic generator
│   │   ├── cai_pipeline.py       # self-critique pipeline
│   │   ├── memory_pruner.py      # daily Qdrant cleanup
│   │   ├── vector_memory.py      # Qdrant episodic
│   │   ├── jwt.py                # RS256 token
│   │   └── ...
│   ├── models/                   # SQLAlchemy ORM
│   └── deps/                     # FastAPI deps (auth, db)
├── frontend/
│   ├── chat.html                 # Chat UI (Day 22)
│   └── dashboard.html            # Admin Dashboard (Day 28)
├── config/
│   ├── agents.json               # agent personas + default_tools
│   └── skills.json               # tool schemas (MCP-compatible)
├── migrations/                   # SQL migrations
├── scripts/
│   ├── migan-setup.sh            # one-line MCP installer
│   └── migan-setup.ps1           # Windows version
└── docs/
    ├── CONTEXT.md                # ⭐ ALWAYS READ FIRST — current project state
    ├── SPRINT_LOG.md             # Day-by-day execution history
    ├── CHANGELOG.md              # Version history
    ├── MCP_USAGE.md              # MCP integration guide
    ├── HANDOFF.md                # This file
    └── DAY28_PLAN.md (etc)       # Per-day plans with audits
```

---

## Critical Knowledge — Wajib Diketahui Sebelum Touch Code

### 1. Multi-tenant + RLS

PostgreSQL Row-Level Security aktif. Always:
```python
await set_tenant_context(db, tenant_id)
```
Sebelum query tabel tenant-scoped. Lihat `deps/db.py` + `deps/auth.py` untuk pattern.

### 2. SOUL.md persona sacred

`docs/01_SOUL.md` = identity foundation. JANGAN modify casual. Setiap tool/pipeline yang melibatkan persona response (chat, distillation) HARUS inject SOUL untuk preserve voice. Lihat `services/distillation.py::_build_teacher_system_prompt()`.

### 3. 4-place sync rule untuk tools baru

Tambah tool baru = update 4 tempat:
1. `api/services/tool_executor.py` — `TOOL_REGISTRY` + handler function
2. `config/skills.json` — schema with `mcp_compatible: true`
3. `config/agents.json` — `core_brain.default_tools` array
4. `migrations/*.sql` — DB tools table policy (required for chat router policy enforcement)

Plus optional:
5. `api/mcp_server.py` — `@mcp.tool()` wrapper kalau mau expose ke MCP clients

Lupa salah satu = tool invisible di salah satu path.

### 4. Container `--build` vs `--force-recreate`

`--force-recreate` reuses old IMAGE. Untuk pickup code changes, MUST use:
```bash
docker compose up -d --build api
```

### 5. lru_cache invalidation

`load_skills_config()`, `load_agents_config()` cached. Edit JSON di host = container masih pakai cache. Always restart after config changes.

### 6. SSE + heartbeat mandatory

Long Ollama responses (30-90s) → nginx/Cloudflare close connection. Pattern di `chat.py::chat_stream()`: `asyncio.wait_for(timeout=15) + ping`. Apply ke endpoint streaming baru.

### 7. Episodic memory poisoning filter

`services/vector_memory.py::_is_tool_error_response()` — jangan index respons gagal/error/policy-block. Lesson dari Day 25 (14 poisoned points purged).

### 8. Pure ASGI middleware (bukan BaseHTTPMiddleware)

Untuk middleware di endpoint streaming (MCP, chat_stream), wajib pure ASGI function. `BaseHTTPMiddleware` buffer entire response → break SSE. Lihat `mcp_server.py::jwt_auth_asgi()` untuk pattern.

---

## Environment Variables (semua di `.env` VPS)

| Variable | Purpose |
|----------|---------|
| `JWT_PRIVATE_KEY_PATH` / `_PUBLIC_KEY_PATH` | RS256 keys (Day 4) |
| `ADMIN_SECRET_KEY` | X-Admin-Key gate untuk /v1/admin |
| `API_KEY_PEPPER` | HMAC pepper for `mgn_live_*` keys (Day 27) |
| `PG_PASSWORD`, `REDIS_PASSWORD`, `QDRANT_API_KEY` | service auth |
| `LETTA_PASSWORD` | Tier 3 memory |
| `FAL_KEY` | fal.ai image generation |
| `ELEVENLABS_KEY`, `ELEVENLABS_VOICE_ID` | TTS |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `KIMI_API_KEY`, `GEMINI_API_KEY` | distillation teachers (Day 28) |

Setelah edit `.env`: `docker compose up -d --force-recreate api` (env reload).

---

## Sprint Continuation — Week 4+

**Day 29 (immediate next):**
- Verify Day 28 distillation results — analyze pair quality, cost efficiency
- A/B test: bandingkan Kimi vs Claude vs Gemini sebagai teacher (30 pairs each)
- Pick winner → scale to 500 pairs

**Week 4:**
- Trigger SimPO training run on RunPod RTX 4090 ($0.69/hr)
- Train MiganCore-7B-distilled on combined dataset (synthetic 1000 + distill 500 + CAI 100 = 1600 pairs)
- A/B test new model vs base — benchmark on real chat
- If win: deploy as new `DEFAULT_MODEL` in config

**Week 5+: Specialist agent rollout (per ADO 2026-2027 vision):**
1. Creative Director Agent (highest ROI for Fahmi's design work)
2. Programming Agent (already partial via tools)
3. Productivity Agent (email, proposals, summaries)
4. Then: Marketing, Customer, Data, Finance, Legal, Cybersecurity, Physical AI

---

## Common Operations Reference

### Restart API after code change
```bash
ssh root@72.62.125.6
cd /opt/ado && git pull && docker compose up -d --build api
```

### Restart API after .env change (no code)
```bash
docker compose up -d --force-recreate api
```

### Check logs
```bash
docker compose logs api --tail=100
docker compose logs api --since=10m | grep ERROR
```

### Access database
```bash
docker compose exec postgres psql -U ado -d ado
```

### Check distillation status
```bash
curl https://api.migancore.com/v1/admin/distill/status -H "X-Admin-Key: $KEY" | jq
```

### Start a 30-pair distillation run
```bash
curl -X POST https://api.migancore.com/v1/admin/distill/start \
  -H "X-Admin-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"teacher":"kimi","target_pairs":30,"budget_cap_usd":0.5}'
```

### Resume synthetic generation
```bash
curl -X POST "https://api.migancore.com/v1/admin/synthetic/start?target_pairs=1000" \
  -H "X-Admin-Key: $KEY"
```

### View dashboard
Browser: `https://app.migancore.com/admin/` → enter admin key

---

## Mandatory Protocol untuk Agent Baru (sebelum eksekusi task)

Sesuai instruksi user yang konsisten dari Day 0:

1. **Baca dokumen penting** sebelum kerja: `CONTEXT.md`, `SPRINT_LOG.md`, sprint plan terbaru di `docs/DAY*_PLAN.md`
2. **Research dulu kalau topik baru** — pakai general-purpose agent untuk parallel research
3. **Plan dulu**: objectives, KPI, hypothesis, risk, benefit, adaptation strategy → tulis ke `docs/DAYXX_PLAN.md`
4. **Audit architecture + infrastructure + timing** sebelum execute
5. **Eksekusi dengan adapt mindset** — kalau hipotesis salah, fallback strategy sudah ada di plan
6. **QA + verify + document** setiap step
7. **Commit + push + deploy + final verify** end-to-end
8. **Update `day{N}_progress.md` + CHANGELOG + SPRINT_LOG + CONTEXT** SEMUA

**Single source of truth principles:**
- Code > Doc (kalau konflik, percaya code, update doc)
- DB > config (kalau policy beda, DB menang, update config + migration)
- `app.version` > hardcoded version strings (lesson Day 25)

---

## Contact

- Owner: Fahmi Wol (tiranyx.id@gmail.com)
- Repo: github.com/tiranyx/migancore (PUBLIC, Apache 2.0)
- VPS: 72.62.125.6 (Ubuntu 22.04, 32GB RAM, 8 core, 400GB)
- Stack: FastAPI + Postgres pgvector + Redis + Qdrant + Ollama Qwen2.5-7B-Q4_K_M + Letta + fal.ai + ElevenLabs

---

**Last updated:** 2026-05-04 (Day 28) by Claude Opus 4.7
