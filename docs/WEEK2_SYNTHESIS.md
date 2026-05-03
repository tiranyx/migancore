# MIGANCORE — WEEK 2 SYNTHESIS.md
**Consolidated Research: Kimi + GPT-5.5 + Claude Code**

**Date:** 2026-05-03  
**Status:** Research Complete — Ready for Implementation  
**Version:** v0.3.1 + Week 2 Planning

> **⚠️ CORE PRINCIPLE (from GPT-5.5):**
> "Jangan tambah 'otak' sebelum tambah 'sistem imun'."
> Safety gates dulu. Letta nanti.

---

## EXECUTIVE SUMMARY

Setelah 3 agent melakukan riset mendalam (Kimi: infrastructure & deployment, GPT-5.5: strategy & security, Claude Code: implementation details), berikut rekomendasi Week 2 yang sudah disepakati:

| Day | Feature | Agent Lead | Status |
|-----|---------|-----------|--------|
| 11 | **Safety Gate + Tool Policy** | Kimi | 🔴 P0 — Must Do First |
| 12 | **Qdrant RAG Tier 2** | Kimi | 🟡 P1 — Core Feature |
| 13 | **Letta Tier 3 Memory** | Kimi | 🟡 P1 — Optional Integration |
| 14 | **MCP Adapter** | Kimi | 🟡 P1 — Future-Proofing |
| 15-17 | **Data Ledger** | Kimi | 🟢 P2 — Foundation for Training |

---

## 1. DAY 11 — SAFETY GATE + TOOL POLICY (P0)

### 1.1 Why Safety First? (GPT-5.5 Assessment)
> "Aha moment paling cepat bukan Letta atau training. Aha moment-nya adalah: user membuat parent agent, spawn child agent, child punya persona berbeda, ingat sesuatu, lalu memakai satu tool aman dengan trace yang terlihat."

Tapi tanpa safety gate, child agent bisa:
- Spawn recursively tanpa limit
- Panggil tool destructive tanpa approval
- Modify persona walaupun `persona_locked=true`
- Escape subprocess sandbox via python_repl

### 1.2 Tool Policy Framework

GPT-5.5 merekomendasikan 6 tool classifications:

| Class | Description | Examples | Enforcement |
|-------|-------------|----------|-------------|
| `read_only` | Read data, no side effects | web_search, memory_search | Auto-allow |
| `write` | Write data, reversible | memory_write | Auto-allow |
| `destructive` | Delete/modify permanent data | DELETE endpoints | Requires approval |
| `open_world` | Call external APIs | http_get | Requires approval |
| `requires_approval` | Always need human OK | spawn_agent | Always approval |
| `sandbox_required` | Execute code | python_repl | Sandboxed only |

### 1.3 Implementation Plan

**A. Tool Policy Schema (update `skills.json`)**
```json
{
  "id": "spawn_agent",
  "policy": {
    "class": "requires_approval",
    "max_daily_calls": 10,
    "requires_sandbox": false,
    "approval_timeout_seconds": 300
  }
}
```

**B. Approval Gate Middleware**
- `services/tool_executor.py` checks policy before executing
- If `requires_approval`: queue for human approval (async notification)
- If `sandbox_required`: run in gVisor/nsjail (defer to Week 3 if complex)

**C. Spawn Limits**
- Enforce `tenants.max_agents` before create/spawn
- Track `generation` depth (max 5 generations?)
- Rate limit: max 3 spawns per hour per parent

**D. Persona Lock Enforcement**
- If `persona_locked=true`, reject any persona modification
- Enforce at API level, not just DB level

### 1.4 Acceptance Criteria
- [ ] `skills.json` has `policy` field for every tool
- [ ] `ToolExecutor.execute()` checks policy before running
- [ ] Spawn endpoint enforces `max_agents`
- [ ] Persona locked agents reject modification
- [ ] python_repl marked as `sandbox_required` (even if sandbox not ready)

---

## 2. DAY 12 — QDRANT RAG TIER 2 (P1)

### 2.1 Key Finding (Claude Code)
> "BAAI/bge-m3 tidak support fastembed 0.5.0 natively. Model terbaik untuk Bahasa Indonesia: **paraphrase-multilingual-mpnet-base-v2** (768-dim, 1GB, support id lang natively)."

### 2.2 Embedding Model Decision

