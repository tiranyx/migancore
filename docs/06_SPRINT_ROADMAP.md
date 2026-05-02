# SPRINT ROADMAP — 30-Day ADO Build
**Version:** 1.0
**Start Date:** 2026-05-02
**Owner:** Tiranyx

---

## SPRINT OVERVIEW

```
Week 1: THE SEED        — VPS → Ollama → First Token → API Live
Week 2: THE DIRECTOR    — LangGraph + Memory + Tools + Multi-tenancy
Week 3: THE INNOVATOR   — Self-learning loop + Specialist agents wired
Week 4: THE BREEDER     — First clone + Training cycle + Demo
```

---

## WEEK 1: "THE SEED" (Day 1–7)
**Goal:** Dari VPS kosong → Mighan-Core bisa diajak ngobrol via API

### Day 1 — Infrastructure Foundation
**Owner Agent:** DevOps Agent
```
□ VPS provisioning & SSH hardening
  - UFW: allow 22/tcp, 80/tcp, 443/tcp only
  - fail2ban install
  - swap file 8GB: fallocate -l 8G /swapfile && mkswap /swapfile && swapon /swapfile
  - Add to /etc/fstab: /swapfile none swap sw 0 0
□ Docker + Docker Compose v2 install
□ git clone repo to /opt/ado
□ .env file created from .env.example
□ Generate JWT RS256 keypair:
  openssl genrsa -out /etc/ado/keys/private.pem 2048
  openssl rsa -in /etc/ado/keys/private.pem -pubout -out /etc/ado/keys/public.pem
```
**Done Criteria:** SSH works, Docker hello-world runs, swap active

### Day 2 — DNS + Reverse Proxy
**Owner Agent:** DevOps Agent
```
□ DNS A records:
  - api.mighan.com → VPS IP
  - app.mighan.com → VPS IP
  - lab.sidixlab.com → VPS IP
  - tiranyx.com → VPS IP
□ Caddy container up + TLS verified
□ Health check endpoint: GET /health → 200 OK
```
**Done Criteria:** curl https://api.mighan.com/health returns 200

### Day 3 — Ollama + First Token
**Owner Agent:** DevOps Agent + Backend Agent
```
□ Ollama container up
□ Pull models:
  ollama pull qwen2.5:7b-instruct-q4_K_M
  ollama pull qwen2.5:0.5b (draft model for speculative decoding)
□ Benchmark: tokens/sec test
  time curl -X POST http://localhost:11434/api/generate \
    -d '{"model":"qwen2.5:7b-instruct-q4_K_M","prompt":"Hello world","stream":false}'
□ Document baseline: ___ tokens/sec at ___ RAM usage
```
**Done Criteria:** ≥7 tokens/sec, response coherent

### Day 4 — Database + Basic API
**Owner Agent:** Backend Agent
```
□ Postgres + pgvector container up
□ Run migrations (init.sql)
□ Qdrant container up
□ Redis container up
□ FastAPI hello-world:
  POST /v1/chat → calls Ollama → returns response
□ Basic auth: POST /v1/auth/register, POST /v1/auth/login
□ JWT middleware: verify token on protected routes
```
**Done Criteria:** Can register, login, get JWT, call chat endpoint authenticated

### Day 5 — Function Calling Test
**Owner Agent:** Backend Agent
```
□ Implement tool registry (db-backed)
□ Implement 3 tools: web_search, python_repl, read_file
□ Test Hermes-style function calling with Qwen2.5-7B
□ Acceptance: model correctly calls web_search when asked "apa berita terbaru hari ini?"
□ Log tool call success/failure to Postgres
```
**Done Criteria:** 3/3 tools callable with ≥80% correct invocation on 10 test prompts

### Day 6 — SOUL.md Integration
**Owner Agent:** Backend Agent
```
□ SOUL.md loaded as system prompt for all conversations
□ Identity consistency test: run 5 fingerprint prompts, log baseline responses
□ Persona stays consistent across 10-turn conversation test
□ Store fingerprint baseline in model_versions.evaluation_scores
```
**Done Criteria:** Agent answers as Mighan-Core, not generic assistant

### Day 7 — CI/CD + Week 1 Review
**Owner Agent:** DevOps Agent
```
□ GitHub Actions workflow: test → build → deploy on push to main
□ Watchtower or SSH+compose pull for auto-deploy
□ Health monitoring: UptimeRobot free tier monitoring api.mighan.com/health
□ Daily backup script: pg_dump → gzip → Backblaze B2 (or local)
□ FOUNDER JOURNAL Entry #007: Week 1 retrospective
```
**Done Criteria:** Push to main triggers deploy, health monitored, backup runs

---

## WEEK 2: "THE DIRECTOR" (Day 8–14)
**Goal:** Core Brain punya memory, bisa orkestrasi multi-step task

