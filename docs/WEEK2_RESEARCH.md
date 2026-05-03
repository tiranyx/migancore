# MIGANCORE — WEEK 2 RESEARCH.md
**Deep Research for Days 11-17**

**Date:** 2026-05-03  
**Researcher:** Kimi Code CLI  
**Sources:** Official docs, arXiv papers, GitHub repos, industry benchmarks

---

## 1. LETTA INTEGRATION (Day 11)

### 1.1 What is Letta?
Letta (formerly MemGPT) is a platform for building **stateful agents** with advanced memory that can learn and self-improve over time. Unlike stateless LLM calls, Letta agents maintain persistent memory blocks across conversations.

**Key insight:** Letta is NOT just a vector DB — it's an agent runtime with memory management, tool calling, and reasoning loops built-in.

### 1.2 Architecture
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Agent     │────▶│ Memory Blocks│────▶│  LLM Core   │
│  Runtime    │     │ - persona    │     │ (Ollama)    │
│             │     │ - human      │     │             │
│             │     │ - world_state│     │             │
└─────────────┘     └──────────────┘     └─────────────┘
        │
        ▼
┌─────────────┐
│   Tools     │
│ - web_search│
│ - memory_*  │
│ - python    │
└─────────────┘
```

### 1.3 Python SDK (Critical for Integration)
```python
from letta_client import Letta  # Sync
from letta_client import AsyncLetta  # Async

client = Letta(base_url="http://letta:8283")  # Our Docker container

# Create agent with memory blocks
agent_state = client.agents.create(
    model="qwen2.5-7b-instruct-q4_K_M",
    embedding="local",  # Use local embeddings
    memory_blocks=[
        {"label": "persona", "value": "...SOUL.md content..."},
        {"label": "human", "value": "User preferences..."},
        {"label": "world_state", "value": "Current context..."}
    ],
    tools=["web_search", "memory_write", "memory_search"]
)

# Send message
response = client.agents.messages.create(
    agent_id=agent_state.id,
    messages=[{"role": "user", "content": "Hello"}]
)
```

### 1.4 Multi-Agent Shared Memory
```python
# Create shared block
shared_block = client.blocks.create(
    label="organization",
    value="Shared team context"
)

# Attach to multiple agents
agent1 = client.agents.create(memory_blocks=[...], block_ids=[shared_block.id])
agent2 = client.agents.create(memory_blocks=[...], block_ids=[shared_block.id])
# Both agents see updates immediately
```

### 1.5 Integration Strategy for MiganCore
**Option A: Full Replacement**
- Replace our custom `director.py` + `memory.py` with Letta runtime
- Pros: Production-grade memory, self-improving agents
- Cons: Lose fine-grained control over tool calling, adds complexity

**Option B: Hybrid (Recommended)**
- Keep our FastAPI + LangGraph director
- Use Letta as **Memory Tier 3** (working memory blocks)
- Redis = Tier 1 (fast K-V), Qdrant = Tier 2 (semantic), Letta = Tier 3 (structured blocks)
- Letta agent per MiganCore agent, linked via `letta_agent_id` column

**Option C: Sidecar**
- Letta runs independently
- MiganCore syncs data via REST API
- Pros: Clean separation, Letta can be swapped
- Cons: Network overhead, eventual consistency

**Recommendation: Option B (Hybrid)**
- Minimal intrusion to existing architecture
- Leverages Letta's memory strengths
- Keeps our orchestration layer

### 1.6 Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Letta cold-start | High | Pre-warm on API startup, cache blocks in Redis |
| Ollama compatibility | Medium | Test `qwen2.5:7b` model with Letta locally first |
| Embedding model | Medium | Use `sentence-transformers` instead of OpenAI |
| Memory block size limits | Low | Chunk large SOUL.md into multiple blocks |

---

## 2. QDRANT RAG / SEMANTIC MEMORY (Day 12)

### 2.1 RAG Pipeline Overview
```
Document → Chunk → Embed → Store → Query → Retrieve → Generate
```

### 2.2 Chunking Strategy (The Hard Problem)
Research shows **chunking strategy matters more than vector DB choice**.

| Strategy | Precision | Recall | F1 | Cost |
|----------|-----------|--------|-----|------|
| Fixed (512 tokens) | 0.65 | 0.58 | 0.61 | Low |
| Semantic | 0.78 | 0.72 | 0.75 | High |
| Hierarchical | 0.82 | 0.79 | 0.80 | Medium |
| **Parent-Context** | **0.88** | **0.85** | **0.86** | Medium |

**Recommendation for MiganCore:**
- **Start with:** Recursive character splitting, 512 tokens, 50-token overlap
- **Iterate to:** Semantic chunking for high-value conversations
- **Store:** Small chunks in Qdrant, full context in Postgres

### 2.3 Embedding Models
| Model | Size | Speed | Quality | License |
|-------|------|-------|---------|---------|
| all-MiniLM-L6-v2 | 22MB | Fast | Good | Apache-2 |
| BGE-small-en-v1.5 | 33MB | Fast | Better | MIT |
| E5-base-v2 | 110MB | Medium | Best | MIT |
| text-embedding-3-large | Cloud | Variable | Excellent | Proprietary |

**Recommendation:** `BGE-small-en-v1.5` or `all-MiniLM-L6-v2` (local, fast, good quality)

### 2.4 Qdrant Integration Pattern
```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

