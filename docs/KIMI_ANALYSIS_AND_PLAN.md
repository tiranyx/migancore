# Kimi Analysis & Implementation Plan
> **Date:** 2026-05-03
> **Status:** Post-research, ready for execution
> **Sources:** GPT-5.5 Codex Synthesis + SIDIX Archive Research + Internal Research

---

## 1. Executive Summary

After analyzing GPT-5.5's synthesis and deep-diving into the SIDIX codebase, the convergence is striking:

**SIDIX already built most of what MiganCore aspires to be.** The 7 Pilar Kemandirian (Nafs, Aql, Qalb, Ruh, Hayat, Ilm, Hikmah) map almost 1:1 to MiganCore's ADO vision. The difference is architectural maturity:

| Dimension | SIDIX | MiganCore (Target) |
|-----------|-------|-------------------|
| Scope | Single-tenant Islamic epistemology | Multi-tenant digital organism factory |
| Orchestration | Custom taskgraph (Raudah) | LangGraph Director (industry standard) |
| Memory | PostgreSQL + GraphRAG (Mizan) | Postgres + Letta + Qdrant (layered) |
| Training | RunPod DoRA (Sprint 13) | SimPO + QLoRA + gated evaluation |
| Auth | Simple/single-user | RS256 JWT + multi-tenant RLS |
| Persona | Hardcoded 5 personas (AYMAN, ABOO, etc.) | Dynamic, tenant-configurable |
| Deployment | Monolithic Python | Containerized, API-first, SaaS-ready |

**Key Insight:** SIDIX is the philosophical prototype. MiganCore is the engineering productization. We don't need to reinvent the self-healing/self-learning patterns — we need to **extract, generalize, and containerize** them.

---

## 2. SIDIX Patterns Worth Port-ing to MiganCore

### 2.1 Nafs — 3-Layer Knowledge Fusion (CRITICAL)

SIDIX's `NafsOrchestrator` has a beautiful, battle-tested pattern:

```
PARAMETRIC  60%  → LLM weights (general reasoning)
DYNAMIC     30%  → Knowledge Graph (runtime-learned)
STATIC      10%  → Frozen corpus (verified references)
```

**For MiganCore Director:**
- This becomes the **memory retrieval strategy** inside the `load_context` node
- Topic-based routing (regex → intent classification) is lightweight and CPU-friendly
- Weight matrix per topic is configurable per tenant

**Port decision:** ✅ Adapt directly. Replace regex with small-model classifier (Qwen 0.5B) for generality, keep weight matrix concept.

### 2.2 Topic Detection + Persona Routing

SIDIX uses regex patterns for topic detection and persona alias mapping. For MiganCore:

```python
# SIDIX pattern (hardcoded)
TOPIC_PATTERNS = {
    "sidix_internal": re.compile(r"\b(sidix|ihos|maqashid|...)\b"),
    "agama": re.compile(r"\b(quran|hadith|fiqh|...)\b"),
    ...
}

# MiganCore pattern (tenant-configurable, stored in DB)
# Each tenant defines their own topic → intent → specialist mapping
```

**Port decision:** ✅ Generalize. Store topic/specialist routing in Postgres per tenant. SIDIX's persona system becomes MiganCore's "agent configuration."

### 2.3 Self-Healing (Qalb / SyifaHealer)

SIDIX has a 4-level health system with auto-actions:

```
🟢 HEALTHY  → Normal operation
🟡 DEGRADED → Reduce batch size, switch to CPU fallback
🟠 SICK     → Restart Ollama, clear cache, switch to backup model
🔴 CRITICAL → Safe mode, full restart, alert admin
```

**For MiganCore:**
- Add health check endpoint (`/health` already exists, but needs real checks)
- Integrate with Celery beat for periodic health checks
- Auto-actions via Celery tasks (restart containers, clear Redis, etc.)
- Alert admin via webhook/email (future)

**Port decision:** ✅ Port concept. Implement as Celery periodic task + FastAPI health endpoint.

### 2.4 Self-Iteration (Hayat / CQF Scoring)

SIDIX's Hayat engine: Generate → Self-evaluate (CQF score) → Refine → Repeat (max 3 iterations, target score ≥ 8.0).

