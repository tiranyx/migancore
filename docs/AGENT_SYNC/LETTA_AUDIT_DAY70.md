# LETTA AUDIT — Day 70
**Date:** 2026-05-08
**Author:** Claude (Implementor)
**Status:** ✅ COMPLETE — No blocking issues found

---

## FINDINGS

### 1. Letta Service — RUNNING ✅
```
Container: ado-letta-1
Image: letta/letta:0.6.0
Port: 8283 (internal Docker network)
Status: Up 6+ hours, stable
```

### 2. Chat Router Wiring — CORRECT ✅
`api/routers/chat.py`:
- **Line 138:** `letta_blocks = await get_letta_blocks(agent.letta_agent_id)` — reads blocks before chat
- **Line 146:** `_build_system_prompt(..., letta_blocks, ...)` — injects persona/knowledge into system prompt
- **Lines 230-236:** `maybe_update_knowledge_block(...)` — runs after chat to update knowledge block

### 3. Agent DB State — WIRED ✅
```sql
SELECT COUNT(*) FROM agents WHERE letta_agent_id IS NOT NULL;
→ 24 agents have Letta IDs (including main MiganCore agent)
```

Main agent: `MiganCore` (id: `7778b521-65aa-4d74-871d-9defe6e881cd`)
- letta_agent_id: `agent-47bc80ad-cb64-4b9f-bd4b-e5130b57b9bf`
- 44+ messages received

### 4. Letta Blocks Status
```
=== persona (329 chars) ✅ ===
[IDENTITAS] Nama: MiganCore ... soul text correctly loaded

=== mission (117 chars) ✅ ===
Mendukung pengguna dalam ekosistem MiganCore ADO.

=== knowledge (66 chars) ❌ ===
Belum ada pengetahuan spesifik yang tersimpan tentang konteks ini.
```

### 5. Fact Extractor — DEPLOYED, CORRECT ✅
`api/services/fact_extractor.py`:
- Uses `qwen2.5:0.5b` (available in Ollama ✅)
- Fire-and-forget via `asyncio.create_task` ✅
- Date-sectioned format with FIFO trimming ✅
- Returns "TIDAK ADA" if no user-specific facts found ✅
- Graceful degradation (never raises) ✅

### 6. archival_memory PostgreSQL Table — DEAD SCHEMA
The `archival_memory` table exists in PostgreSQL but has NO writer anywhere in the codebase.
The actual persistent memory is stored in Letta's internal DB (knowledge block), NOT in this table.
This is by design — fact_extractor.py writes to Letta via REST API, not to archival_memory.

---

## ROOT CAUSE: Knowledge Block = Empty

**Why knowledge is at default after 44+ conversations:**

Beta user conversations are primarily testing/exploration:
- "Hai", "siapa kamu?", "apa itu ADO", "coba buat gambar"
- These contain NO extractable user-specific facts (names, professions, projects, preferences, stack)

The 0.5B extraction model correctly returns "TIDAK ADA" for general/test queries.
This is **expected behavior** — the system is working correctly.

**When knowledge WILL populate:**
- Users have substantive onboarding conversations ("nama saya X, saya kerja di Y, proyek Z")
- Users return and reference previous context
- Beta onboarding flow is implemented (Day 71+)

---

## GAP ANALYSIS vs CLAUDE_PLAN_70 Vision

| Gap | Status | Finding |
|-----|--------|---------|
| archival_memory = 0 (RED FLAG) | ✅ CLARIFIED | Not a bug — data goes to Letta's internal KB, not this table. The table is dead schema. |
| Letta unwired (claim) | ✅ REFUTED | Letta IS fully wired to chat router since Day 13-14. |
| Cross-session memory not working | ⚠️ PARTIAL | Mechanically correct. Functionally limited by low-context beta conversations. |

---

## RECOMMENDATIONS

### Immediate (Day 71)
- **No code changes needed.** Infrastructure is correct.
- Remove `archival_memory` table from schema or add a comment marking it as dead.
- Add a "memory active" indicator to admin dashboard (show knowledge block char count).

### Short-term (Day 75-80)
- **Onboarding conversation flow:** First 3 messages guide user to reveal:
  - Name + organization
  - Current project/goal
  - Preferred working style
  This gives fact extractor material to work with.
- **Trigger fact extraction from admin:** Admin can manually update knowledge blocks.

### Medium-term (Day 80-90)
- **Fact extraction from feedback:** When a user rates a response positively (thumbs up), store the topic as a preference fact.
- **KB weekly update triggers knowledge push:** After KB auto-update, relevant facts pushed to knowledge block.

---

## VERDICT

**No action required today.** Letta memory infrastructure is correctly implemented.
The "empty knowledge" is a content problem, not a code problem.
Priority order: Feedback flywheel → Onboarding flow → Knowledge accumulation naturally follows.

*Next review: Day 80 — check if knowledge blocks have grown post-onboarding.*
