# MIGANCORE — HANDOFF DOCUMENT
**From:** Kimi Code CLI  
**To:** Claude Code  
**Date:** 2026-05-03  
**Version:** 0.3.2 (Day 11 Complete)  
**Status:** Production-deployed on VPS

---

# BAGIAN 1: VISI & TUJUAN AKHIR

## Apa yang Sedang Dibangun?

**MiganCore (Mighantect Autonomous Core)** adalah "Autonomous Digital Organism" — sebuah sistem AI agent yang dapat:

1. **Berpikir mandiri** melalui LangGraph director (state machine)
2. **Mengingat** melalui 3-tier memory (Redis → Qdrant → Letta)
3. **Menggunakan tools** secara otomatis (web search, code execution, memory, spawning)
4. **Berkembang biak** — agent dapat spawn child agent dengan persona inheritance
5. **Belajar dari interaksi** — training pipeline (DPO) untuk self-improvement
6. **Aman** — safety gates, tool policy, rate limiting, audit logging

## North Star Vision
> "Every vision deserves a digital organism"

Proyek ini dibangun oleh **tiranyx** (founder) sebagai fondasi untuk ekosistem agent AI yang:
- Beroperasi 24/7 secara autonomous
- Dapat membuat agent baru (spawn) sesuai kebutuhan
- Menggunakan model open-source (Qwen2.5) tanpa ketergantungan API berbayar
- Mampu berkomunikasi dalam Bahasa Indonesia (native)
- Self-evolving melalui feedback loop dan fine-tuning

---

# BAGIAN 2: STATUS SAAT INI (Day 11 / v0.3.2)

## Week 1 (Days 1-10) — FOUNDATION ✅ COMPLETE

| Day | Feature | Status |
|-----|---------|--------|
| 0 | Architecture, 8 master docs | ✅ |
| 1 | VPS provisioning (32GB, 8 cores) | ✅ |
| 2 | DNS + Reverse Proxy (aaPanel nginx) | ✅ |
| 3 | Ollama + Qwen2.5-7B + 0.5B | ✅ |
| 4 | Auth (RS256 JWT, Argon2id, refresh rotation) | ✅ |
| 5 | RLS + Tenant Isolation | ✅ |
| 6 | Agent CRUD + Chat endpoint | ✅ |
| 7 | Redis Memory (Tier 1) + SSE Streaming | ✅ |
| 8 | Tool Executor (web_search, memory_write, memory_search, python_repl) | ✅ |
| 9 | LangGraph Director (StateGraph orchestrator) | ✅ |
| 10 | Agent Spawning + Schema Sync | ✅ |

## Week 2 (Days 11-17) — SAFETY + INTELLIGENCE 🔄 IN PROGRESS

| Day | Feature | Status |
|-----|---------|--------|
| **11** | **Safety Gates + Tool Policy** | **✅ COMPLETE** |
| 12 | Qdrant RAG Tier 2 | 🕐 NEXT |
| 13 | Letta Tier 3 Memory | 🕐 PENDING |
| 14 | MCP Adapter (Streamable HTTP) | 🕐 PENDING |
| 15-17 | Training Pipeline (Data Ledger → DPO) | 🕐 PENDING |

---

# BAGIAN 3: CREDENTIALS & AKSES

## VPS Information

| Item | Value |
|------|-------|
| **IP Address** | `72.62.125.6` |
| **OS** | Ubuntu 22.04 LTS |
| **RAM** | 32GB |
| **CPU** | 8 cores |
| **Disk** | 400GB |
| **Swap** | 32GB |
| **SSH Key** | `sidix_vps_key` (stored in repo) |
| **SSH User** | `root` |
| **SSH Port** | 22 |

```bash
# SSH Access
ssh -i ~/.ssh/sidix_vps_key root@72.62.125.6

# Or if key is in repo:
ssh -i /path/to/sidix_vps_key root@72.62.125.6
```

## GitHub Repository