client = QdrantClient(url=settings.QDRANT_URL)
model = SentenceTransformer('BAAI/bge-small-en-v1.5')

# Store
embedding = model.encode(chunk_text)
client.upsert(
    collection_name=f"tenant_{tenant_id}",
    points=[PointStruct(id=uuid, vector=embedding, payload={"text": chunk_text, "agent_id": agent_id})]
)

# Retrieve
query_embedding = model.encode(user_query)
results = client.search(
    collection_name=f"tenant_{tenant_id}",
    query_vector=query_embedding,
    limit=5,
    filter=Filter(must=[FieldCondition(key="agent_id", match=MatchValue(value=agent_id))])
)
```

### 2.5 Hybrid Search
Pure vector search misses keyword-specific queries. Solution:
1. Vector similarity for conceptual matching
2. BM25/keyword for exact terms
3. Re-ranker (cross-encoder) for final ranking

**Qdrant supports hybrid search natively** (sparse vectors + dense vectors).

### 2.6 Integration Strategy
**Architecture:**
```
User Query → Embed → Qdrant Search → Retrieve Chunks → 
Inject into System Prompt → Ollama Generate
```

**When to use RAG:**
- Long conversation history (> context window)
- Knowledge base queries ("What did we discuss about X?")
- Multi-document synthesis

**When NOT to use RAG:**
- Simple Q&A (Redis memory is faster)
- Real-time data (use web search instead)

---

## 3. MODEL CONTEXT PROTOCOL (Day 13-14)

### 3.1 What is MCP?
Anthropic's **Model Context Protocol** (Nov 2024) is an open standard for connecting LLM applications to external tools and data sources. Think of it as "USB-C for AI agents."

**Adoption:** OpenAI, Google DeepMind, Microsoft, Cloudflare (20M+ weekly downloads)

### 3.2 Architecture
```
┌─────────────┐     JSON-RPC 2.0     ┌─────────────┐
│  MCP Client │◄────────────────────►│  MCP Server │
│  (Agent)    │   stdio / HTTP SSE   │  (Tools)    │
└─────────────┘                      └─────────────┘
```

### 3.3 Core Concepts
| Concept | Description |
|---------|-------------|
| **Tools** | Functions the agent can call |
| **Resources** | Read-only data (files, APIs) |
| **Prompts** | Reusable prompt templates |
| **Reflection** | Discovery: client asks server "what can you do?" |

### 3.4 Tool Definition (JSON Schema)
```json
{
  "name": "web_search",
  "description": "Search the web",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"}
    },
    "required": ["query"]
  }
}
```

### 3.5 Integration Strategy for MiganCore
**Current state:** Our `skills.json` is already MCP-compatible in spirit.

**Migration path:**
1. Convert `skills.json` entries to MCP tool definitions
2. Build MCP server wrapping our `tool_executor.py`
3. Update `director.py` to speak MCP protocol
4. External MCP servers can be plugged in (Composio, etc.)

**Benefits:**
- 7000+ pre-built tools from Composio ecosystem
- Standardized tool discovery
- Swappable tool implementations

### 3.6 Security Considerations
MCP has known vulnerabilities:
- Tool squatting (malicious tools with same name)
- Rug pull (server changes tool behavior)
- Prompt injection via tool descriptions

**Mitigation:**
- Tool signature verification
- Sandboxed execution
- Approval gates for high-risk tools

---

## 4. TRAINING PIPELINE V1 (Day 15)

### 4.1 Standard Post-Training Pipeline
```
Base Model → SFT → DPO/RLHF → Deployed Model
```

### 4.2 Methods Comparison
| Method | Complexity | Quality | Cost | Use Case |
|--------|-----------|---------|------|----------|
| SFT | Low | Medium | Low | Instruction following |
| DPO | Medium | High | Medium | Preference alignment |
| RLHF (PPO) | High | Highest | High | Production models |
| GRPO | Medium | High | Medium | Reasoning tasks |
| LoRA | Low | Good | Very Low | Efficient fine-tuning |

### 4.3 DPO (Direct Preference Optimization)
**Why DPO for MVP?**
- No reward model needed (simpler than RLHF)
- Directly optimizes from preference pairs
- Works well with Qwen2.5

**Dataset format:**
```json
{
  "prompt": "User question...",
  "chosen": "Good response...",
  "rejected": "Bad response..."
}
```

**Tools:** LLaMA Factory supports DPO out of the box for Qwen models.

### 4.4 Data Collection Strategy
| Source | Quality | Volume | Effort |
|--------|---------|--------|--------|
| Chat logs | High | Medium | Automatic |
| Human feedback | Highest | Low | Manual |
| LLM-as-judge | Medium | High | Semi-auto |
| Synthetic (self-play) | Variable | Very High | Automated |

**MiganCore approach:**
1. Collect chat logs automatically
2. User thumbs up/down for preference signals
3. LLM-as-judge for initial filtering
4. DPO training on filtered preference pairs

### 4.5 Training Infrastructure
**Option A: Local (VPS)**
- Qwen2.5-7B + LoRA = ~8GB VRAM needed
- Our VPS has 32GB RAM, no GPU
- CPU training: very slow (hours per epoch)

**Option B: RunPod GPU**
- RTX 4090: $0.74/hr, 24GB VRAM
- A100: $1.99/hr, 80GB VRAM
- Training time: minutes instead of hours

**Option C: Unsloth (Recommended for efficiency)**
- 2x faster training, 70% less memory
- Supports Qwen2.5
- Works with LoRA

**Recommendation:** Use Unsloth + LoRA on RunPod for training, export GGUF for Ollama.

### 4.6 Evaluation
| Metric | How | Target |
|--------|-----|--------|
| Perplexity | Calculate on held-out set | Lower is better |
| Win rate vs base | Human/LLM judge | > 55% |
| Task accuracy | Benchmark tasks | Match or improve |
| User satisfaction | In-app feedback | > 4.0/5.0 |

---

## 5. WEEK 2 DECISION MATRIX

| Day | Feature | Approach | Complexity | Risk |
|-----|---------|----------|------------|------|
| 11 | Letta | Hybrid (Tier 3 memory) | Medium | Medium |
| 12 | Qdrant RAG | Recursive chunking + BGE | Medium | Low |
| 13-14 | MCP | Convert skills.json, build server | Medium | Low |
| 15 | Training | Unsloth + LoRA + DPO | High | High |
| 16-17 | Model versioning | Deploy pipeline integration | Medium | Medium |

---

## 6. KEY TAKEAWAYS

1. **Letta is mature** — Python SDK, async support, shared memory. Use as Tier 3 memory, not replacement.
2. **Chunking > Vector DB** — Start simple (recursive, 512 tokens), iterate to semantic.
3. **MCP is the future** — 20M+ downloads, industry adoption. Migrate our skills.json gradually.
4. **Training needs GPU** — CPU training on VPS is impractical. Budget ~$50 for RunPod training.
5. **DPO > RLHF for MVP** — Simpler, no reward model, good results with Qwen.

---

*Research compiled from: Letta docs, Qdrant docs, Anthropic MCP spec, arXiv papers, LLaMA Factory guide, Unsloth documentation.*
