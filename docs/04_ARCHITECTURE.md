# TECHNICAL ARCHITECTURE — ADO System
**Version:** 1.0
**Status:** Approved for Implementation
**Last Updated:** 2026-05-02

---

## 1. SYSTEM OVERVIEW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MIGANCORE.COM — CENTRAL HUB                     │
│              (Development + Production + Core Services)             │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────┐  ┌─────────────────────┐   │
│  │ api.         │  │ app.             │  │ lab.                │   │
│  │ migancore    │  │ migancore        │  │ migancore           │   │
│  │ (API GW)     │  │ (Dashboard)      │  │ (Observability)     │   │
│  └──────┬───────┘  └──────────────────┘  └─────────────────────┘   │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    CORE SERVICE LAYER                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │   │
│  │  │ LANGGRAPH│  │  LETTA   │  │  CELERY  │  │  QDRANT    │  │   │
│  │  │ Director │  │ Memory   │  │ Workers  │  │  Vectors   │  │   │
│  │  │ (Brain)  │  │+ Spawner │  │          │  │            │  │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │   │
│  │       │             │             │              │         │   │
│  │  ┌────┴─────────────┴─────────────┴──────────────┴──────┐  │   │
│  │  │              POSTGRESQL + REDIS + OLLAMA              │  │   │
│  │  │         (Data + Cache + Qwen2.5-7B Inference)         │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ API Calls (api.migancore.com)
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼─────┐        ┌──────▼──────┐       ┌─────▼──────┐
   │sidixlab  │        │  mighan     │       │  tiranyx   │
   │.com      │        │  .com       │       │  .com      │
   │(Research │        │  (Platform  │       │  (Project  │
   │Consumer) │        │  Consumer)  │       │  Owner)    │
   └──────────┘        └─────────────┘       └────────────┘
```

**Keterangan Arsitektur:**
- **migancore.com** = Satu-satunya lokasi development & deployment. Semua backend, model, memory, dan training berjalan di sini.
- **sidixlab.com** = Consumer channel untuk research. Frontend/UI yang consume API di `api.migancore.com`.
- **mighan.com** = Consumer channel untuk clone platform. Frontend/UI yang consume API di `api.migancore.com`.
- **tiranyx.com** = Consumer channel untuk governance. Frontend/UI yang consume API di `api.migancore.com`.

---

## 2. COMPONENT SPECIFICATIONS

### 2.1 Inference Layer — Ollama

| Parameter | Value |
|---|---|
| Model | `qwen2.5:7b-instruct-q4_K_M` |
| Context Window | 8192 tokens (initial), expand to 32K after validation |
| Parallel Requests | 2 (OLLAMA_NUM_PARALLEL=2) |
| Keep Alive | 24h |
| Memory Limit | 12GB (Docker) |
| Speculative Decoding | Qwen2.5-0.5B as draft model |
| Threads | 8 (all cores) |
| Port | 11434 (internal only) |

**Why Ollama over vLLM:**
- vLLM requires GPU for production efficiency
- Ollama + llama.cpp = CPU-optimized, 7–14 tokens/sec for 7B Q4 on 8-core
- OpenAI-compatible API = drop-in with all frameworks

### 2.2 Orchestration Layer — LangGraph

**State Schema:**
```python
class AgentState(TypedDict):
    messages: List[BaseMessage]
    tenant_id: str
    agent_id: str
    current_task: Optional[str]
    tool_calls: List[ToolCall]
    memory_context: str
    iteration_count: int
    max_iterations: int  # circuit breaker
    plan: Optional[str]
    reflections: List[str]
```

**Graph Nodes:**
```
[START]
   │
   ▼
[intent_classifier]  ─── routes ──► [chat_node] (simple Q&A)
   │                                [task_node] (multi-step)
   │                                [spawn_node] (agent creation)
   │                                [research_node] (paper/web)
   ▼
[planner]  ─── generates step-by-step plan
   │
   ▼
[memory_reader]  ─── loads relevant memory from Letta
   │
   ▼
[reasoner]  ─── LLM call with full context + tools
   │
   ├── has_tool_calls ──► [tool_executor] ──► [reasoner] (loop)
   │
   └── no_tool_calls ──► [response_synthesizer]
                                │
                                ▼
                         [reflector]  ─── log lesson, update memory
                                │
                                ▼
                         [feedback_logger]  ─── to Redis Streams
                                │
                                ▼
                             [END]