### Day 8 — Full Docker Stack
**Owner Agent:** DevOps Agent
```
□ All services up: Ollama, Postgres, Qdrant, Redis, Letta, API, Workers, Langfuse, Caddy
□ Memory usage baseline: document each service RAM usage
□ Verify: no service hitting memory limit
□ Langfuse accessible at lab.sidixlab.com
```

### Day 9 — Multi-tenant Foundation
**Owner Agent:** Backend Agent
```
□ Tenant creation endpoint + user scoping
□ JWT includes tenant_id
□ Postgres middleware: SET app.current_tenant = :tenant_id before queries
□ RLS policies active and tested:
  - User from Tenant A cannot read Tenant B's agents
□ Integration test suite for RLS
```

### Day 10 — LangGraph Director MVP
**Owner Agent:** Backend Agent + Core Agent
```
□ LangGraph StateGraph with 6 nodes:
  intent_classifier → planner → memory_reader → reasoner → tool_executor → response_synthesizer
□ Circuit breaker: max_iterations=10
□ Streaming response via SSE
□ Task ledger visible in response metadata
```

### Day 11 — Letta Memory Integration
**Owner Agent:** Core Agent
```
□ Letta server running, connected to Postgres
□ Core Brain agent created in Letta with SOUL.md as persona block
□ Memory read/write via tools: memory_write, memory_search
□ Sleep-time compute: background consolidation script (cron every 2 hours)
□ Test: agent recalls fact from session 5+ messages ago
```

### Day 12 — Qdrant + Embeddings
**Owner Agent:** Core Agent
```
□ BGE-M3 embedding service (fastembed CPU) running as utility
□ Qdrant collections created: semantic_{agent_id}, episodic_{agent_id}
□ Auto-embed and index all messages asynchronously
□ memory_search tool queries Qdrant for semantic similarity
□ Test: "remember that my company is called X" → searchable 10 messages later
```

### Day 13 — Celery Workers + Specialist Stubs
**Owner Agent:** Backend Agent
```
□ Celery workers: code, web, research queues
□ Worker health endpoints in Langfuse
□ Stub implementations for 3 specialists:
  CodeSpecialist: executes Python in sandbox
  WebSpecialist: Playwright browser automation
  ResearchSpecialist: ArXiv API query
□ LangGraph routes task to appropriate specialist queue
```

### Day 14 — Week 2 Integration Test
**Owner Agent:** QA Agent
```
□ End-to-end test: 
  "Research the latest paper on self-improving agents, summarize key findings, 
   then write a Python script that implements the core loop"
  → should invoke ResearchSpecialist + CodeSpecialist
□ Memory persists across session boundary
□ All logs in Langfuse with traces
□ FOUNDER JOURNAL Entry #014: Week 2 retrospective + metrics
```

---

## WEEK 3: "THE INNOVATOR" (Day 15–21)
**Goal:** Self-learning pipeline wired, Constitution active, full multi-agent running

### Day 15 — Constitution.md + CAI Loop
**Owner Agent:** Core Agent
```
□ Write Constitution.md (12 principles, see SOUL.md Section VI)
□ Implement critique-revise tool:
  For each assistant message → auto-critique vs principles
  If violation → revise → store (original, revised) as preference pair
□ Preference pair table being populated
```

### Day 16 — LLM-as-Judge Pipeline
**Owner Agent:** Training Agent
```
□ Judge implementation using local Hermes-3-8B or Qwen2.5-7B itself
□ Batch judge: score 100 historical messages vs Constitution
□ Output: preference_pairs table with 100+ entries, judge_score > 0.7
□ Validate judge quality: human spot-check 20 pairs
```

### Day 17 — Feedback Aggregator
**Owner Agent:** Training Agent
```
□ Celery beat: hourly feedback aggregation job
□ Implicit signals: track retry count, conversation length, follow-up frequency
□ Redis Streams: feedback.events populated in real-time
□ Dashboard in Langfuse: feedback trends over time
```

### Day 18 — Training Pipeline Scaffold
**Owner Agent:** Training Agent
```
□ RunPod API integration: trigger pod → wait → download artifacts
□ Unsloth + TRL SimPOTrainer script ready in /training/train_simpo.py
□ Auto-eval harness: 20 held-out prompts + persona consistency test
□ MLflow logging: all training runs tracked
□ Dry run: trigger fake training job, verify pipeline works end-to-end
```

### Day 19 — Specialist Agents Full Implementation
**Owner Agent:** Backend Agent
```
□ CodeSpecialist: full E2B or Docker sandbox code execution
□ WebSpecialist: Playwright + JS console capture
□ ResearchSpecialist: ArXiv API + Tavily + KG ingestion
□ AudioSpecialist: Coqui XTTS TTS stub (CPU, ~15s for 200 chars)
□ All specialists publish results back to Redis Streams
```