| Model | Dim | Size | id-lang | Speed | Quality | Verdict |
|-------|-----|------|---------|-------|---------|---------|
| all-MiniLM-L6-v2 | 384 | 22MB | ❌ No | Fastest | Good | ❌ Skip |
| BGE-small-en-v1.5 | 384 | 33MB | ❌ No | Fast | Better | ❌ Skip |
| **paraphrase-multilingual-mpnet** | **768** | **1GB** | **✅ Yes** | **Medium** | **Best** | **✅ USE** |
| bge-m3 | 1024 | 567MB | ✅ Yes | Slow | SOTA | ⚠️ Heavy |

**Decision: paraphrase-multilingual-mpnet-base-v2**
- Native Bahasa Indonesia support
- 1GB RAM acceptable for VPS
- Better quality than MiniLM

### 2.3 Chunking Strategy (Claude Code)

**Decision: Turn-pair chunking**
- Unit: 1 user message + 1 assistant response = 1 chunk
- Reason: preserves conversational context naturally
- Alternative (rejected): per-message chunking loses turn context

### 2.4 Qdrant Schema (GPT-5.5 + Claude)

**Decision: Single collection per embedding model**
```
Collection: "migan_memory_v1"
  ├── vector: 768-dim (paraphrase-multilingual-mpnet)
  ├── payload:
  │     ├── tenant_id (filter)
  │     ├── agent_id (filter)
  │     ├── conversation_id (filter)
  │     ├── memory_type: "conversation" | "document" | "fact"
  │     ├── created_at
  │     └── content
  └── index: HNSW
```

**Why NOT collection per tenant?**
- Overhead: too many collections = memory bloat
- Filtering by tenant_id in payload is sufficient with RLS

### 2.5 Implementation Plan

**A. `services/rag.py` skeleton**
```python
async def chunk_turns(messages: list[Message]) -> list[Chunk]:
    """Group into (user, assistant) turn pairs."""

async def embed_chunks(chunks: list[Chunk]) -> list[Embedding]:
    """Use paraphrase-multilingual-mpnet via asyncio.to_thread()."""

async def store_chunks(tenant_id, agent_id, chunks):
    """Upsert to Qdrant with payload filtering."""

async def search_memory(tenant_id, agent_id, query, k=5):
    """Embed query, search Qdrant, filter by tenant+agent."""
```

**B. Integration with Chat Flow**
1. User sends message
2. System embeds query → search Qdrant → get top 5 relevant past turns
3. Inject relevant context into system prompt
4. Call Ollama with enriched prompt

**C. Performance Target**
- Embedding: ~100ms per chunk (CPU, via asyncio.to_thread)
- Search: 20-50ms end-to-end (Claude measured)
- Total RAG overhead: <200ms (acceptable for chat)

### 2.6 Acceptance Criteria
- [ ] `services/rag.py` implemented with turn-pair chunking
- [ ] Embedding model: paraphrase-multilingual-mpnet-base-v2
- [ ] Qdrant collection: single collection, payload filtering
- [ ] Search latency <200ms
- [ ] Integration with chat endpoint (inject context into system prompt)

---

## 3. DAY 13 — LETTA TIER 3 MEMORY (P1)

### 3.1 Key Finding (Claude Code)
> "Qwen2.5 Q4 model kita di bawah threshold Q6 yang Letta rekomendasikan untuk tool calls. Solusi: gunakan Letta sebagai **passive storage saja** — panggil `blocks.retrieve()` dan `blocks.update()` langsung, jangan invoke `agents.messages.create()`."

### 3.2 Architecture Decision

**Passive Storage Pattern (NOT Active Agent)**
```
MiganCore Agent          Letta Agent
     │                        │
     ├─ create ──────────────▶│
     │   (maps to Letta agent)│
     │                        │
     ├─ chat ────────────────▶│
     │   ├─ retrieve persona block ─┤
     │   ├─ retrieve human block ───┤
     │   ├─ retrieve world block ───┤
     │   └─ inject into prompt ─────┤
     │                        │
     ├─ memory update ───────▶│
     │   └─ update world block ─────┤
```

**Why passive?**
- Avoids Letta's tool calling instability with Q4 models
- Keeps our LangGraph director as single orchestrator
- Letta = memory storage, not reasoning engine

### 3.3 Implementation Plan