**For MiganCore:**
- This becomes a **Celery background task** for quality improvement
- Not blocking the user response path
- CQF score stored in `audit_events` table for trend analysis

**Port decision:** ⚠️ Adapt. Don't block user response with iteration. Use as background quality scoring + optional refinement for flagged responses.

### 2.5 TaskGraph (Raudah) — Topological Execution

SIDIX's Raudah taskgraph groups tasks into "waves" based on role:

```python
ROLE_WAVE = {
    "peneliti": 0,      # Wave 0: research first
    "analis": 1,        # Wave 1: analyze research
    "perekayasa": 1,    # Wave 1: engineering parallel with analysis
    "penulis": 2,       # Wave 2: write after analysis
    "verifikator": 3,   # Wave 3: verify last
}
```

**For MiganCore:**
- This pattern maps directly to LangGraph's parallel execution
- Specialists = nodes, waves = parallel branches in graph
- `asyncio.gather` per wave = LangGraph's fan-out/fan-in

**Port decision:** ✅ Direct inspiration for specialist node design.

### 2.6 Training Pipeline (RunPod DoRA)

SIDIX Sprint 13 has a working training pipeline:
- `runpod_train_lora.py`: SFTTrainer, DoRA/LoRA, HF upload, auto-terminate
- `runpod_pod_orchestrator.py`: Pod lifecycle management
- Dataset format: `{instruction, input, output, metadata}`

**For MiganCore:**
- Replace SFT with SimPO (preference optimization)
- Add evaluation gates before training
- Add "shadow evolution" deployment pattern
- Reuse RunPod orchestration pattern

**Port decision:** ✅ Port orchestration. Replace SFT with SimPO, add evaluation harness.

---

## 3. GPT-5.5 Recommendations vs SIDIX Reality

### Alignment (Both Say the Same Thing)

| GPT-5.5 Says | SIDIX Already Has | Confidence |
|-------------|-------------------|------------|
| "Director first, agents second" | Raudah taskgraph with deterministic waves | ✅ High |
| "Postgres is truth" | Mizan Repository (PostgreSQL + GraphRAG) | ✅ High |
| "Do not let agents modify their own graph" | Policy/capability registry separate from core | ✅ High |
| "Circuit breaker with budgets" | SyifaHealer health levels + auto-actions | ✅ High |
| "Shadow evolution for model promotion" | Not explicitly, but CQF scoring enables it | ⚠️ Medium |
| "Rule-based first for forbidden actions" | Maqashid filter system (IJTIHAD/ACADEMIC/CREATIVE) | ✅ High |

### Divergence (Where GPT-5.5 Goes Further)

| Area | GPT-5.5 | SIDIX | Decision |
|------|---------|-------|----------|
| Auth | RS256 JWT + multi-tenant RLS | Simple/single-user | 🆕 MiganCore must implement |
| Memory layers | Postgres + Letta + Qdrant | Postgres + GraphRAG | 🆕 Add Letta for living context |
| Training | SimPO + gated evaluation | SFT/DoRA weekly | 🆕 Add gates, switch to SimPO |
| Checkpointing | PostgresSaver for LangGraph | In-memory only | 🆕 Add persistence |
| Observability | Langfuse + structured tracing | Basic logging | 🆕 Add production tracing |

---

## 4. Red Flags from GPT-5.5 — Verified Against Codebase

| # | Issue | Status | Action |
|---|-------|--------|--------|
| 1 | `LETTA_URL` may be wrong port (8283 vs 8083) | ⚠️ Unverified | Check container logs before wiring |
| 2 | `api/requirements.txt` uses `bcrypt`, need Argon2id | ✅ Confirmed | Replace in Day 4 |
| 3 | RLS incomplete for tables without direct `tenant_id` | ✅ Confirmed | Add columns or join policies in Day 5 |
| 4 | Celery references `app.celery` but module doesn't exist | ✅ Confirmed | Create module in Day 6+ |
| 5 | `/ready` is stub — no real downstream checks | ✅ Confirmed | Implement in Day 4 |
| 6 | Self-signed SSL for auth endpoints | ⚠️ Risk | Add Let's Encrypt or warn users |
| 7 | `langgraph-checkpoint-postgres` not in requirements | ✅ Confirmed | Add in Day 6 |
| 8 | No `refresh_tokens` table | ✅ Confirmed | Add in Day 4 |
| 9 | No `audit_events` table | ✅ Confirmed | Add in Day 5 |
| 10 | Ollama `NUM_PARALLEL=1` but may need tuning | ⚠️ TBD | Benchmark after Day 4 |

