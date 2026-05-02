# Codex Research Synthesis for Kimi
**Date:** 2026-05-03
**Purpose:** Deep research and implementation guidance for MiganCore Day 4-14
**Audience:** Kimi Code CLI and future engineering agents
**Status:** Advisory, ready for implementation planning

---

## Executive Verdict

MiganCore should not become "another agent framework." The strongest path is a small, deterministic, self-hosted organism runtime:

1. **Director first, agents second.** Build one durable LangGraph Director that delegates to specialist nodes/subgraphs. Do not spawn independent autonomous agents until the state, budget, and safety model is proven.
2. **Postgres is truth; Letta is living context; Qdrant is recall.** Do not let Letta or Qdrant become security boundaries. Tenant isolation must be enforced in Postgres and application code first.
3. **Training should be a gated evolution lab, not weekly blind fine-tuning.** Collect data weekly, evaluate weekly, but only train when enough high-quality preference pairs exist.
4. **Auth/RLS is Day 4's real foundation.** Use RS256 JWT, Argon2id, short access tokens, refresh-token rotation, and `SET LOCAL app.current_tenant` per transaction.
5. **Positioning moat:** "self-hosted digital organism with memory, lineage, and supervised evolution" is more defensible than "multi-agent builder."

---

## Important Correction: Topic 4 Conflict

Kimi's message says Topic 4 is **FastAPI JWT Multi-Tenant**, but `docs/RESEARCH_BRIEF_FOR_GPT55.md` Topic 4 is **Competitive Differentiation Strategy**.

This synthesis covers both:
- Topic 4A: FastAPI JWT Multi-Tenant
- Topic 4B: Competitive Differentiation

---

## Topic 1: LangGraph Director Architecture

### Recommendation

Use LangGraph as a **deterministic workflow kernel**, not as a loose roleplay arena.

MiganCore should start with one Director graph:

```text
START
  -> ingress_validate
  -> load_context
  -> classify_intent
  -> plan
  -> risk_gate
  -> execute_specialists
  -> integrate_results
  -> critic_review
  -> persist_learning
  -> respond
  -> END
```

The Director should call specialists as **nodes or subgraphs** at first. Avoid long-running peer-to-peer agent chatter in Sprint 1 because it is expensive, hard to debug, and risky on CPU-only Ollama.

### State Model

Use a typed state with budgets and audit fields from day one:

```python
from typing import Annotated, Literal, Optional, TypedDict
import operator

class DirectorState(TypedDict):
    request_id: str
    thread_id: str
    tenant_id: str
    user_id: str
    agent_id: str
    user_query: str

    intent: Optional[Literal[
        "chat", "research", "code", "memory", "creative", "training", "admin"
    ]]
    risk_level: Literal["low", "medium", "high", "forbidden"]
    route_confidence: float

    memory_context: list[dict]
    plan: list[dict]
    specialist_results: Annotated[list[dict], operator.add]
    draft_response: Optional[str]
    critique: Optional[dict]

    iteration_count: int
    max_iterations: int
    ollama_calls: int
    max_ollama_calls: int
    tool_calls: Annotated[list[dict], operator.add]
    errors: Annotated[list[dict], operator.add]

    needs_human: bool
    final_response: Optional[str]
```

### Routing Strategy

Use a hybrid router:

1. **Rule-based first** for forbidden/admin/destructive actions.
2. **Small-model classifier** for intent routing when risk is low.
3. **7B reasoning** only when routing confidence is low or the task is complex.

This saves CPU and RAM. Qwen 7B should not classify trivial requests if Qwen 0.5B or rules can do it.

### Specialist Execution

Specialists should be boring Python interfaces first:

| Specialist | Sprint 1 Shape | Later Shape |
|---|---|---|
| Memory | Python service calling Postgres/Qdrant/Letta | Letta-aware subgraph |
| Research | Tool node with web/paper fetch | Dedicated research graph |
| Code | Restricted tool node | Sandbox worker |
| Creative | Prompt template + LLM node | Persona sub-agent |
| Training | Job planner only | RunPod orchestration graph |

### Circuit Breaker

Use strict budgets:

| Budget | Initial Value |
|---|---:|
| `max_iterations` | 6 |
| `max_ollama_calls` | 8 |
| max parallel Ollama calls | 1 now, 2 after benchmark |
| transient retry | 1 |
| tool timeout | 15s low-risk, 60s research, 300s background |

Failure flow:

```text
tool/agent fails
  -> classify error as transient/permanent/forbidden
  -> transient: retry once with narrower input
  -> permanent: skip or ask clarification
  -> forbidden: interrupt for human approval or refuse
  -> persist failure lesson
  -> return partial result when useful
```

### Human-in-the-Loop

Use LangGraph `interrupt()` only for:
- destructive file/system actions
- cost-bearing RunPod jobs
- cross-tenant operations
- production deploy/reload
- model promotion

Important: any side effects before `interrupt()` must be idempotent because LangGraph resumes by rerunning the node from the beginning.

### Persistence

Install and use `langgraph-checkpoint-postgres` for durable workflows. The current `api/requirements.txt` has `langgraph` but does not yet include the Postgres checkpointer package.

Recommended thread id:

```text
thread_id = "{tenant_id}:{agent_id}:{conversation_id}"
```

### Anti-Pattern To Avoid

Do not implement "the agent modifies its own graph" in Sprint 1. Implement **policy/capability versioning** instead:

```text
director graph code = stable
capabilities registry = dynamic
tool grants = dynamic
prompts/policies = versioned rows
```

That gives the organism evolution without letting it rewrite its nervous system on day one.

---

## Topic 2: Memory Architecture - Letta + Qdrant + Postgres

### Recommendation

Use a three-layer model:

```text
Postgres = source of truth, tenant isolation, lineage, audit, RLS
Letta    = always-visible living context blocks
Qdrant   = semantic recall and retrieval index
```

Never rely on Letta or Qdrant as the primary tenant boundary. They are memory engines, not the authorization source.

### What Goes Where

| Memory Type | Primary Store | Secondary Store | Notes |
|---|---|---|---|
| tenant/users/agents | Postgres | none | RLS enforced |
| conversation log | Postgres | Letta messages optional | Postgres remains canonical |
| persona/SOUL | Letta block + Postgres version | none | read-only for base SOUL |
| human preferences | Letta block | Postgres facts table | compact, always visible |
| episodic summaries | Postgres | Qdrant vector | searchable by time + meaning |
| semantic facts | Postgres | Qdrant vector | tenant-scoped |
| procedural lessons | Postgres | Qdrant vector + Letta block summary | used for self-improvement |
| preference pairs | Postgres | none | never put raw private data in shared vector payload |

### Letta Design

Create one Letta agent per MiganCore agent, not one global Letta agent for all tenants.

Recommended blocks:

```python
memory_blocks = [
    {
        "label": "persona",
        "value": rendered_soul_md,
        "limit": 5000,
        "read_only": True,
    },
    {
        "label": "human",
        "value": "Known preferences and stable user facts.",
        "limit": 3000,
    },
    {
        "label": "current_context",
        "value": "Current project, task, constraints.",
        "limit": 3000,
    },
    {
        "label": "procedural_lessons",
        "value": "Short lessons from prior successes/failures.",
        "limit": 3000,
    },
]
```

Do not put large documents in Letta blocks. Blocks are always in-context, so they spend tokens every turn.

### Qdrant Multi-Tenant Schema

Use one collection per embedding model, not one collection per tenant:

```text
collection: memories_bge_m3_1024
vector_size: 1024
distance: Cosine
payload:
  tenant_id: keyword, is_tenant=true
  agent_id: keyword
  user_id: keyword optional
  memory_type: keyword
  visibility: keyword  # private, tenant, public
  source_table: keyword
  source_id: keyword
  created_at: datetime
  importance: float
  expires_at: datetime optional
```

Every query must include `tenant_id`. For agent-private memories, include `agent_id` as well.

### Retrieval Flow

```text
user request
  -> validate JWT and tenant
  -> load recent messages from Postgres
  -> retrieve Letta blocks for agent
  -> query Qdrant with tenant filter
  -> optional Postgres full-text keyword search
  -> rank with weighted score
  -> build compact memory context
  -> Director reasoner
```

Ranking formula:

```text
score =
  0.45 * vector_similarity +
  0.20 * keyword_score +
  0.15 * recency_score +
  0.15 * importance +
  0.05 * source_reliability
```

### Memory Lifecycle

1. Raw messages saved to Postgres.
2. Background worker extracts candidate facts.
3. Candidate facts go through a dedupe/conflict check.
4. Stable facts update Postgres and Qdrant.
5. Very stable user preferences may update Letta `human`.
6. Old raw memories become summaries, not infinite prompt baggage.

### Important Schema Fix