```

**Circuit Breaker:** max_iterations=10. If exceeded → return partial result + escalate.

### 2.3 Memory Layer — Letta

**Memory Block Architecture:**
```python
memory_blocks = [
    {
        "label": "persona",
        "value": open("SOUL.md").read(),  # always full SOUL.md
        "limit": 4096
    },
    {
        "label": "human",
        "value": "Owner: [name], Role: [role], Preferences: [...]",
        "limit": 2048
    },
    {
        "label": "current_task",
        "value": "",  # updated per session
        "limit": 2048
    },
    {
        "label": "world_state",
        "value": "",  # running facts about the world
        "limit": 2048
    }
]
```

**Recall Memory:** Last N messages (default: 50) stored in Postgres, searchable.

**Archival Memory:** All historical context stored in Qdrant collection `archival_{agent_id}`, embedded with BGE-M3 (1024 dims).

**Sleep-Time Compute:** When agent idle > 1 hour, background process consolidates episodic → semantic memory.

### 2.4 Vector Store — Qdrant

**Collections:**
```
semantic_{agent_id}      — facts, entities, relationships
episodic_{agent_id}      — conversation summaries
archival_{agent_id}      — long-term memory
kb_{tenant_id}_{slug}    — uploaded knowledge bases
papers                   — research papers (Sidixlab)
kg_entities              — knowledge graph nodes
```

**Embedding Model:** BGE-M3 via `fastembed` (CPU, ~380MB model, no extra GPU needed)

### 2.5 Event Bus — Redis Streams

**Streams:**
```
feedback.events          — user interactions for training data collection
agent.spawned            — new agent lifecycle events
agent.retired            — agent deactivation
training.triggered       — training pipeline start signals
task.queued              — new tasks for specialist workers
task.completed           — task results back to orchestrator
```

**Consumer Groups:**
```
feedback.events   → GROUP feedback_processors (1 consumer)
task.queued       → GROUP workers (1 consumer per queue type)
training.triggered → GROUP training_runner (1 consumer)
```

### 2.6 Task Queue — Celery

**Queues and Workers:**
```
code      — CodeSpecialist (python_repl, git operations)
web       — WebSpecialist (Playwright, scraping)
research  — ResearchSpecialist (ArXiv, Tavily)
audio     — AudioSpecialist (Coqui TTS, Piper)
training  — TrainingWorker (triggers RunPod job)
kb        — KBWorker (vectorize uploaded docs)
```

**Priority:** code=9, web=7, research=5, audio=5, training=1, kb=3

---

## 3. DATA FLOW DIAGRAMS

### 3.1 Standard Conversation Flow

```
User Request
     │
     ▼
FastAPI (/v1/agents/{id}/chat)
     │ validate JWT, extract tenant_id
     ▼
LangGraph Director
     │ intent classification
     │ load memory from Letta
     │ build full context
     ▼
Ollama (Qwen2.5-7B)
     │ reasoning + tool selection
     ▼
Tool Executor (if needed)
     │ web_search / python_repl / etc
     ▼
Response Synthesizer
     │
     ├──► Letta (update memory blocks)
     ├──► Redis Streams (log for training)
     ├──► Postgres (log message)
     └──► User Response
```

### 3.2 Agent Spawn Flow

```
POST /v1/agents/spawn
     │ validate JWT + quota check
     ▼
Resolve Personality Template
     │ merge with customizations
     │ render final SOUL.md variant
     ▼
Letta API: agents.create()
     │ memory blocks initialized
     ▼
Postgres: INSERT agents row
     │ parent_agent_id = Core Brain
     ▼
Celery: kb.ingest (async)
     │ vectorize owner's documents
     ▼
Return: {agent_id, webhook_url}
```

### 3.3 Self-Improvement Flow (Weekly)

```
Sunday 02:00 WIB — Celery beat trigger
     │
     ▼
Sample 1000 interactions from Postgres
     │ filter: quality_score > 0 OR has_feedback
     ▼
LLM-as-Judge (Hermes-3-8B local)
     │ evaluate each interaction vs Constitution
     │ generate preference pairs (chosen/rejected)
     ▼
Filter: keep pairs with judge_score > 0.7
     │
     ▼
Trigger RunPod Job (via API)
     │ template: Unsloth + SimPO + Qwen2.5-7B
     │ dataset: new preference pairs
     ▼
Fine-tuning (4–8 hours, RTX 4090)
     │ output: LoRA adapter GGUF
     ▼
