# MIGANCORE — AGENT_PROMPTS.md
**Prompt Templates for Multi-Agent Research & Development**

**Purpose:** Give Claude Code and GPT-5.5 specific, actionable research prompts so they don't waste time on things we've already solved. Each prompt includes context, constraints, and expected deliverables.

**Last Updated:** 2026-05-03

---

## PROMPT A — For Claude Code (Implementation Focus)

### A1. Letta Integration Architecture

```
You are a senior backend engineer working on MiganCore, an Autonomous Digital Organism platform.

CONTEXT:
- We have a FastAPI app with LangGraph director for agent orchestration
- Current memory: Redis K-V (Tier 1), no semantic search yet
- Letta container exists in docker-compose.yml (profile: memory) but disabled
- We need Letta as Tier 3 memory: structured blocks (persona, human, world_state)
- Our agent table has a `letta_agent_id` column ready
- Letta runs at http://letta:8283 in Docker network

RESEARCH TASK:
1. Study the Letta Python SDK (letta-client) async API
2. Design the integration pattern:
   - When a MiganCore agent is created, also create a Letta agent
   - Map SOUL.md → Letta persona block
   - Map user profile → Letta human block
   - Map Redis memories → Letta world_state block
3. Design the sync protocol:
   - How do we keep MiganCore agent state ↔ Letta agent state in sync?
   - What happens when user edits persona in our UI?
   - What happens when Letta updates its own memory blocks?
4. Error handling:
   - Letta container not running → graceful degradation
   - Letta API rate limits → backoff strategy
   - Memory block size limits → chunking strategy

DELIVERABLES:
- Architecture diagram (text or ASCII)
- Sequence diagram: MiganCore agent creation → Letta agent creation
- Code skeleton for `services/letta_bridge.py`
- List of 5 biggest integration risks with mitigations
- Decision: Should we use Letta's built-in tool calling or keep our LangGraph director?

CONSTRAINTS:
- Must work with Ollama (local LLM), not OpenAI
- Must be async (FastAPI + asyncio)
- Must not break existing chat endpoints
- Budget: minimal compute overhead
```

### A2. Qdrant RAG Pipeline Implementation

```
You are a senior backend engineer working on MiganCore.

CONTEXT:
- We have Qdrant running at http://qdrant:6333
- We have pgvector in Postgres but only used for schema, not embeddings yet
- Current memory: Redis K-V (strings only)
- We need semantic memory for long-term recall across conversations
- Model: qwen2.5:7b-instruct-q4_K_M on Ollama (CPU inference)

RESEARCH TASK:
1. Design the full RAG pipeline:
   a. Chunking strategy for conversation history
   b. Embedding model selection (local, fast, Bahasa Indonesia support)
   c. Storage in Qdrant (collections per tenant? per agent?)
   d. Retrieval at query time
   e. Injection into system prompt
2. Compare embedding models:
   - all-MiniLM-L6-v2 (22MB, fast, English-only)
   - paraphrase-multilingual-MiniLM-L12-v2 (118MB, multilingual)
   - BGE-small-en-v1.5 (33MB, English, better quality)
   - bge-m3 (567MB, multilingual, SOTA)
   - Which is best for Bahasa Indonesia + English mixed content?
3. Design chunking for conversations:
   - User messages are short (1-2 sentences)
   - Assistant messages can be long (paragraphs)
   - How to chunk without losing context?
4. Design the query flow:
   - User asks: "What did we discuss about AI last week?"
   - System: embed query → search Qdrant → get top 5 chunks → inject into prompt
   - How to combine with Redis recent memory?

DELIVERABLES:
- Code skeleton for `services/rag.py` with:
  - `chunk_conversation(messages) -> list[Chunk]`
  - `embed_chunks(chunks) -> list[Embedding]`
  - `store_chunks(tenant_id, agent_id, chunks)`
  - `search_memory(tenant_id, agent_id, query, k=5) -> list[Chunk]`
- Embedding model recommendation with justification
- Qdrant schema design (collection structure, payload fields)
- Performance estimate: chunking 1000 messages, embedding, storage time

CONSTRAINTS:
- No GPU on VPS (CPU only for embeddings)
- Must be async
- Must respect tenant isolation
- Max 200ms for retrieval (blocking chat response)
```

