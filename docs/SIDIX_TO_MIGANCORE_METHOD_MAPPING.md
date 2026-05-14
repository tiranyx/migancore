# SIDIX to MiganCore Method Mapping

Date: 2026-05-15
Status: Canonical method bridge
Owner: Fahmi + MiganCore

## Purpose

SIDIX contains many mature metaphorical methods. MiganCore must not copy them
blindly and must not ignore them either. This file maps SIDIX methods into the
MiganCore organism architecture so future agents know which ideas are already
implemented, which should be generalized, and which should stay deferred.

Core distinction:

```text
SIDIX = philosophical prototype and research sibling.
MiganCore = multi-tenant productized organism engine.
```

Adopt methods, contracts, and taxonomies. Do not import SIDIX answer content
directly into MiganCore training without filtering, provenance, and evaluation.

## Sources Read

Repo docs:
- `docs/KIMI_ANALYSIS_AND_PLAN.md`
- `docs/DAY0-5_COMPREHENSIVE_REVIEW.md`
- `docs/SYNTHESIS_KIMI_GPT_CLAUDE.md`
- `docs/ADO_KNOWLEDGE_RETURN_DESIGN.md`
- `docs/SPRINT_1_CLOSING_LOG_2026-05-14.md`
- `docs/SPRINT_LOG.md`
- `docs/ORGANISM_IMPLEMENTATION_MAPPING.md`

SIDIX read-only sources sampled from `/opt/sidix/brain/public`:
- `research_notes/288_cognitive_synthesis_kernel_iteration_pattern.md`
- `research_notes/305_jurus_seribu_bayangan_holistic_orchestrator_20260430.md`
- `research_notes/311_sidix_io_and_growth_synthesis.md`
- `research_notes/244_brain_anatomy_as_sidix_architecture.md`
- `research_notes/174_sidix_code_intelligence_module.md`
- `research_notes/189_arsitektur_jiwa_7_pilar_sidix.md`
- `research_notes/106_hafidz_mvp_implementation.md`
- `maqashid/tuned_profile.json`

## Method Mapping

| SIDIX Method | Meaning | MiganCore Body Part | Current MiganCore State | Decision |
|---|---|---|---|---|
| Nafs | Self-awareness, failure/success reflection, 3-layer knowledge fusion | Pikiran + Metabolisme | `reflection_daemon`, `code_lab`, `nafs` bucket partial | Adopt gradually |
| Aql / Akal | Judgment, validation, structured learning | Akal | Dev Organ gates + proposal lifecycle partial | Adopt directly |
| Qalb | Emotional resonance and healing | Jiwa + Imun | `voice_tone`, `qalb` bucket partial | Adopt as creator relationship + health signal |
| Ruh | Self-improvement continuity | Jiwa + Metabolisme | Northstar docs, auto-train proposal mode partial | Adopt as identity-preserving growth |
| Hayat | Generate -> evaluate -> refine -> repeat | Pikiran + Akal + Organ | Dev Organ loop partial | Adopt as module iteration contract |
| Ilm | Knowledge acquisition and study library | Indera + Otak | SIDIX brain inherit, docs ingestion, Qdrant partial | Adopt with provenance filters |
| Hikmah | Wisdom from successful patterns | Metabolisme | `hikmah` bucket via Code Lab partial | Adopt as reusable lesson layer |
| Raudah | Multi-agent orchestration in waves | Syaraf + Otak | LangGraph-style routing, no full swarm yet | Defer until workload justifies |
| Jurus Seribu Bayangan | Parallel multi-source fanout and synthesis | Otak + Syaraf + Indera | Tool router + memory/search partial | Adopt as deep mode, not default chat |
| Sanad | Provenance, source chain, claim verification | Akal + Imun | citation/source chips partial | Adopt for factual/high-stakes output |
| Pencernaan | Select -> digest -> absorb knowledge | Metabolisme | SIDIX ingest v2 with heading propagation partial | Adopt as ingestion standard |
| Mizan | Balance/homeostasis/drift detection | Akal + Imun | planned sprint-5 drift detection | Adopt after eval baselines |
| Kitabah Auto-Iterate | Writing/code artifact self-iteration | Organ + Akal | Artifact Builder planned | Adopt as first Artifact Builder loop |
| Brain Anatomy Mini-Apps | Many lightweight specialized background services | Full organism | `/v1/system/organism` and background daemons partial | Adopt as module architecture |
| world.json / skill-registry | Declarative agents and lazy skills | Syaraf + Organ | `agents.json`, `skills.json`, tool registry partial | Adopt and formalize |
| Ixonomic supply integrity | Invariants for quotas, tokens, value creation | Imun + Metabolisme | partial license/proposal gates | Adopt for cost/license gates |

## Adoption Rules

### Adopt Now

These patterns are already aligned with current architecture and low risk:

1. **Akal gates**
   - proposal -> readiness -> owner review -> sandbox -> promote
   - Current anchors: `api/services/dev_organ.py`, `api/routers/sandbox.py`

2. **Pencernaan ingestion**
   - preserve heading, source path, trust score, bucket, and freshness
   - Current anchors: SIDIX ingest v2, admin docs, memory search

3. **Hafidz partial**
   - child knowledge return is opt-in, anonymized, and reviewed
   - Current anchors: `api/routers/hafidz.py`, `api/services/hafidz.py`

4. **Nafs/Hikmah buckets**
   - failure becomes self-awareness
   - success becomes reusable wisdom
   - Current anchors: `api/services/code_lab.py`, `api/routers/reflection_daemon.py`

5. **world/skill registry idea**
   - agent identity and tools should be declarative and version-controlled
   - Current anchors: `api/config/agents.json`, `api/config/skills.json`

### Adopt With Guardrails