**A. `services/letta_bridge.py` (async)**
```python
class LettaBridge:
    def __init__(self, base_url="http://letta:8283"):
        self.client = AsyncLetta(base_url=base_url)

    async def create_agent(self, migan_agent: Agent) -> str:
        """Create Letta agent, return letta_agent_id."""
        # Map SOUL.md → persona block
        # Map user profile → human block
        # Map Redis memories → world_state block

    async def get_memory_blocks(self, letta_agent_id: str) -> dict:
        """Retrieve persona, human, world_state blocks."""

    async def update_world_state(self, letta_agent_id: str, new_facts: list[str]):
        """Append new facts to world_state block."""
```

**B. Feature Flag**
- `settings.LETTA_ENABLED` (default: False)
- If Letta down → graceful fallback to Redis only
- No chat interruption if Letta unavailable

**C. Resource Budget**
- Letta container: ~500-850MB RAM (Claude measured)
- With our 32GB VPS, this is acceptable

### 3.4 Acceptance Criteria
- [ ] `services/letta_bridge.py` with async API
- [ ] Feature flag `LETTA_ENABLED`
- [ ] Graceful fallback when Letta down
- [ ] Memory blocks sync: SOUL.md → persona, Redis → world_state

---

## 4. DAY 14 — MCP ADAPTER (P1)

### 4.1 Key Finding (GPT-5.5)
> "MCP modern tidak lagi HTTP+SSE. Spec resmi 2025-03-26 mengganti dengan **Streamable HTTP**, plus stdio tetap penting."

### 4.2 Transport Correction

| Transport | Status | Use Case |
|-----------|--------|----------|
| HTTP+SSE | ❌ **DEPRECATED** | Don't use |
| **Streamable HTTP** | ✅ **Current** | Remote servers |
| **stdio** | ✅ **Current** | Local servers |

### 4.3 Implementation Plan

**A. MCP Server (expose OUR tools)**
- Package: `pip install "mcp[cli]"` (v1.27.0)
- Expose 3 tools via MCP: `web_search`, `memory_search`, `http_get`
- Keep native (NOT MCP): `python_repl`, `memory_write`, `spawn_agent`
- Why? Security — destructive tools stay internal

**B. MCP Client (consume EXTERNAL tools)**
- Connect to Composio (200+ SaaS tools)
- Connect to custom MCP servers
- Feature flag: `MCP_CLIENT_ENABLED`

**C. skills.json = Source of Truth**
- `skills.json` tetap internal format
- Build exporter: `skills.json` → MCP tool schema
- Build importer: MCP tool schema → `skills.json`
- Zero migration needed (our schema already compatible)

### 4.4 Security (GPT-5.5)
- Tool approval gates for external MCP tools
- Sandboxing for untrusted MCP servers
- Prevent tool name collisions

### 4.5 Acceptance Criteria
- [ ] MCP server running locally (stdio + streamable-http)
- [ ] 3 tools exposed: web_search, memory_search, http_get
- [ ] MCP client can connect to Composio
- [ ] Tool approval gate for external tools

---

## 5. DAY 15-17 — DATA LEDGER (P2)

### 5.1 Key Finding (GPT-5.5)
> "Training jangan dimulai dari fine-tune. Mulai dari **data ledger**: prompt, response, tool_calls, user feedback, chosen/rejected, PII scrubber, eval set. DPO/SimPO/Unsloth baru masuk setelah ada data preferensi yang cukup."

### 5.2 Data Ledger Schema

```sql
CREATE TABLE training_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    tool_calls JSONB,
    model_version VARCHAR(64),
    -- Feedback signals
    user_rating INTEGER,  -- 1-5 or thumbs up/down
    user_feedback TEXT,
    -- Preference pairs (for DPO)
    chosen_response TEXT,
    rejected_response TEXT,
    preference_source VARCHAR(32), -- 'human', 'llm_judge', 'implicit'
    -- Quality metrics
    response_time_ms INTEGER,
    token_count INTEGER,
    -- PII & safety
    pii_scrubbed BOOLEAN DEFAULT false,
    toxic_flag BOOLEAN DEFAULT false,
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    -- Evaluation split
    eval_split VARCHAR(16) DEFAULT 'train' -- 'train', 'val', 'test'
);
```

### 5.3 Data Collection Pipeline