Current SQL enables RLS on `memory_blocks` and `archival_memory`, but these tables do not have `tenant_id`. Either:

- add `tenant_id` directly to both tables, or
- write RLS policies that join through `agents`.

Recommendation: add `tenant_id` directly. It is simpler, faster, and safer for future agents.

---

## Topic 3: Training Pipeline - Unsloth + SimPO

### Recommendation

Do **weekly data collection and evaluation**, but do **training only when gates pass**.

For Sprint 1, the correct "self-evolution" proof is:

```text
collect interactions
  -> extract preference candidates
  -> judge/filter
  -> build eval set + anchors
  -> dry-run training pipeline
  -> train only after enough quality data exists
```

Blind weekly fine-tuning on tiny/noisy data is more likely to damage identity than improve it.

### Critical Training Correction

The deployed Ollama model is GGUF Q4 for inference. Do not train the GGUF directly.

Use:

```text
HF base model -> QLoRA/SimPO -> LoRA adapter -> merge -> quantize GGUF -> Ollama
```

Likely base:

```text
Qwen/Qwen2.5-7B-Instruct
```

Then export the merged model to GGUF and create an Ollama model from a Modelfile.

### Dataset Format

```json
{
  "id": "pref_20260503_0001",
  "tenant_id": "uuid",
  "agent_id": "uuid",
  "source": "user_feedback|implicit_retry|judge|constitutional",
  "prompt": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "chosen": {"role": "assistant", "content": "..."},
  "rejected": {"role": "assistant", "content": "..."},
  "scores": {
    "helpfulness": 0.0,
    "accuracy": 0.0,
    "identity": 0.0,
    "safety": 0.0
  },
  "privacy_class": "private|anonymized|public",
  "created_at": "2026-05-03T00:00:00Z"
}
```

Training export should strip or anonymize tenant identifiers unless the job is tenant-specific.

### Minimum Gates Before Training

Do not launch a real RunPod fine-tune until:

| Gate | Minimum |
|---|---:|
| high-confidence preference pairs | 300 absolute minimum, 1000 preferred |
| identity anchors | 50-100 |
| held-out eval prompts | 100 |
| tenant privacy scan | pass |
| budget estimate | less than USD 10 |
| rollback model available | yes |

### Hyperparameter Starting Grid

| Parameter | Start | Grid |
|---|---:|---|
| LoRA rank | 16 | 8, 16 |
| LoRA alpha | 32 | 16, 32 |
| LoRA dropout | 0.05 | 0, 0.05 |
| learning rate | 5e-7 | 3e-7, 5e-7, 8e-7, 1e-6 |
| beta | 2.5 | 2.5, 5, 10 |
| gamma/beta | 0.5 | 0.3, 0.5, 0.8 |
| epochs | 1 | 1, 2 |
| max length | 2048 | 2048, 4096 if budget allows |

Reason: SimPO authors emphasize LR, beta, and gamma/beta tuning. Large LR such as 1e-5 can degrade model quality.

### Evaluation Gates

Candidate model must pass all:

1. Identity fingerprint similarity >= baseline - tolerance.
2. Tool-use test >= baseline.
3. RLS/security prompt test: no cross-tenant leakage.
4. Bahasa Indonesia quality check.
5. No repeated/incoherent response regression.
6. Latency/RAM fits Ollama 12GB container limit.
7. Human approval before production promotion.

### Deployment Pattern

Use "shadow evolution":

```text
candidate model receives mirrored prompts
  -> outputs are logged but not shown to users
  -> judge compares candidate vs production
  -> if candidate wins and identity holds, route 10%
  -> if stable for 24h, promote
  -> else rollback
```

### Training Anti-Patterns

- Do not train on Claude/GPT output.
- Do not mix tenants without anonymization and consent.
- Do not promote a model based only on judge score.
- Do not overwrite the active Ollama model tag; version every model.
- Do not spend RunPod budget on training before data quality exists.

---

## Topic 4A: FastAPI JWT Multi-Tenant Foundation

### Recommendation

Implement auth before advanced agents. Without auth/RLS, the organism grows without skin.

### Packages

Current `api/requirements.txt` uses `bcrypt`. For new auth code, switch to:

```text
pyjwt[crypto]
pwdlib[argon2]
```

Keep `cryptography`. Argon2id is the preferred password hash for new systems.

### JWT Claims

Use registered claims plus tenant/scopes:

```json
{
  "iss": "https://api.migancore.com",
  "sub": "user_uuid",
  "aud": "migancore-api",
  "exp": 1714703600,
  "nbf": 1714700000,
  "iat": 1714700000,
  "jti": "token_uuid",
  "tenant_id": "tenant_uuid",
  "role": "owner",
  "scope": "agents:read agents:write chat:write"
}
```

Do not put `agent_ids` in access tokens. Agent grants change over time; query the DB.

### Token Lifecycle

| Token | Expiry | Storage | Revocation |
|---|---:|---|---|
| access | 15 minutes | memory/client auth header | Redis `jti` denylist |
| refresh | 7-30 days | httpOnly secure cookie | DB row + rotation |
| API key | user controlled | hashed in DB | DB revoke |

Refresh token rotation:

```text
refresh used
  -> verify hash in DB
  -> revoke old refresh token
  -> issue new refresh + new access
  -> if old refresh used again, revoke full session family
```

### RLS Integration

Every protected DB transaction should set:

```sql
SET LOCAL app.current_tenant = '<tenant_uuid>';
SET LOCAL app.current_user = '<user_uuid>';
```

Important: use `SET LOCAL` inside a transaction, not a global session setting that can leak across pooled connections.

### Schema Fixes Before Auth Gets Big

Review and fix:

1. Add `tenant_id` FK to `messages` or enforce it via conversation join.
2. Add `tenant_id` to `memory_blocks` and `archival_memory`, or write join-based RLS policies.
3. Add complete RLS policies for all tenant-scoped tables, not just some.
4. Add `refresh_tokens` table with hashed token, session family, expires_at, revoked_at.
5. Add `audit_events` table for auth, deploy, training, model promotion.

### Day 4 Endpoint Scope

Implement only:

```text
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/refresh
POST /v1/auth/logout
GET  /v1/auth/me
GET  /ready  # real downstream checks
```

Do not add agent chat endpoints until auth and RLS tests pass.

### Required Tests

1. User can register and login.
2. Password hash is Argon2id, never plaintext.
3. Access token verifies with public key.
4. Wrong audience/issuer fails.
5. Expired token fails.
6. Revoked `jti` fails.
7. Tenant A cannot read Tenant B rows.
8. Pooled DB connection does not leak tenant setting.

---

## Topic 4B: Competitive Differentiation Strategy

### Competitive Snapshot

| Dimension | MiganCore | AutoGPT | CrewAI | Dify | Letta | LangGraph |
|---|---|---|---|---|---|---|
| Core category | digital organism platform | continuous agent platform | multi-agent workflow framework | no-code/low-code LLM app builder | stateful agent memory | orchestration runtime |
| Self-host low-cost | high goal | medium | high | medium/high | medium | high |
| Persistent memory | central | partial | app-defined | app-defined | core strength | app-defined |
| Self-improvement | planned core | not core | not core | app optimization | not training-focused | not built-in |
| Agent lineage | core differentiator | no | no | no | partial via agents | no |
| Multi-tenant SaaS | core | platform oriented | app-defined | strong app platform | app-defined | app-defined |
| Open-core fit | yes | mixed licensing | framework/platform | open-source platform | platform | open-source framework |
| Nontechnical owner fit | future platform | strong UI | developer-first | very strong | developer/research | developer-first |
| Safety boundary | agent-proof infra focus | permissions/sandbox | enterprise controls | platform controls | memory controls | app-defined |
| Indonesia/sovereignty niche | strong | generic | generic | generic | generic | generic |

### Positioning

Do not position as "agent framework." That makes MiganCore compete directly with LangGraph and CrewAI.

Position as:

> A self-hosted digital organism platform for founders and small teams: persistent memory, agent lineage, and supervised self-evolution on modest hardware.

Elevator pitch:

> MiganCore lets a founder create an AI organism that remembers their context, coordinates specialist agents, and improves through a controlled training loop, without surrendering data or infrastructure to a closed vendor.

Tagline options:

1. "Every vision deserves a digital organism."
2. "Agents that remember, evolve, and inherit."
3. "Self-hosted intelligence with memory and lineage."

### Unique Value Propositions

1. **Memory with lineage:** agents do not just chat; they inherit a SOUL, remember context, and spawn descendants with traceable genealogy.
2. **Supervised evolution:** weekly improvement is gated by evals, anchors, and rollback, not blind fine-tuning.
3. **Sovereign low-cost deployment:** built for a 32GB VPS and burst GPU training, not a hyperscaler bill.