These are powerful but can become expensive or noisy if used everywhere:

1. **Jurus Seribu Bayangan**
   - Use for deep research, strategy, high-value synthesis, or complex creation.
   - Do not use for greetings, lightweight chat, or low-value queries.
   - MiganCore already has reflex/lightweight/full paths; this should be a
     fourth "deep synthesis" tier.

2. **CQF / Composite Quality Filter**
   - Useful for evals, training candidate review, artifacts, and high-stakes docs.
   - Too heavy for every response.
   - Implement as background scoring or promote gate, not default runtime tax.

3. **Raudah multi-agent waves**
   - Useful when a task naturally decomposes into research, analysis,
     engineering, writing, verification.
   - Defer as default until MiganCore has enough active users and eval data.

4. **Sanad**
   - Required for factual/high-stakes claims, docs, KB retrieval, and imported
     knowledge.
   - Optional for casual chat or creative ideation.

### Do Not Adopt Blindly

1. **SIDIX answer content into training**
   - Past docs already warned about hallucination transfer.
   - Safe use: topic taxonomy, framing patterns, source paths, method docs.
   - Unsafe use: auto-generated QA answers without review.

2. **IHOS or domain-specific terminology as MiganCore core identity**
   - MiganCore can understand SIDIX, but should not become SIDIX.
   - Keep MiganCore language broader: organism, creator bond, modular organs,
     multi-tenant clone economy.

3. **Always-on heavy fanout**
   - This can make MiganCore feel slow and expensive.
   - Reflex/lightweight/full/deep synthesis routing must remain.

## How SIDIX Maps Into MiganCore Organism

### Jiwa

Adopt:
- creator relationship depth from Qalb/Ruh
- identity continuity across clones
- "not a chatbot" doctrine

Do not adopt:
- SIDIX-specific persona names as core MiganCore identity

Next:
- Add eval prompts for organism identity and method explanation.

### Otak

Adopt:
- cognitive synthesis kernel
- 3-layer knowledge weighting as retrieval strategy
- deep synthesis mode for complex requests

Guardrail:
- Do not turn every chat into a multi-source fanout.

Next:
- Add `deep_synthesis` routing tier after full cognition.

### Pikiran

Adopt:
- idea -> synthesis -> module proposal habit
- reflection journal as thought trace
- chat insights becoming backlog/proposals

Next:
- Convert strong reflection output into proposal/eval candidate automatically.

### Akal

Adopt:
- Maqashid-like rule-first judgment, generalized as risk/cost/license/content gates.
- CQF as promotion score, not every-message score.

Next:
- Build reusable gate library for Artifact/Image/Video modules.

### Syaraf

Adopt:
- tool registry, skill registry, routing tiers, fanout/fanin.
- Raudah waves for decomposable tasks.

Next:
- Add routing eval to prevent reflex/tool/deep-mode misfires.

### Indera

Adopt:
- "input apapun" doctrine: text, image, audio, file, URL.
- normalize every input before cognition.

Next:
- Standardize modality schemas for image, video, audio, document, web.

### Organ

Adopt:
- Kitabah auto-iterate for Artifact Builder.
- SIDIX creative output doctrine: output should match requested medium.

Next:
- Build Artifact Builder MVP before GPU-heavy Image/Video modules.

### Metabolisme

Adopt:
- Pencernaan.
- Hafidz knowledge return.
- Ilm and Hikmah buckets.
- growth journal.

Next:
- approved proposal -> eval case
- strong output -> training candidate
- failed gate -> lesson

### Imun

Adopt:
- Mizan homeostasis.
- Sanad for provenance.
- supply integrity and two-step approval from Ixonomic/Mighantect.

Next:
- add cost/license/content/PII gates before heavy generator modules.

## Current Overlap Check

| Concern | Existing MiganCore Feature | SIDIX Equivalent | Overlap Risk | Resolution |
|---|---|---|---|---|
| Reflection | `reflection_daemon`, `nafs` | Nafs | Low | Keep MiganCore naming, cite SIDIX root |
| Voice/emotion | `voice_tone`, `qalb` | Qalb | Low | Use for creator bond, not mood theater |
| Knowledge ingest | admin docs, SIDIX ingest v2 | Ilm/Pencernaan | Medium | Keep provenance and trust score |
| Multi-source synthesis | tool router/search/memory | Seribu Bayangan | Medium | Make deep tier only |
| Eval quality | auto eval, readiness gates | CQF | Medium | Use CQF only for promotion/artifacts |
| Clone/return | license/Hafidz | 1000 Bayangan/Hafidz | Low | Continue opt-in anonymized path |
| Tool building | Dev Organ | Kitabah/Pencipta | Medium | Artifact Builder first, no uncontrolled deploy |

## Next Implementation Priority

1. **Artifact Builder MVP**
   - First real Organ.
   - Uses Kitabah auto-iterate.
   - Saves success to Hikmah and failures to Nafs.
   - Requires Akal + Imun gates.

2. **Reusable Gate Library**
   - cost, license, content, PII, rollback, eval exists.
   - This generalizes Maqashid/Mizan/Ixonomic approval into product code.

3. **Deep Synthesis Tier**
   - Jurus Seribu Bayangan adapted as explicit mode.
   - Trigger only for complex strategy, research, docs, artifact planning.

4. **SIDIX Content Safety**
   - Keep SIDIX as read-only library.
   - Use taxonomy/methods first.
   - Do not train on raw answers without review.

## Doctrine

SIDIX gives MiganCore a library of living metaphors. MiganCore's job is to
turn those metaphors into product contracts:

```text
metaphor -> technical contract -> gate -> test -> module -> memory -> training candidate
```

That is how the sibling systems complement each other instead of overlapping.