---

## 5. Implementation Plan — Day 4-6 (Revised)

### Day 4: Auth Foundation + Readiness (High Confidence)

**Goal:** Secure the API before any agent endpoints exist.

```
├── api/
│   ├── deps/auth.py          ← JWT verification, get_current_user
│   ├── deps/tenant.py        ← SET LOCAL app.current_tenant helper
│   ├── services/jwt.py       ← RS256 sign/verify, token rotation
│   ├── services/password.py  ← Argon2id hashing
│   ├── routers/auth.py       ← /v1/auth/* endpoints
│   └── main.py               ← Wire auth router, real /ready
│
├── migrations/
│   ├── 004_add_refresh_tokens.sql
│   └── 005_add_audit_events_skeleton.sql
│
└── scripts/
    └── test_auth.sh          ← curl-based auth flow tests
```

**Endpoints:**
- `POST /v1/auth/register`
- `POST /v1/auth/login`
- `POST /v1/auth/refresh`
- `POST /v1/auth/logout`
- `GET /v1/auth/me`
- `GET /ready` (real checks: Postgres, Redis, Qdrant, Ollama)

**Tests (must pass before Day 5):**
1. Register → Login → Access token works
2. Wrong password → 401
3. Expired token → 401
4. Revoked `jti` → 401
5. Wrong `aud` → 401
6. `/ready` returns all-green when services up

---

### Day 5: RLS + Tenant Safety (High Confidence)

**Goal:** Ensure Tenant A can never read Tenant B data.

```
├── migrations/
│   ├── 006_add_tenant_id_to_messages.sql
│   ├── 007_add_tenant_id_to_memory_blocks.sql
│   ├── 008_add_tenant_id_to_archival_memory.sql
│   ├── 009_complete_rls_policies.sql
│   └── 010_add_audit_events.sql
│
├── api/
│   ├── deps/tenant.py        ← SQLAlchemy helper with SET LOCAL
│   ├── deps/db.py            ← Session with tenant context
│   └── tests/
│       └── test_rls.py       ← Cross-tenant injection tests
│
└── docs/
    └── RLS_TEST_RESULTS.md   ← Evidence of isolation
```

**RLS Policy Pattern:**
```sql
-- Every tenant-scoped table
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON messages
  USING (tenant_id = current_setting('app.current_tenant', true)::UUID);

-- Application helper (called per transaction)
SET LOCAL app.current_tenant = '<tenant_uuid>';
SET LOCAL app.current_user = '<user_uuid>';
```

**Tests:**
1. User A (tenant 1) creates record
2. User B (tenant 2) queries → empty result
3. Admin (no tenant) → full result (optional superuser policy)
4. Pooled connection resets tenant after transaction

---

### Day 6: Director Skeleton (Medium Confidence)

**Goal:** A working LangGraph Director with no expensive specialists yet.

```
├── api/core/
│   ├── director/
│   │   ├── __init__.py
│   │   ├── state.py          ← DirectorState TypedDict
│   │   ├── graph.py          ← StateGraph definition
│   │   ├── nodes/
│   │   │   ├── ingress.py    ← JWT validate, load context
│   │   │   ├── classify.py   ← Intent classification (rule-based first)
│   │   │   ├── plan.py       ← Simple plan generation
│   │   │   ├── risk_gate.py  ← Budget/circuit breaker check
│   │   │   ├── respond.py    ← Format response
│   │   │   └── persist.py    ← Save to Postgres
│   │   └── routers/
│   │       └── specialist_router.py  ← Route to specialist (stub)
│   │
│   └── memory/
│       ├── __init__.py
│       ├── service.py        ← Postgres-only memory interface
│       └── qdrant_client.py  ← Qdrant wrapper (stub for now)
│
├── api/routers/
│   └── agent.py              ← /v1/agent/ask endpoint
│
└── migrations/
    └── 011_add_conversations.sql
```