### A3. MCP Server Implementation

```
You are a senior backend engineer working on MiganCore.

CONTEXT:
- We have 7 tools in skills.json (web_search, python_repl, memory_write, etc.)
- Our tools use a custom registry pattern in `services/tool_executor.py`
- We want to expose our tools via MCP (Model Context Protocol)
- MCP uses JSON-RPC 2.0 over stdio or HTTP SSE
- We want external MCP servers to also be usable by our agents

RESEARCH TASK:
1. Study MCP Python SDK (`mcp` package from Anthropic)
2. Design dual-mode architecture:
   a. MCP Server mode: expose MiganCore tools to external clients
   b. MCP Client mode: consume external MCP servers in our agents
3. Implement MCP server wrapping our ToolExecutor:
   - Map skill_id → MCP tool name
   - Map skills.json schema → MCP inputSchema
   - Handle JSON-RPC requests: initialize, tools/list, tools/call
4. Implement MCP client:
   - Connect to external MCP servers (stdio or HTTP)
   - Discover tools dynamically
   - Convert MCP tool calls to our ToolExecutor format
5. Security:
   - Tool approval gates (which tools can auto-run vs need approval)
   - Sandboxing for external MCP tools
   - Prevent tool name collisions

DELIVERABLES:
- Code skeleton for `services/mcp_server.py` (MCP server wrapping ToolExecutor)
- Code skeleton for `services/mcp_client.py` (MCP client consuming external servers)
- Update to `services/tool_executor.py` to support both native and MCP tools
- Decision matrix: which of our 7 tools should be native vs MCP?
- Security checklist for MCP integration

CONSTRAINTS:
- Must work with our existing LangGraph director
- Must not break existing tool calling
- Must support both stdio (local) and HTTP SSE (remote) transports
- Async throughout
```

### A4. Training Pipeline with Unsloth

```
You are an ML engineer working on MiganCore.

CONTEXT:
- Model: qwen2.5:7b-instruct-q4_K_M (4-bit quantized, ~4.7GB)
- We collect chat logs + user feedback (thumbs up/down)
- We need a training pipeline: SFT → DPO
- No GPU on VPS (32GB RAM, CPU only)
- Budget: ~$50 for cloud GPU training

RESEARCH TASK:
1. Study Unsloth framework:
   - Installation: `pip install unsloth`
   - Qwen2.5 support status
   - LoRA configuration (rank, alpha, target_modules)
   - 4-bit quantization compatibility
2. Design training pipeline:
   a. Data collection: extract preference pairs from chat logs
   b. Data formatting: JSON structure for SFT and DPO
   c. Training config: learning rate, epochs, batch size for 7B model
   d. Export: merge LoRA → GGUF for Ollama
3. Design evaluation:
   - How to evaluate model quality without human annotators?
   - LLM-as-judge pattern (GPT-4o or local judge model)
   - Metrics: win rate vs base model, perplexity, task accuracy
4. Design deployment:
   - Trigger: manual or automatic when N preference pairs collected?
   - A/B testing: route 10% traffic to new model
   - Rollback: revert to previous model if quality drops
5. Cost modeling:
   - RunPod RTX 4090 ($0.74/hr): training time estimate
   - RunPod A100 ($1.99/hr): training time estimate
   - Local CPU (VPS): training time estimate (warning: will be days)

DELIVERABLES:
- Training script skeleton using Unsloth
- Data preprocessing script: chat logs → DPO format
- Training config YAML with hyperparameters
- Evaluation script: LLM-as-judge comparison
- Deployment script: export GGUF + update Ollama
- Cost estimate table for different scenarios
- Risk analysis: what if training makes model worse?

CONSTRAINTS:
- Must support Qwen2.5-7B-Instruct
- Must output GGUF for Ollama compatibility
- Must work with limited data (startup, not enterprise volume)
- Must have rollback capability
- Training data must be filtered for PII/toxic content
```

---

## PROMPT B — For GPT-5.5 (Strategic Research Focus)

### B1. Strategic Technology Evaluation