Download adapter to VPS
     │
     ▼
Identity Consistency Test
     │ run 5 fingerprint prompts
     │ cosine similarity > 0.85?
     ▼
     ├── PASS → Hot-swap in Ollama → A/B 10%
     └── FAIL → Rollback, log, investigate
```

---

## 4. API SPECIFICATION

### 4.1 Core Endpoints

```
POST   /v1/auth/register        — User registration
POST   /v1/auth/login           — Get JWT
GET    /v1/auth/me              — Current user info

GET    /v1/agents               — List user's agents
POST   /v1/agents/spawn         — Create new agent
GET    /v1/agents/{id}          — Get agent details
PUT    /v1/agents/{id}/persona  — Update personality
DELETE /v1/agents/{id}          — Archive agent

POST   /v1/agents/{id}/chat     — Send message to agent
GET    /v1/agents/{id}/memory   — View agent memory
POST   /v1/agents/{id}/memory/ingest — Add documents to KB
GET    /v1/agents/{id}/lineage  — View agent family tree

GET    /v1/models               — List model versions
GET    /v1/models/{version}/eval — Get eval scores

POST   /v1/admin/training/trigger — Manual training trigger
GET    /v1/admin/system/health   — System health check
GET    /v1/admin/system/metrics  — RAM, GPU, queue depths
```

### 4.2 WebSocket

```
WS /v1/agents/{id}/stream       — Streaming chat (token by token)
```

### 4.3 Webhook (Mighan Platform)

Agents can have webhooks that receive POST callbacks:
```json
{
  "event": "message",
  "agent_id": "...",
  "conversation_id": "...",
  "message": { "role": "user", "content": "..." },
  "response": { "role": "assistant", "content": "...", "tool_calls": [...] }
}
```

---

## 5. SECURITY ARCHITECTURE

### 5.1 Authentication Flow

```
User → POST /auth/login
     → verify password (bcrypt)
     → generate JWT {user_id, tenant_id, agent_ids, plan, exp}
     → sign with RS256 private key
     → return {access_token, refresh_token}

Request → extract Bearer token
        → verify RS256 signature
        → extract claims
        → set pg session variable: app.current_tenant = tenant_id
        → RLS policies apply automatically
```

### 5.2 Row-Level Security

```sql
-- Applied to ALL tables with tenant_id
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON agents
  USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Agent tools — additional check
CREATE POLICY agent_tool_scope ON agent_tool_grants
  USING (
    agent_id IN (SELECT id FROM agents WHERE owner_user_id = current_user_id())
  );
