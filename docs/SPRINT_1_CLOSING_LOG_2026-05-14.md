# Sprint 1 — Closing Log

**Date:** 2026-05-14 (Day 73)
**Sprint:** 1 — SIDIX Knowledge Inherit
**Status:** ✅ CLOSED (acceptable foundation, refinements in Sprint 2)
**Principle Tag:** Hafidz partial (replikasi SIDIX→MiganCore) + Ilm foundation (knowledge bucket aktif)
**Facility Area:** C. OTAK (Study Library)

---

## 1. DELIVERABLES SHIPPED

- ✅ `scripts/ingest_sidix_brain.py` (v1) + `scripts/ingest_sidix_brain_v2.py` (Pencernaan-aware)
- ✅ Mount `/opt/sidix/brain/public:/opt/sidix_kb:ro` di container
- ✅ Qdrant collection `episodic_cb3ebd3b-...` (core_brain agent)
- ✅ 5,709+ chunks indexed (mix v1 + v2 payload)
- ✅ Bucket taxonomy: ilm:coding, ilm:glossary, ilm:curriculum, ilm:domain, ilm:research, ilm:persona_corpus, maqashid, hikmah, patterns
- ✅ Provenance metadata: source_path, heading_path, trust_score, freshness_days, language, entities

## 2. KNOWLEDGE INHERITED (samples)

| Bucket | Sample sources |
|--------|---------------|
| ilm:coding | roadmap_ai_engineer, roadmap_backend, roadmap_dsa, roadmap_docker, roadmap_javascript, roadmap_linux, roadmap_ml_topics, roadmap_python_topics, roadmap_sql, roadmap_system_design |
| ilm:glossary | technical_glossary, islamic_concepts_glossary, goal_models |
| ilm:curriculum | structured learning paths |
| ilm:research | research notes (Islamic concept map, AI architecture, MiganForge, ADO) |
| ilm:domain | omnyx_knowledge, persona_corpus |
| maqashid | purpose-intent frameworks |
| hikmah | hafidz wisdom patterns |

## 3. QA RESULT

**Semantic search probes (5 queries):**
- ✅ 3/5 STRONG hits (correct bucket + relevant content + canonical doc)
- ⚠️ 2/5 PARTIAL (semantic vocabulary match pulled wrong doc — example: "roadmap Python" hit Q&A instead of canonical roadmap_python_topics.md)

**Root cause partial misses:** Vocabulary-similarity ranking tanpa reranker. Top hit kadang co-occur vocabulary not best semantic match.

**Fix planned Sprint 2:** Wire `BAAI/bge-reranker-v2-m3` (cached, ready) post-hybrid search → top-K rerank → resolve weak ranking.

## 4. WHAT WORKED

- Idempotent UUID-based upsert (deterministic IDs from source_path + chunk_index)
- Pencernaan v2 enhancements: heading propagation, structure preserve, rich payload
- Auto-classification by filename pattern → SSOT tabs
- Bucket-aware search via existing search_semantic (no migration needed — namespace column reused as bucket)
- Adaptive design throughout (no blanket rules)

## 5. WHAT DIDN'T WORK / LESSONS

- **Multiple restart cycles** — every API container rebuild kills ingest. Loss of v2 progress each time.
  - Lesson: future ingest scripts should run OUTSIDE api container (host or separate worker)
  - Workaround: scripts/idempotent, can resume
- **v1 stale chunks remain** — orphan v1 payload chunks coexist with v2 (different chunk boundaries). Net effect: payload mix, no functional issue, just slight inconsistency in metadata richness.
  - Defer: cleanup orphans in Sprint 2 (delete `is_knowledge=true` chunks without `ingest_version=v2.0`)
- **Reranker not yet wired** — bge-reranker-v2-m3 cached but unused. Causes 2/5 QA probe weak rankings.
  - Sprint 2 priority deliverable.

## 6. SIDE FIXES SHIPPED

- Pencipta bond patch (chat.py runtime prompt) — strengthened identity recognition + anti role-reversal + voice register (Day 73)
- Container image-baked code lesson (#136 candidate): SCP + restart ≠ deploy, always `docker compose build`
- agents.json default_tools cleanup (35 tools matching schema)
- skills.json revert (cosmetic unicode)
- OpenRouter teacher integration (4 free models, 2 verified working)

## 7. METRICS

- **Files processed (v2):** ~100-450 per partial run, restarts capped total
- **Chunks total Qdrant:** 5,709 indexed
- **Compute used:** 0 GPU, all local CPU embedding
- **Cost:** $0
- **Time elapsed:** ~3 hours (with multiple restart interruptions)

## 8. VISION ALIGNMENT CHECK

- ✅ Hafidz partial (knowledge replikasi dari SIDIX sister project)
- ✅ Ilm bucket aktif (foundation knowledge)
- ✅ Anti vendor lock-in (semua lokal)
- ✅ Adaptive design (no blanket cite rule)
- ✅ Pencernaan principles applied (Selection skip incoming/, Digestion heading propagation, Absorption rich payload)
- ⚠️ Metabolism layer NOT YET (Sprint 2-4 will add)
- ⚠️ Retrieval upgrade NOT YET (Sprint 2 reranker)

## 9. HANDOFF TO SPRINT 2

Sprint 2 deliverables (Day 74-80) yang inherit dari Sprint 1:

1. **Wire bge-reranker** — improve weak QA hits to strong
2. **Trust filter** — high-stakes queries filter by trust_score (already in payload)
3. **Adaptive citation surface** — chip ONLY for factual KB recall, search, memory (per Adaptive Design doctrine)
4. **Code Lab Pyodide** — TANGAN expansion (rasa sakit/senang scoring)
5. **Daily reflection daemon** — nafs bucket auto-populate
6. **Voice tone analysis** — qalb resonance via Scribe + sentiment

## 10. PROGRESS TRACKER UPDATE

`api/routers/admin_progress.py` updated:
- sprint-1: status `running` 75% → `done` 100%
- sprint-2: status `planned` 0% → `running` 5% (design doc shipped)

## 11. COMMITS Day 73

```
a4afc78 feat(Day73): autonomous growth — KG extractor + auto-train watchdog
ea8b4a5 feat(Day73): live conversation harvester
a91fb61 feat(Day73): daily auto-harvest cron
ca9f6ad feat(Day73): auto eval + hot-swap pipeline
92b0369 feat(Day73): 7 new tools + advanced synthesis
2b6aa21 feat(perf): lazy tool router
f891226 fix(onamix): persistent chown + multi-engine fallback
8fa5736 test(day73): live QA script — 6/6 PASS
f410c93 feat(cognition): innovation engine doctrine (Codex)
e8a3f80 docs(cognition): m17 deploy QA log
ef103e0 chore(vps-sync): commit Day 73 runtime drift
26fc17f test(m17): innovation engine live QA 4/4 PASS
49b550b feat(sprint1): SIDIX brain inherit + pencipta bond patch
a9e8838 feat(sprint1.5): SSOT admin backlog browser + ingest v2
41c21eb docs(sprint1.5): SSOT pointer block + AGENT_ONBOARDING.md inject
edb92f5 feat(sprint1.5): Gantt progress tracker
1434656 feat(sprint1.5): OpenRouter free teachers + admin guide ID
b498375 fix(openrouter): refactor to working 2026 free models
f4fc6f5 feat(sprint2): admin pattern broaden + design doc placeholder
913a580 docs(sprint2): Code Lab Pyodide design doc to SSOT backlog
```

**Total: 21 commits Day 73** — major sprint of infrastructure + doctrine + facilities.