| Item | Value |
|------|-------|
| **Repo** | `tiranyx/migancore` |
| **Branch** | `main` |
| **Latest Commit** | `7bfac0a` (v0.3.2) |
| **Local Path (VPS)** | `/opt/ado/` |
| **Local Path (Windows)** | `C:\migancore\migancore\` |

```bash
# Clone
gh repo clone tiranyx/migancore
# atau
git clone https://github.com/tiranyx/migancore.git
```

> ⚠️ **CRITICAL:** `api/.venv` is tracked in git (tech debt). Do NOT modify it.

## Docker Compose Services

All services run via Docker Compose in `/opt/ado/`:

```bash
cd /opt/ado && docker compose ps
```

| Service | Container Name | Port (Host) | Port (Container) | Status |
|---------|---------------|-------------|------------------|--------|
| API | `ado-api-1` | `127.0.0.1:18000` | `8000` | ✅ Running |
| Postgres | `ado-postgres-1` | internal | `5432` | ✅ Running |
| Redis | `ado-redis-1` | internal | `6379` | ✅ Running |
| Qdrant | `ado-qdrant-1` | internal | `6333` | ✅ Running |
| Ollama | `ado-ollama-1` | internal | `11434` | ✅ Running |
| Letta | `ado-letta-1` | — | — | ❌ DISABLED (profile:memory) |

## Database Credentials

| DB | User | Password Location |
|----|------|-------------------|
| Postgres `ado` | `ado` | `/opt/ado/.env` (`PG_PASSWORD`) |
| Postgres app | `ado_app` | Same |
| Redis | — | `/opt/ao/.env` (`REDIS_PASSWORD`) |

```bash
# Access Postgres
docker exec -it ado-postgres-1 psql -U ado -d ado

# Access Redis
docker exec ado-redis-1 redis-cli -a $(grep REDIS_PASSWORD /opt/ado/.env | cut -d= -f2)
```

## API Endpoints

| Environment | Base URL |
|-------------|----------|
| VPS (localhost) | `http://127.0.0.1:18000` |
| External (via nginx) | `https://api.migancore.com` |

### Key Endpoints
- `POST /v1/auth/register` — Register (requires tenant_name + tenant_slug)
- `POST /v1/auth/login` — Login
- `GET /v1/auth/me` — Current user
- `POST /v1/agents` — Create agent
- `GET /v1/agents/{id}` — Get agent
- `POST /v1/agents/{id}/spawn` — Spawn child
- `GET /v1/agents/{id}/children` — List children
- `POST /v1/agents/{id}/chat` — Sync chat with tools
- `POST /v1/agents/{id}/chat/stream` — SSE streaming
- `GET /health` — Liveness
- `GET /ready` — Readiness (checks all deps)

---

# BAGIAN 4: ARSITEKTUR & INFRASTRUKTUR

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  CLIENT (Web/Mobile)                                        │
│  https://api.migancore.com                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  aaPanel nginx (Reverse Proxy)                              │
│  Ports: 80/443 → 127.0.0.1:18000                           │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│  FASTAPI (ado-api-1) :8000 → Host :18000                   │
│  Python 3.11, Uvicorn, SQLAlchemy 2.0                       │
│  LangGraph Director, Structlog                              │
└────────────────────┬────────────────────────────────────────┘
                     │
    ┌────────────────┼────────────────┬────────────────┐
    │                │                │                │
    ▼                ▼                ▼                ▼
┌─────────┐  ┌─────────────┐  ┌───────────┐  ┌─────────────┐
│Postgres │  │ Redis       │  │ Qdrant    │  │ Ollama      │
│pgvector │  │ Async Pool  │  │ Vector DB │  │ Inference   │
│:5432    │  │ :6379       │  │ :6333     │  │ :11434      │
└─────────┘  └─────────────┘  └───────────┘  └─────────────┘
```

## 3-Tier Memory Architecture

| Tier | Technology | Purpose | Status |
|------|-----------|---------|--------|
| **Tier 1** | Redis K-V | Working memory, instant R/W, 30-day TTL | ✅ Day 7 |
| **Tier 2** | Qdrant + embeddings | Semantic search, RAG retrieval | 🕐 Day 12 |
| **Tier 3** | Letta blocks | Long-term persona persistence | 🕐 Day 13 |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI + Pydantic v2 |
| Auth | RS256 JWT, Argon2id, refresh rotation |
| ORM | SQLAlchemy 2.0 + asyncpg |
| DB | PostgreSQL 16 + pgvector extension |
| Cache/Memory | Redis (asyncio) |
| Vector DB | Qdrant |
| LLM | Ollama (self-hosted) |
| Model | Qwen2.5-7B-Instruct-Q4_K_M |
| Director | LangGraph StateGraph |
| Rate Limiting | slowapi + RedisStorage |
| Logging | structlog |
| Infra | Docker Compose, Ubuntu 22.04 |

## Database Schema (Key Tables)

```
tenants          — Multi-tenancy root
  └─ users       — Auth users (Argon2id hashed)
  └─ agents      — AI agents (with genealogy: parent_agent_id, generation)
  └─ tools       — Tool registry (with policy JSONB)
  └─ agent_tool_grants — Junction table (which agent can use which tool)
  └─ conversations — Chat threads
  └─ messages    — Individual messages (with tool_calls JSONB)
  └─ audit_events — Security/compliance logging
  └─ memory_blocks — Letta memory (Tier 3)
  └─ archival_memory — Qdrant backup (Tier 2)
  └─ model_versions — Trained model registry