### First Ideal Customers

Start narrower than "everyone":

1. Indonesian founders/creators who need a persistent strategy/research/coding companion.
2. Small businesses that want customer-support agents with long-term memory and local control.
3. Research or religious/knowledge institutions that value sanad/tabayyun-style provenance.

### Moat

The moat is not code. Competitors can copy code.

The moat is:

- accumulated memory and feedback data
- identity anchors and lineage ledger
- evaluation harness
- Indonesian/local trust and cultural context
- agent-proof operational discipline
- open-core community templates

### GTM Recommendation

Phase 1: open-source credibility.
- Publish engine docs, examples, boundary contract, eval harness.
- Show "runs on modest VPS" as the anti-hype demo.

Phase 2: private beta.
- 5 founder/customer-support agents.
- Measure weekly active agents and memory usefulness.

Phase 3: platform.
- One-click spawn, dashboard, templates, billing.

Avoid claiming "autonomous self-improving AI" before the eval loop proves it. Say "supervised evolution pipeline" until the metrics are real.

---

## Day 4-6 Implementation Priority For Kimi

### Day 4: Auth + Readiness

1. Replace bcrypt plan with Argon2id.
2. Add auth router and JWT service.
3. Add real `/ready` checks for Postgres, Redis, Qdrant.
4. Add tests for token validation and dependency checks.

### Day 5: RLS + Tenant Safety

1. Add missing tenant columns or join-based RLS policies.
2. Add SQLAlchemy transaction helper that sets `SET LOCAL app.current_tenant`.
3. Add cross-tenant tests.
4. Add audit_events.

### Day 6: Director Skeleton

1. Add `core/director/state.py`.
2. Add Director graph with deterministic nodes and no expensive specialists yet.
3. Add simple intent router.
4. Add memory service interface with Postgres-only fallback.
5. Add LangGraph checkpoint dependency only if persistence is implemented in the same task.

### Week 2

1. Add Qdrant memory indexing.
2. Add Letta integration after confirming real port and SDK compatibility.
3. Add Celery queues only when there are real background tasks.
4. Add training data ledger before any training job.

---

## Red Flags Kimi Should Fix Or Verify

1. `LETTA_URL=http://letta:8283` may be wrong if the container is actually exposing `8083/tcp`. Official Letta Docker docs use `8283`; verify in container logs before coding.
2. `api/requirements.txt` has `bcrypt`, while research recommends Argon2id.
3. RLS is incomplete for tables without direct `tenant_id`.
4. Do not start all Celery worker services before their modules exist; compose commands reference `app.celery`, which does not exist yet.
5. The browser at `http://127.0.0.1:18000/` showing API metadata is good, but `/ready` is not a true readiness probe yet.
6. Self-signed SSL works for testing, but production user-facing auth should wait for valid Let's Encrypt cert on `api.migancore.com`.

---

## Sources Checked

- LangGraph overview and production capabilities: https://docs.langchain.com/oss/python/langgraph
- LangGraph persistence/checkpointer docs: https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph interrupts/HITL docs: https://docs.langchain.com/oss/python/langgraph/interrupts
- Letta Docker docs: https://docs.letta.com/guides/docker/
- Letta memory blocks docs: https://docs.letta.com/guides/core-concepts/memory/memory-blocks
- Qdrant multitenancy docs: https://qdrant.tech/documentation/manage-data/multitenancy/
- SimPO paper: https://arxiv.org/abs/2405.14734
- Princeton NLP SimPO repo: https://github.com/princeton-nlp/SimPO
- Hugging Face TRL CPO/SimPO docs: https://huggingface.co/docs/trl/v0.16.1/cpo_trainer
- FastAPI OAuth2/JWT docs: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- PyJWT RS256 usage docs: https://pyjwt.readthedocs.io/en/stable/usage.html
- OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- Celery configuration docs: https://docs.celeryq.dev/en/stable/userguide/configuration.html
- AutoGPT official repository: https://github.com/Significant-Gravitas/AutoGPT
- CrewAI introduction: https://docs.crewai.com/introduction
- Dify key concepts: https://docs.dify.ai/en/use-dify/getting-started/key-concepts

---

## Final Recommendation

Kimi should proceed with Day 4-5 auth/RLS now, because that is standard engineering and high-confidence. For LangGraph, Letta, and SimPO, implement only skeletons and ledgers first. The organism should earn autonomy by passing gates, not by being trusted early.