1. **Automatic collection**: Every chat turn → insert to `training_data`
2. **User feedback**: thumbs up/down + optional text feedback
3. **LLM-as-judge**: Compare response vs alternative, score quality
4. **PII scrubber**: Detect and redact personal information
5. **Toxic filter**: Flag harmful content

### 5.4 Training Trigger

**When to start training?**
- Minimum: 500 preference pairs (Claude estimate)
- Target: 2000+ pairs for meaningful improvement
- Trigger: manual (founder review) or automatic (weekly)

### 5.5 Training Configuration (Claude Code)

**Hardware:**
- RunPod RTX 4090 Community Cloud: **$0.34/hr** (bukan $0.69 Secure Cloud)
- 500 pairs × 3 epochs = ~18 menit = **~$0.10**

**Method:**
- DPO (not GRPO) — GRPO is for reasoning, not chat alignment
- LoRA rank 32, alpha 64
- PatchDPOTrainer() must be called BEFORE importing DPOTrainer

**Export:**
- Merge LoRA → full model → GGUF for Ollama
- Bug fix: `pip install --force-reinstall unsloth-zoo unsloth` before export

### 5.6 Acceptance Criteria
- [ ] `training_data` table created
- [ ] Automatic collection from chat endpoint
- [ ] User feedback UI (thumbs up/down)
- [ ] PII scrubber implemented
- [ ] 500+ pairs collected before any training

---

## 6. KOREKSI PENTING

### 6.1 MCP Transport (from GPT-5.5)
- ❌ Jangan desain dengan HTTP+SSE (deprecated)
- ✅ Gunakan **Streamable HTTP** atau **stdio**
- Spec resmi: modelcontextprotocol.io/specification/2025-03-26

### 6.2 Model Quality for Letta (from Claude)
- Qwen2.5 Q4_K_M di bawah threshold Letta untuk tool calls
- Solusi: Letta sebagai **passive storage only**
- Jangan invoke `agents.messages.create()` — langsung `blocks.retrieve/update()`

### 6.3 Embedding Model (from Claude)
- ❌ BGE-small-en (English only)
- ❌ bge-m3 (bug dengan fastembed)
- ✅ **paraphrase-multilingual-mpnet-base-v2** (Bahasa Indonesia native)

### 6.4 Training Cost (from Claude)
- RunPod RTX 4090 Community Cloud: **$0.34/hr** (bukan $0.74)
- 500 pairs × 3 epochs: ~18 menit = **$0.10**
- Much cheaper than estimated

### 6.5 Training Method (from Claude)
- ❌ GRPO (for reasoning, not chat)
- ✅ **DPO** (Direct Preference Optimization) for chat alignment

---

## 7. NON-NEGOTIABLE CONSTRAINTS (from GPT-5.5)

1. **Single 32GB VPS** — no horizontal scaling yet
2. **SIDIX/Ixonomic must remain zero-downtime** — deploy carefully
3. **python_repl is unsafe until sandboxed** — marked as `sandbox_required`
4. **tenant.max_agents must be enforced** — before any autonomous spawning
5. **MCP target: stdio + Streamable HTTP** — NOT legacy HTTP+SSE
6. **Letta is Tier 3 memory, not replacement director** — LangGraph stays

---

## 8. Sumber Resmi yang Digunakan

| Agent | Sumber |
|-------|--------|
| GPT-5.5 | MCP transport spec, MCP changelog 2025-03-26, MCP authorization, MCP tool annotations, OWASP LLM Top 10, OWASP Agentic Skills Top 10 |
| Claude Code | Letta memory blocks, Qdrant multitenancy, Qdrant hybrid search, TRL DPO Trainer, Unsloth docs |
| Kimi | Letta Python SDK docs, Qdrant docs, MCP spec overview, LLaMA Factory guide |

---

## 9. NEXT STEPS

1. **Kimi (sekarang):** Implement Day 11 — Safety Gate + Tool Policy
2. **Claude Code (nanti):** Implement Day 12 — Qdrant RAG (code skeleton sudah di docs/CLAUDE_RESEARCH_WEEK2.md)
3. **GPT-5.5 (nanti):** Review Day 13-14 — Letta + MCP integration plan
4. **Semua:** Day 15-17 — Data Ledger (foundation untuk training)

---

*Synthesized from: Kimi Code CLI (infrastructure), GPT-5.5 (strategy), Claude Code (implementation). Consensus reached on all major decisions.*
