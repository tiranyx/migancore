# MIGANCORE — FOUNDER_JOURNAL.md
**Decisions, Learnings, and Strategic Reflections**

> This is the founder's running journal. It captures *why* decisions were made, not just *what* was built. Future agents should read this to understand the reasoning behind architectural choices.

---

## Entry 1 — Day 0: Why "Autonomous Digital Organism"?

**Decision:** Position MiganCore as an organism, not a chatbot.

**Reasoning:**
Chatbots are disposable. Organisms evolve, remember, reproduce. The metaphor shapes every technical decision:
- Memory is not caching — it's experience
- Spawning is not templating — it's reproduction with mutation
- Training is not fine-tuning — it's evolution

**Impact:** This framing justified the complexity of agent genealogy, memory tiers, and the SOUL.md concept.

---

## Entry 2 — Day 3: CPU Inference Reality

**Decision:** Accept CPU-only inference for MVP. No GPU on VPS.

**Reasoning:**
- RunPod GPU costs $0.50-2.00/hr. At 24/7, that's $360-1,440/month.
- Qwen2.5-7B on CPU gives 7-14 tok/s — usable for MVP, not production.
- Seed stage budget: $0 spent of $50 allocated.

**Trade-off:** Latency vs. cost. We chose cost.

**Future path:** When token volume justifies it, migrate to RunPod or local GPU.

---

## Entry 3 — Day 4: RS256 over HS256

**Decision:** Use asymmetric JWT (RS256) instead of symmetric (HS256).

**Reasoning:**
- HS256 requires sharing the secret between services — any leak compromises everything
- RS256: public key can be distributed safely; only the gateway holds the private key
- Future microservices can verify tokens without accessing secrets

**Cost:** More complex key management. Worth it.

---

## Entry 4 — Day 5: RLS is Non-Negotiable

**Decision:** PostgreSQL Row Level Security from day one.

**Reasoning:**
- Multi-tenancy bugs are catastrophic (data leakage)
- RLS is defense-in-depth: even if application code has a bug, the database enforces isolation
- `set_config('app.current_tenant', ...)` pattern is clean and testable

**Lesson:** RLS added ~10% dev overhead but eliminated an entire class of security bugs.

---

## Entry 5 — Day 6: SOUL.md as Living Document

**Decision:** Each agent has a SOUL.md — a markdown manifesto of identity.

**Reasoning:**
- JSON is too rigid for persona (nested objects, escaping issues)
- Markdown is human-editable and LLM-friendly
- SOUL.md becomes the "genome" that gets inherited during spawning
- `persona_overrides` in `agents.json` provides structured mutations

**Unexpected benefit:** SOUL.md files are self-documenting. New developers understand an agent's purpose by reading its soul.

---

## Entry 6 — Day 7: Redis over Letta for Tier 1

**Decision:** Defer Letta (Day 11), use Redis K-V for Tier 1 memory.

**Reasoning:**
- Letta cold-start: requires database init, agent creation, block management
- Redis: single SET/GET, TTL built-in, no state to manage
- For MVP, agents need ~20 facts max. Redis handles this trivially.

**Lesson:** Don't build infrastructure before you need it. Letta's working memory blocks are powerful but overkill for PoC.

---

## Entry 7 — Day 8: subprocess over exec() for Python REPL

**Decision:** Use `subprocess.run()` for Python code execution, not `exec()` with restricted builtins.

**Reasoning:**
- `exec()` sandbox is trivially escaped via `().__class__.__bases__[0].__subclasses__()`
- subprocess = real OS process boundary. Even if code escapes Python, it's still in a subprocess.
- Timeout and output cap are straightforward

**Trade-off:** Slower (~100ms startup). Acceptable for MVP.

---

## Entry 8 — Day 9: LangGraph over Plain Loop

**Decision:** Replace `for` loop with LangGraph `StateGraph`.

**Reasoning:**
- Plain loops become unmaintainable when adding branches (reflection, human-in-the-loop)
- LangGraph gives: typed state, conditional edges, checkpointing potential
- Nodes are testable in isolation

**Unexpected challenge:** Ollama 0.22.1 doesn't support native tool calling. Fallback logic added.

**Lesson:** Frameworks add value when the complexity they solve exceeds their own complexity. At Day 9, we crossed that threshold.

---

## Entry 9 — Day 10: The Schema Mismatch Crisis

**Discovery:** ORM and SQL schema had diverged significantly.

**What happened:**
- `migrations/init.sql` was the "source of truth" but had been updated on the VPS manually
- ORM added `description`, `system_prompt` columns not in init.sql
- SQL had `letta_agent_id`, `webhook_url`, `avg_quality_score` not in ORM
- Both had `model_version` (string in ORM) vs `model_version_id` (UUID FK in SQL)

**Root cause:** No Alembic. Raw SQL migrations require manual discipline. We failed.

**Fix:**
1. Audit both schemas
2. Create `010_day10_schema_sync.sql`
3. Update init.sql to match reality
4. Update ORM to include all columns

**Lesson:** Schema drift is a silent killer. Alembic setup is now P0 for Week 2.

---

## Entry 10 — Agent Collaboration Model

**Observation:** Different AI agents (Kimi, Claude) have different strengths.

**Pattern that works:**
- **Kimi:** Infrastructure, DevOps, systematic debugging, schema work
- **Claude:** Architecture design, creative features, frontend polish

**Anti-pattern discovered:**
- Don't let one agent make assumptions about another's work. The schema mismatch happened because Claude assumed the init.sql was current.
- Always verify: `\d tablename` on the live DB before trusting any schema file.

**Protocol added:** Every agent MUST run `docker compose exec postgres psql -U ado_app -d ado -c '\d {table}'` before modifying any table.

---

## Entry 11 — Tool Calling: The Ollama Surprise

**Discovery:** Ollama 0.22.1 `/api/chat` returns 404 when `tools` field is sent.

**What we assumed:** Tool calling works since Ollama docs say it's supported.
**Reality:** VPS has Ollama 0.22.1 (older). Model `qwen2.5:7b-instruct-q4_K_M` supports tools natively, but the Ollama version didn't expose the endpoint correctly.

**Fix:** Graceful fallback in `director.py` — if tool call fails, fall back to plain chat.

**Lesson:** Always test the actual deployed version, not just read docs.

---

## Strategic Principles (Living)

1. **Verify before trusting** — Any schema, config, or dependency claim must be verified against the live system.
2. **Fix debt before building** — Day 10 proved that ignoring schema mismatch would have caused explosions in Week 2.
3. **E2E test is the only truth** — Unit tests prove code works. E2E tests prove the system works.
4. **Document the why, not just the what** — This journal exists because future agents need context, not just code.

---

*Next entry: Week 2 learnings (Letta integration, Qdrant RAG, training pipeline)*