```
You are a CTO-level technology strategist advising MiganCore, an early-stage AI startup building autonomous digital organisms.

CONTEXT:
- Current stack: FastAPI, Postgres+pgvector, Redis, Qdrant, Ollama (Qwen2.5-7B)
- Current features: auth, agents, chat, tool calling, memory, spawning
- Next 30 days: Letta, RAG, MCP, training pipeline, model versioning
- Resources: 1 VPS (32GB RAM, CPU), $50/month cloud GPU budget
- Team: solo founder + AI agents (you, Claude, Kimi)

RESEARCH TASK:
1. Evaluate technology choices for Week 2:
   a. Letta vs custom memory implementation — which gives better ROI?
   b. Qdrant vs pgvector for embeddings — performance vs complexity
   c. MCP adoption timeline — should we be early adopter or wait?
   d. Unsloth vs LLaMA Factory vs raw PyTorch — which for our scale?
2. Competitive landscape:
   a. What are other agent frameworks doing? (AutoGPT, CrewAI, LangChain)
   b. What differentiates MiganCore? (genealogy, SOUL.md, spawning)
   c. What features are table stakes vs differentiators?
3. Risk assessment:
   a. Technical risks: model drift, training instability, data scarcity
   b. Business risks: running out of budget, feature bloat, user retention
   c. Security risks: model poisoning, prompt injection, data leakage
4. Build vs buy analysis:
   a. Which components should we build ourselves?
   b. Which should we integrate (Letta, Composio, etc.)?
   c. Which should we defer until product-market fit?

DELIVERABLES:
- Technology recommendation matrix with scores (1-10) for each option
- Risk register: top 10 risks with probability and impact
- Build vs buy decision tree
- Suggested feature priority for next 30 days (ranked)
- 1-page strategic memo for a hypothetical investor

CONSTRAINTS:
- Be honest about limitations — don't oversell AI capabilities
- Consider budget constraints seriously
- Factor in maintenance burden (we're a small team)
- Prioritize user-visible features over infrastructure polish
```

### B2. Security Deep Dive

```
You are a security researcher auditing MiganCore's architecture.

CONTEXT:
- Multi-tenant SaaS with PostgreSQL RLS
- Agents can execute Python code via subprocess
- Agents can spawn child agents with inherited personas
- Tool calling includes web search and memory write
- Users can create unlimited agents (no enforcement yet)
- MCP integration will allow external tool servers

RESEARCH TASK:
1. Threat model:
   a. Create STRIDE threat model for our system
   b. Identify attack surfaces: auth, agents, tools, memory, spawning
   c. Map threats to our specific features
2. Agent-specific security:
   a. What if a spawned agent escapes its parent's constraints?
   b. What if an agent modifies its own SOUL.md to remove safety guidelines?
   c. What if agent A spawns agent B which spawns agent C... infinite chain?
3. Tool execution security:
   a. subprocess sandbox escape vectors (beyond what we have)
   b. Web search SSRF risks
   c. Memory poisoning: one agent corrupting another's memory
4. MCP security:
   a. Tool squatting attacks
   b. Malicious MCP servers
   c. Privilege escalation via tool composition
5. Data security:
   a. PII in chat logs → training data leakage
   b. Cross-tenant data leakage via embeddings
   c. Model memorization of sensitive data

DELIVERABLES:
- Threat model diagram (text-based)
- Top 15 security findings ranked by severity
- Mitigation recommendations for each finding
- Security testing checklist for Week 2 features
- Incident response playbook template (what if breach happens?)

CONSTRAINTS:
- Be paranoid but practical — not every risk needs immediate fix
- Prioritize findings that could cause data loss or system compromise
- Consider that we're an early-stage startup, not a bank
- Suggest defense-in-depth, not silver bullets
```

### B3. Cost & Scaling Analysis

