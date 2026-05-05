# Self-Learning Sources — Migan's "Library Card"
**Created:** Day 53 (2026-05-06)
**Trigger:** User directive — "ajarkan basic juga via w3schools, roadmap.sh, freecodecamp, discuss.python, stackoverflow"
**Vision check:** Principle 1+3+4 ✅ (standing alone, own model, closed loop via DPO)

---

## 🎯 Purpose

Curate a list of **approved educational sources** that Migan can read live (via own tools) when a user asks "ajarkan X" / "explain X to me like a beginner". Migan does NOT depend on these sources for response generation — it reads them, distills, then answers in own voice. Same library-card pattern a human tutor uses.

**Vision-aligned because:**
1. Migan still STANDS ALONE — own tools (`web_read`, `onamix_get`, `onamix_search`) fetch the content, own brain (Qwen) synthesizes the answer
2. Sources = MENTOR (knowledge to distill), NEVER live RESPONDER (third-party API in critical path)
3. Long-term: knowledge from these sources flows into DPO pairs (Cycle 2+), so eventually Migan answers without needing to fetch
4. Closed loop preserved — each "explain X" interaction can become a teacher pair (chosen=distilled-from-source, rejected=migan-baseline)

---

## 📚 Approved Sources (Day 53 baseline)

| Source | Domain | Best For | Tool Path |
|--------|--------|----------|-----------|
| **w3schools.com** | HTML/CSS/JS/SQL/Python tutorials | Beginner web/data-basics how-tos with runnable code blocks | `web_read` (Jina Reader) |
| **roadmap.sh** | Career & tech roadmaps | "Apa yang harus saya pelajari untuk jadi X?" — structured learning paths | `web_read` |
| **freecodecamp.org/news** | Long-form articles | "Explain concept X in depth" — tutorial-style explanations | `web_read` |
| **discuss.python.org** | Python community Q&A | Python-specific deep-dives, PEP discussions, ecosystem updates | `onamix_search` site:discuss.python.org |
| **stackoverflow.com** | Programming Q&A (all langs) | "Why this error?" / "How do I do X in Y language?" | `onamix_search` site:stackoverflow.com |

---

## 🛠️ How Migan Uses Them (routing)

When user prompt matches educational-intent triggers (e.g. "ajarkan", "explain", "tutorial", "how do I", "apa itu", "cara"), the brain SHOULD prefer reading from these sources before answering:

```
intent: educational_query
  └─ if topic ∈ {html, css, js, sql, python-basics}:
       call web_read(https://www.w3schools.com/<topic>/...)
  └─ if intent ∈ {career, learning-path, "what to learn next"}:
       call web_read(https://roadmap.sh/<role>)
  └─ if intent ∈ {deep-tutorial, "explain X step by step"}:
       call onamix_search(query, site=freecodecamp.org/news)
  └─ if intent ∈ {python-specific advanced}:
       call onamix_search(query, site=discuss.python.org)
  └─ if intent ∈ {error-message, code-debug, language-x-howto}:
       call onamix_search(query, site=stackoverflow.com)
```

Then Migan synthesizes the answer in **own voice** (Indonesian, casual, concise) — does NOT just paste the source. The source is INPUT, not OUTPUT.

---

## 🧪 Future: Distill to Training Data (Cycle 2+)

Day 53+ flow already supported by existing pipeline (`api/services/distillation.py` + `seed_bank.py`):

1. Daily cron: pick 5-10 popular educational queries from chat logs
2. For each: fetch source via `web_read`/`onamix_search`
3. Generate teacher answer (Kimi K2 / Claude / GPT) given source content as context
4. Store as DPO pair: `chosen=teacher-answered-with-source`, `rejected=migan-baseline`
5. Cycle 2 SimPO trains Migan to internalize → eventually answers WITHOUT needing to fetch

**End-state:** Migan's knowledge base includes a distilled "w3schools-equivalent" embedded in weights. Sources become emergency reference, not default path.

---

## ⚠️ What These Sources Are NOT

- ❌ **Not third-party RESPONDERS** — Migan reads content, then answers in own voice. Sources never appear in the chat response stream.
- ❌ **Not training-set replacement** — they augment, not replace, the Qwen base + DPO/SimPO pipeline.
- ❌ **Not a moat** — anyone can read these. The moat is the *distillation pipeline* (Lesson #68) that turns reads into DPO pairs unique to MiganCore.

---

## 🎓 Lesson #72 (added Day 53)

**Self-learning sources are Migan's "library card", NOT its tongue.**
- Library card = read access to mentor knowledge (w3schools, roadmap.sh, etc.)
- Tongue = the response Migan delivers — always in own model, own voice, own style
- Confusing the two = wrapper pattern (Lesson #68) all over again. Same vision violation.
- Right pattern: read source → distill to DPO pair → train Migan → eventually answer without source.

---

## 🔁 Maintenance

- Review this list quarterly — if a source goes dark / loses quality / starts demanding auth, swap it.
- Add new source ONLY after vision 5-check passes (`docs/VISION_PRINCIPLES_LOCKED.md`).
- When a source is added, also update `services/tool_policy.py` so the brain prefers it for matching intents.