**Director Graph (Sprint 1):**
```
START → ingress_validate → load_context → classify_intent → risk_gate
                                                          ↓
                              ┌─────────────────────────────────────┐
                              ↓                                     ↓
                     confidence < 0.7                         confidence >= 0.7
                              ↓                                     ↓
                       clarify_node                         plan → respond
                              ↓                                     ↓
                              └─────────────────────────────────────┘
                                                                    ↓
                                                                 persist
                                                                    ↓
                                                                   END
```

**No specialists yet.** Just: classify → respond. The graph compiles and runs.

**Anti-pattern avoided:** No "agent modifies its own graph." Capabilities = versioned rows in Postgres.

---

## 6. SIDIX-Inspired Additions for Week 2

After Day 6, these SIDIX patterns should be ported:

### Week 2-1: Self-Healing (Qalb → MiganCore Health Service)
- Celery beat task: every 60s check system health
- Health levels: HEALTHY → DEGRADED → SICK → CRITICAL
- Auto-actions: reduce Ollama keepalive, clear Redis, restart containers
- FastAPI endpoint: `/health` returns health level + metrics

### Week 2-2: Quality Scoring (CQF → MiganCore Response Eval)
- Background Celery task: score every agent response
- Dimensions: helpfulness, accuracy, identity, safety
- Store scores in `audit_events` for trend analysis
- Trigger refinement if score < threshold

### Week 2-3: Memory Lifecycle (Aql → MiganCore Learning Loop)
- Background worker: extract facts from conversations
- Deduplication + conflict resolution
- Update Qdrant (semantic) + Letta blocks (living context)
- Queue preference pairs for training data

### Week 2-4: Training Pipeline (Takwin → MiganCore Evolution)
- Weekly data collection from `preference_pairs` table
- Evaluation gates before any training job
- RunPod orchestration (reuse SIDIX pattern)
- Shadow evolution: candidate model gets mirrored prompts

---

## 7. Memory Budget Revisited (with Director)

| Service | Idle | Loaded | Post-Day 6 |
|---------|------|--------|------------|
| Existing VPS | ~5GB | ~5GB | ~5GB |
| Postgres | 200MB | 500MB | 500MB |
| Redis | 50MB | 100MB | 200MB (queues) |
| Qdrant | 100MB | 200MB | 200MB |
| Letta | 200MB | 500MB | 500MB |
| FastAPI + Auth | 100MB | 200MB | 300MB |
| Celery Workers (x3) | 300MB | 600MB | 600MB |
| Ollama (qwen2.5:7b) | 0MB | 4.7GB | 4.7GB |
| LangGraph Runtime | — | — | 300MB |
| **Total MiganCore** | **~1GB** | **~7GB** | **~7.5GB** |
| **Grand Total** | **~6GB** | **~12GB** | **~12.5GB** |

**Verdict:** Still safe with 32GB RAM + 8GB swap. Director adds ~300MB overhead — negligible.

---

## 8. Competitive Positioning — Final

Based on GPT-5.5 analysis + SIDIX reality check:

> **MiganCore is not "LangGraph + Letta + Ollama in a box."**
>
> MiganCore is a **self-hosted digital organism platform** that:
> 1. Remembers everything (Postgres + Letta + Qdrant layers)
> 2. Thinks before acting (deterministic Director with circuit breaker)
> 3. Heals itself (health monitoring + auto-recovery)
> 4. Evolves under supervision (gated SimPO training, shadow deployment)
> 5. Runs on modest hardware (32GB VPS, CPU inference, burst GPU training)
> 6. Protects tenant data (RS256 JWT + RLS + audit trail)
>
> Competitors have pieces. MiganCore has the organism.

**Moat:** Not the code (copyable), but the **accumulated memory, evaluation harness, and cultural context** (Indonesian/local focus).

---

## 9. Final Recommendation

**Proceed with Day 4 immediately.** Auth is standard engineering with zero research risk. Every day we delay auth is a day agents grow without skin.

**Day 5 immediately after.** RLS is the safety boundary. Without it, multi-tenant = multi-disaster.

**Day 6 with caution.** Director skeleton only — no specialists, no Letta integration yet. Just a graph that compiles, classifies intent, and returns a response. Prove the state machine works before adding complexity.

**Week 2:** Port SIDIX patterns (self-healing, quality scoring, memory lifecycle) into the containerized, multi-tenant architecture.

---

*Ready for execution. Kimi, commence Day 4.*