```
You are a cloud infrastructure analyst advising MiganCore.

CONTEXT:
- Current: 1 VPS ($40/month), 32GB RAM, CPU-only inference
- Ollama runs qwen2.5:7b at 7-14 tok/s on CPU
- 5 Docker containers: API, Postgres, Redis, Qdrant, Ollama
- Next: Letta (memory), training (GPU), possibly more models
- Budget: $50/month for cloud GPU, total infra budget ~$100/month

RESEARCH TASK:
1. Current cost optimization:
   a. Is our VPS properly sized? (32GB for current load)
   b. Can we reduce Ollama memory footprint?
   c. Should we use model quantization more aggressively?
2. Scaling scenarios:
   a. 10 active users → resource needs?
   b. 100 active users → when do we need GPU?
   c. 1000 active users → architecture changes needed?
3. Training cost modeling:
   a. RunPod vs Vast.ai vs Lambda Labs pricing comparison
   b. Training 7B model with LoRA: time + cost for 1 epoch
   c. Continuous training (weekly retraining): monthly cost
4. Letta cost impact:
   a. Letta container resource requirements
   b. Embedding model memory footprint
   c. Database growth with memory blocks
5. Revenue modeling:
   a. At what user count does $100/month infra pay for itself?
   b. Freemium model: free tier limits vs paid tier value
   c. Cost per active user at different scales

DELIVERABLES:
- Spreadsheet-style cost model (text table)
- Break-even analysis: users vs revenue vs infra cost
- Scaling roadmap: what to upgrade at each milestone
- Infrastructure recommendation for next 6 months
- Warning signs: metrics that indicate we need to scale NOW

CONSTRAINTS:
- Realistic pricing (use actual RunPod/Vast.ai prices)
- Don't assume viral growth — model conservative scenarios
- Consider that training is optional, not continuous
- Factor in data storage costs (chat logs grow forever)
```

### B4. User Experience & Product Strategy

```
You are a product strategist advising MiganCore.

CONTEXT:
- Current product: API-only (backend), no frontend yet
- Features: agents, chat, memory, tool calling, spawning
- Target users: developers, power users, eventually enterprises
- Differentiators: agent genealogy, SOUL.md, autonomous spawning

RESEARCH TASK:
1. User journey mapping:
   a. Day 0: User discovers MiganCore → first action?
   b. Day 1: User creates first agent → what should happen?
   c. Day 7: User has 3 agents → what features do they need?
   d. Day 30: Power user → what advanced features?
2. Feature prioritization:
   a. Must-have for public beta (launch threshold)
   b. Nice-to-have for v1.0
   c. Defer to v2.0
   d. What should we cut from current roadmap?
3. Competitive positioning:
   a. Compare to: OpenAI Assistants, Claude Projects, Poe, Character.AI
   b. What can we do that they can't? (genealogy, spawning)
   c. What's our unfair advantage?
4. Go-to-market:
   a. Who is our ideal first 100 users?
   b. What distribution channels? (Hacker News, Reddit, Twitter)
   c. What demo/showcase would go viral?
5. Metrics:
   a. What should we track from day 1?
   b. North Star metric for an agent platform?
   c. Leading indicators of product-market fit?

DELIVERABLES:
- User journey map (text-based flow)
- Feature priority matrix (MoSCoW: Must, Should, Could, Won't)
- Competitive differentiation 2x2 matrix
- Launch readiness checklist
- Recommended metrics dashboard

CONSTRAINTS:
- We're pre-revenue, pre-launch
- No dedicated frontend team yet
- API-first approach is correct for now
- Don't suggest features that require massive infrastructure
```

---

## HOW TO USE THESE PROMPTS

### For Claude Code:
1. Copy the relevant prompt (A1-A4)
2. Paste into Claude Code with `--prompt` flag or inline
3. Specify which deliverable to prioritize if time-constrained
4. Review code skeletons carefully — they are starting points, not production code

### For GPT-5.5:
1. Copy the relevant prompt (B1-B4)
2. Use GPT-5.5's deep research mode if available
3. Ask follow-up questions for clarification
4. Synthesize findings into actionable recommendations

### Cross-Agent Workflow:
```
GPT-5.5 (strategy) → "Should we use Letta?"
    ↓
Claude Code (implementation) → "How to integrate Letta?"
    ↓
Kimi Code (deployment) → "Deploy Letta to VPS"
    ↓
GPT-5.5 (evaluation) → "Did the integration work?"
```

---

*Prompts designed for MiganCore Week 2 — adjust constraints as project evolves*