```

---

# BAGIAN 5: KONTEKS KRITIS & CONCERN

## Concern #1: VPS adalah Single Point of Failure
- Hanya 1 VPS (32GB RAM, no GPU)
- Ollama inference di CPU (7-14 tok/s)
- **Jangan deploy resource-intensive tasks tanpa monitoring**
- SIDIX/Ixonomic zero-downtime requirement

## Concern #2: Python REPL Security (PARTIAL)
- Saat ini: subprocess.run + import blacklist
- **Belum fully sandboxed** — gVisor/nsjail deferred ke Day 16+
- Tool policy menandai `python_repl` sebagai `sandbox_required` + `requires_approval`
- **Jangan enable python_repl untuk tenant free/pro**

## Concern #3: Rate Limiting
- Slowapi sekarang pakai RedisStorage (multi-worker safe)
- Key function: hybrid (tenant-id header → IP fallback)
- **Tapi spawn endpoint belum ada rate limit khusus** (hanya IP-level)
- Tenant-level dilindungi via `max_agents`

## Concern #4: Model Limitation
- Qwen2.5-7B Q4_K_M di bawah threshold Letta untuk tool calls
- Letta (Day 13) hanya boleh digunakan sebagai **passive storage** (blocks.retrieve/update)
- **Jangan invoke `agents.messages.create()` di Letta**

## Concern #5: Git Hygiene
- `.venv` masih tracked di git (bloat repo)
- No Alembic — migrations pakai raw SQL
- **Jangan delete .venv dari git tanpa koordinasi dengan founder**

## Concern #6: Windows Development Environment
- Workspace utama: `C:\migancore\migancore\`
- File copy ke VPS sering bermasalah dengan quoting PowerShell
- **Gunakan shell script (.sh) atau base64 encoding untuk transfer file**

## Concern #7: Database Ownership
- Table owner adalah user `ado` (superuser saat init)
- `ado_app` tidak bisa ALTER TABLE
- **Migration harus di-run sebagai `ado`**:
  ```bash
  cat migration.sql | docker compose exec -T postgres psql -U ado -d ado
  ```

---

# BAGIAN 6: ROADMAP & TAHAPAN BERIKUTNYA

## Week 2 Revised Order (GPT-5.5 + Claude Code Consensus)

```
Day 11 ✅ Safety Gates + Tool Policy (DONE)
Day 12 🕐 Qdrant RAG Tier 2
Day 13 🕐 Letta Tier 3 (PASSIVE STORAGE ONLY)
Day 14 🕐 MCP Adapter (Streamable HTTP, NOT legacy SSE)
Day 15-17 🕐 Training Pipeline (Data Ledger → DPO/Unsloth)
```

## Key Decisions (Jangan Diubah Tanpa Diskusi)

1. **"Jangan tambah otak sebelum tambah sistem imun"** — Safety dulu, Letta kemudian
2. **Embedding model:** `paraphrase-multilingual-mpnet-base-v2` (768-dim, Bahasa Indonesia native)
   - BUKAN BGE-small-en (English-only)
   - BUKAN BAAI/bge-m3 (compatibility issues)
3. **MCP Transport:** Streamable HTTP (spec 2025-03-26)
   - BUKAN HTTP+SSE (deprecated)
4. **Training:** DPO (bukan GRPO)
   - Data ledger dulu, minimum 500 pairs
   - RunPod RTX 4090 Community Cloud = $0.34/hr
5. **Chunking unit:** Turn-pair (user+assistant), bukan per-message

## Tujuan Akhir (30-Day Blueprint)

| Phase | Timeline | Deliverable |
|-------|----------|-------------|
| Foundation | Week 1 | Auth, Agent, Chat, Tools, Memory, Director |
| Safety | Week 2 | Policy, RAG, Letta, MCP, Training pipeline |
| Scale | Week 3 | Multi-model, load balancing, monitoring |
| Polish | Week 4 | UI, docs, deployment automation |

---

# BAGIAN 7: CARA KERJA SAAT INI

## Alur Request Chat (Sync)

```
1. User POST /v1/agents/{id}/chat {message}
2. Auth middleware → validate JWT
3. Rate limiter (slowapi + Redis)
4. Tenant context SET LOCAL
5. Load agent config + SOUL.md + Redis memory summary
6. Build Ollama messages (system + history + user)
7. Load tool policies from DB
8. ToolContext(tenant_id, agent_id, tenant_plan, tool_policies)
9. run_director(model, messages, tools_spec, tool_ctx)
   ├── reason_node: Ollama chat_with_tools
   ├── if tool_calls → execute_tools_node
   │   └── ToolExecutor.execute(skill_id, args)
   │       └── Policy check → handler dispatch
   └── Loop max 5 iterations