### Day 20 — A/B Framework
**Owner Agent:** Backend Agent
```
□ Model version header: X-Model-Version in responses
□ Traffic splitter: Caddy routes 10% requests to candidate model
□ Metrics comparison dashboard in Langfuse
□ Auto-promote logic: if new_model_score > baseline + 0.02 for 24h → promote
```

### Day 21 — Week 3 Integration Test
**Owner Agent:** QA Agent
```
□ End-to-end self-improvement cycle simulation:
  Generate 50 conversations → extract feedback → judge → 50 preference pairs
  Verify training pipeline triggers correctly
□ Constitution violations detected and logged
□ FOUNDER JOURNAL Entry #021: Week 3 retrospective + first model quality metrics
```

---

## WEEK 4: "THE BREEDER" (Day 22–30)
**Goal:** First real training cycle + first child agent spawned + demo ready

### Day 22 — Magpie Data Generation
**Owner Agent:** Training Agent
```
□ Magpie pipeline running on VPS overnight (Qwen2.5-7B-Instruct as base)
□ Target: 20K instruction-response pairs
□ Quality filter: keep top 50% by diversity score + judge
□ Push to HuggingFace Hub: mighan/magpie-soul-v1
```

### Day 23 — RunPod First Real Training Run
**Owner Agent:** Training Agent
```
□ Trigger RunPod job: Unsloth + QLoRA + SFT, Qwen2.5-7B, 10K samples, 3 epochs
□ Estimated: 6–8 hours, ~$3–5, RTX 4090
□ Monitor: training loss, eval loss via Weights & Biases or MLflow
□ Download GGUF Q4_K_M on completion
```

### Day 24 — Model v0.2 Deployment
**Owner Agent:** Training Agent + DevOps Agent
```
□ Pull GGUF to VPS
□ Identity consistency test: 5 fingerprint prompts
□ If pass: hot-swap in Ollama (ollama create mighan-v02 -f Modelfile)
□ A/B: 10% traffic to v0.2, 90% to v0.1
□ Log all metrics to MLflow
```

### Day 25 — SimPO Preference Training
**Owner Agent:** Training Agent
```
□ Collect 500+ preference pairs from Weeks 2–3
□ Second RunPod job: SimPO fine-tune on preferences
□ Estimated: 4–6 hours, ~$2–3
□ Model v0.3 candidate
```

### Day 26 — Agent Spawn Endpoint
**Owner Agent:** Backend Agent
```
□ POST /v1/agents/spawn fully implemented
□ Letta agent creation with custom persona
□ Genealogy tree visible in Postgres
□ Test: spawn "Aria" — customer success agent for demo client
□ Verify: Aria answers in her persona (warm, patient) not Core Brain's
```

### Day 27 — Sidixlab Research Pipeline
**Owner Agent:** Research Agent
```
□ Daily ArXiv cron (04:00 WIB): fetch cs.AI + cs.LG papers
□ PDF download + Marker parsing
□ Auto-summarize with Qwen2.5-7B
□ Entity extraction → KG
□ Experiment hypothesis auto-generated from top-3 insights
□ Verify: 5+ papers ingested overnight
```

### Day 28 — Full System Test
**Owner Agent:** QA Agent
```
□ FULL end-to-end:
  1. Register new tenant "Demo Co"
  2. Spawn agent "Aria" with customer_success template
  3. Have 10-turn conversation with Aria
  4. Verify Aria's memory persists
  5. Aria spawns a "research helper" sub-agent
  6. Self-improvement cycle triggered manually
□ All traces visible in Langfuse
□ All metrics logged
```

### Day 29 — Documentation & Public Assets
**Owner Agent:** Docs Agent
```
□ README.md polished
□ API documentation (FastAPI auto-docs at /docs)
□ Demo video recorded (Loom, 5 minutes)
□ tiranyx.com landing page live
□ GitHub repo public (with appropriate LICENSE)
```

### Day 30 — Demo + Retrospective
**Owner Agent:** Project Owner (Human)
```
□ Demo recording published
□ FOUNDER JOURNAL Entry #030: Full retrospective
□ Sprint 2 planning: Month 2 goals
□ Budget reconciliation: actual RunPod spend vs planned
□ Update all documentation with lessons learned
□ Celebrate 🎉
```

---

## MILESTONE TRACKING

| Milestone | Target Day | Status |
|---|---|---|
| First token from Ollama | Day 3 | ⬜ Pending |
| Authenticated chat API live | Day 5 | ⬜ Pending |
| Memory persists across sessions | Day 11 | ⬜ Pending |
| Multi-step task completed by specialists | Day 14 | ⬜ Pending |
| First preference pairs generated | Day 16 | ⬜ Pending |
| Training pipeline verified E2E | Day 18 | ⬜ Pending |
| First real training run (RunPod) | Day 23 | ⬜ Pending |
| First child agent spawned | Day 26 | ⬜ Pending |
| Self-improvement cycle proven | Day 28 | ⬜ Pending |
| Public demo | Day 30 | ⬜ Pending |