```

### 5.3 Secrets Management

```
.env file → chmod 600, not in git
JWT RS256 key pair → generated at VPS init, stored in /etc/ado/keys/
API keys → Fernet-encrypted in Postgres (per-tenant BYOK)
Redis passwords → in .env
Database URL → in .env
```

---

## 6. INFRASTRUCTURE AS CODE

### 6.1 docker-compose.yml (Complete)

```yaml
version: "3.9"
services:
  ollama:
    image: ollama/ollama:latest
    restart: unless-stopped
    volumes:
      - ./data/ollama:/root/.ollama
    environment:
      OLLAMA_NUM_PARALLEL: "2"
      OLLAMA_MAX_LOADED_MODELS: "1"
      OLLAMA_KEEP_ALIVE: "24h"
    deploy:
      resources:
        limits: { memory: 12G }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/"]
      interval: 30s

  postgres:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    environment:
      POSTGRES_DB: ado
      POSTGRES_USER: ado
      POSTGRES_PASSWORD: ${PG_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./migrations/init.sql:/docker-entrypoint-initdb.d/init.sql
    deploy:
      resources:
        limits: { memory: 4G }
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "ado"]

  qdrant:
    image: qdrant/qdrant:v1.9.0
    restart: unless-stopped
    volumes:
      - ./data/qdrant:/qdrant/storage
    environment:
      QDRANT__SERVICE__API_KEY: ${QDRANT_API_KEY}
    deploy:
      resources:
        limits: { memory: 4G }

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 1500mb
      --maxmemory-policy allkeys-lru
    volumes:
      - ./data/redis:/data
    deploy:
      resources:
        limits: { memory: 2G }

  letta:
    image: letta/letta:0.6.0
    restart: unless-stopped
    environment:
      LETTA_PG_URI: postgresql://ado:${PG_PASSWORD}@postgres:5432/ado
      LETTA_OLLAMA_BASE_URL: http://ollama:11434
      LETTA_SERVER_PASSWORD: ${LETTA_PASSWORD}
      SECURE: "true"
    depends_on:
      postgres: { condition: service_healthy }
      ollama: { condition: service_healthy }
    deploy:
      resources:
        limits: { memory: 3G }

  api:
    build: { context: ./api, dockerfile: Dockerfile }
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://ado:${PG_PASSWORD}@postgres:5432/ado
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      QDRANT_URL: http://qdrant:6333
      QDRANT_API_KEY: ${QDRANT_API_KEY}
      OLLAMA_URL: http://ollama:11434
      LETTA_URL: http://letta:8283
      LETTA_PASSWORD: ${LETTA_PASSWORD}
      JWT_PRIVATE_KEY_PATH: /etc/ado/keys/private.pem
      JWT_PUBLIC_KEY_PATH: /etc/ado/keys/public.pem
    volumes:
      - /etc/ado/keys:/etc/ado/keys:ro
    depends_on: [postgres, qdrant, redis, letta, ollama]
    deploy:
      resources:
        limits: { memory: 2G }

  worker_code:
    build: { context: ./api, dockerfile: Dockerfile }
    command: celery -A app.celery worker -Q code -c 2 -l info
    restart: unless-stopped
    environment: *api_env
    deploy:
      resources:
        limits: { memory: 1G }

  worker_web:
    build: { context: ./api, dockerfile: Dockerfile }
    command: celery -A app.celery worker -Q web -c 2 -l info
    restart: unless-stopped
    environment: *api_env

  worker_research:
    build: { context: ./api, dockerfile: Dockerfile }
    command: celery -A app.celery worker -Q research,kb,training -c 1 -l info
    restart: unless-stopped
    environment: *api_env

  langfuse:
    image: langfuse/langfuse:2
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://ado:${PG_PASSWORD}@postgres:5432/langfuse
      NEXTAUTH_SECRET: ${LANGFUSE_SECRET}
      NEXTAUTH_URL: https://lab.sidixlab.com
      SALT: ${LANGFUSE_SALT}
    depends_on: [postgres]
    deploy:
      resources:
        limits: { memory: 1G }

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./data/caddy:/data
      - ./config/caddy:/config

networks:
  default:
    name: ado_network
```

### 6.2 Caddyfile

```caddyfile
# MIGANCORE.COM — Central Hub Reverse Proxy
# Semua core services berjalan di migancore.com
# sidixlab.com, mighan.com, tiranyx.com = consumer (external)

api.migancore.com {
  reverse_proxy api:8000
}

app.migancore.com {
  reverse_proxy frontend:3000
}

lab.migancore.com {
  reverse_proxy langfuse:3000
}

studio.migancore.com {
  reverse_proxy studio:3000
}

migancore.com, www.migancore.com {
  redir https://app.migancore.com{uri}
}
```

---

## 7. MEMORY BUDGET

| Service | RAM Allocation | Justification |
|---|---|---|
| Ollama (7B Q4) | 12 GB | Model ~5GB + KV cache + overhead |
| PostgreSQL | 4 GB | Shared buffers + connections |
| Qdrant | 4 GB | Vector index + collections |
| Redis | 2 GB | Streams + Celery + cache |
| Letta | 3 GB | Agent state management |
| API + Workers | 4 GB | 3 worker processes + API |
| Langfuse | 1 GB | Observability |
| OS + Caddy + misc | 2 GB | System overhead |
| **TOTAL** | **32 GB** | ✅ Fits exactly with 0 headroom |

**⚠️ WARNING:** Zero headroom at peak. Mitigations:
- Ollama OLLAMA_NUM_PARALLEL=1 during training runs
- Disable Langfuse during memory-intensive operations
- 8GB swap file configured on VPS disk

---

## 8. DISK BUDGET (400GB)

| Data | Allocation |
|---|---|
| Ollama models (Qwen2.5-7B + draft) | 8 GB |
| Additional models (Phi-4, Hermes-3) | 12 GB |
| PostgreSQL data | 50 GB |
| Qdrant vectors | 30 GB |
| Redis snapshots | 5 GB |
| Letta state | 10 GB |
| Training datasets | 20 GB |
| LoRA adapters / checkpoints | 30 GB |
| Application code + logs | 15 GB |
| Backups (rolling 7 days) | 70 GB |
| Free buffer | 150 GB |
| **TOTAL** | **400 GB** |