10. Persist assistant message + tool_calls
11. Return ChatResponse
```

## Tool Policy Enforcement Flow

```
ToolExecutor.execute(skill_id)
  └── ToolPolicyChecker.check(skill_id)
      ├── Plan tier check (free/pro/enterprise)
      ├── requires_approval gate (hard block)
      ├── sandbox_required gate (log warning)
      ├── max_calls_per_day (Redis counter)
      └── Increment counter if passed
```

---

# BAGIAN 8: QUICK REFERENCE COMMANDS

```bash
# SSH ke VPS
ssh -i ~/.ssh/sidix_vps_key root@72.62.125.6

# Workspace
cd /opt/ado

# Status services
docker compose ps
docker compose logs api --tail 50

# Restart API (setelah code change)
docker compose restart api

# Copy file ke container
docker cp /opt/ado/api/models/tool.py ado-api-1:/app/models/tool.py

# Build + restart (kalau Dockerfile berubah)
docker compose build api && docker compose up -d api

# Database
docker exec ado-postgres-1 psql -U ado -d ado -c "SELECT ..."

# Redis
docker exec ado-redis-1 redis-cli -a $(grep REDIS_PASSWORD .env | cut -d= -f2) ping

# Run migration
cat migrations/011_day11_safety_gates.sql | docker compose exec -T postgres psql -U ado -d ado

# Health check
curl http://127.0.0.1:18000/health
curl http://127.0.0.1:18000/ready

# API version
curl http://127.0.0.1:18000/ | python3 -m json.tool
```

---

# BAGIAN 9: LIVING DOCS DIRECTORY

Semua dokumen berikut ada di `/opt/ado/docs/` (VPS) dan `migancore/docs/` (local):

| Doc | Purpose |
|-----|---------|
| `MASTER_CONTEXT.md` | Overview arsitektur, stack, decision log |
| `SPRINT_LOG.md` | Riwayat harian Day 0-11 |
| `CHANGELOG.md` | Perubahan per versi (0.1.0 → 0.3.2) |
| `FOUNDER_JOURNAL.md` | Catatan founder, visi, pivots |
| `QA_REPORT.md` | Hasil audit kualitas + security gaps |
| `WEEK2_RESEARCH.md` | Riset teknis untuk Week 2 |
| `WEEK2_SYNTHESIS.md` | Kompilasi consensus 3-agent |
| `AGENT_PROMPTS.md` | Prompt patterns untuk AI agents |
| `CLAUDE_RESEARCH_WEEK2.md` | Temuan riset Claude Code |
| `HANDOFF_DAY11_KIMI_TO_CLAUDE.md` | **Dokumen ini** |

---

# BAGIAN 10: CATATAN PERSONAL (Kimi → Claude)

## Yang Bekerja dengan Baik
1. **Docker cp + restart** adalah cara tercepat deploy ke container (bukan scp langsung ke host)
2. **Base64 encoding** untuk transfer file via SSH menghindari quoting hell di PowerShell
3. **Idempotent migrations** dengan `ADD COLUMN IF NOT EXISTS` — aman untuk re-run
4. **ToolContext** sebagai carrier untuk policy — clean separation dari director graph

## Yang Perlu Diperhatikan
1. **PowerShell quoting** adalah nightmare — selalu gunakan shell script (.sh) untuk command kompleks
2. **Docker compose restart** = keep container (file changes persist). `docker compose up -d` = recreate from image (changes LOST).
3. **Postgres user `ado`** adalah table owner, bukan `ado_app` atau `postgres`
4. **Letta constraint** — Qwen2.5 Q4 tidak cukup untuk Letta tool calls. Gunakan sebagai storage ONLY.
5. **Redis auth** — CLI butuh password, API connection string sudah include password

## Yang Founder (tiranyx) Prioritaskan
1. **Keamanan** — "Jangan tambah otak sebelum tambah sistem imun"
2. **Bahasa Indonesia** — Model harus native Bahasa Indonesia
3. **Cost efficiency** — Self-hosted, minimal API berbayar
4. **Zero downtime** — SIDIX/Ixonomic tidak boleh down
5. **Audit trail** — Semua action harus tercatat

---

**End of Handoff Document**

*"Semua visi pantas mendapat organisme digital. Terus bangun dengan hati-hati."*

— Kimi Code CLI, 2026-05-03
