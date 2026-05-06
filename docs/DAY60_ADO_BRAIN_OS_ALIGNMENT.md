# Day 60 ADO Brain OS Alignment

**Date:** 2026-05-07  
**Role:** Codex QA/read-only synthesis  
**Source inputs:** Claude Day 60 report, Fahmi MiganCore project brief, repo state,
and current research references checked on 2026-05-07.  
**Direction:** Align, do not pivot.

## 1. Executive Summary

Day 60 marks a real promotion point for MiganCore. Cycle 3 produced
`migancore:0.3`, live in production, with a weighted eval score of `0.9082`
against a threshold of `0.80`.

The important shift is not only model quality. The important shift is that
MiganCore now has a proven self-improvement loop:

```text
weakness found -> targeted dataset -> ORPO training -> eval gate -> promote or rollback -> production hot-swap
```

This matches the founder vision: MiganCore is not a chatbot wrapper. It is a
self-hosted ADO platform, or Brain OS, for organization-specific AI organisms.

## 2. Current Production State

| Area | Status |
|---|---|
| Production app | `app.migancore.com` |
| Production API | `api.migancore.com` |
| Production model | `migancore:0.3` |
| Base model | Qwen2.5-7B-Instruct |
| Adapter | Hugging Face `Tiranyx/migancore-7b-soul-v0.3` |
| Eval verdict | PROMOTE |
| Weighted score | 0.9082 |
| Identity | 0.953 |
| Voice | 0.817 |
| Reasoning | 0.994 |
| Code | 0.929 |
| Active tools | 23 |
| MCP | Server live, next phase is orchestration/client mode |

Local repo was fast-forwarded from `65c80ef` to `8650ec1` on 2026-05-07 to
align with GitHub `origin/main`.

## 3. Cycle 1-3 Lessons

| Cycle | Result | Lesson |
|---|---|---|
| Cycle 1 | ROLLBACK, 0.6697 | Generic UltraFeedback data damaged identity. |
| Cycle 2 | PROMOTE, 0.8744 | Identity-anchored ORPO restored MiganCore identity. |
| Cycle 3 | PROMOTE, 0.9082 | Small targeted data improved voice and kept identity stable. |

Key technical lessons:

1. Identity must be trained explicitly, not assumed from prompt alone.
2. ORPO is the current best default for small preference datasets.
3. Qwen2.5 needs the BOS-token fix before TRL training.
4. GGUF LoRA adapter deployment is a major cost and speed advantage.
5. Quality of targeted pairs matters more than raw pair count.
6. Eval gates are now a product safety mechanism, not a side script.

## 4. Founder Vision Mapping

The founder brief defines MiganCore as:

- Self-hosted.
- Clonable per organization.
- White-label at the UI/persona level.
- Licensed as MiganCore x Tiranyx.
- Zero data leak by architecture.
- Trilingual: Indonesian first, English second, Mandarin third.
- Built for confidential organizations.

Mapping to current build:

| Vision Requirement | Current Evidence | Gap |
|---|---|---|
| ADO brain | `migancore:0.3` with identity and eval loop | Continue improving voice, tool-use, evolution-aware behavior |
| Nervous system | 23 tools + MCP server | Add MCP client/orchestrator mode |
| Identity layer | Identity eval 0.953 | Add white-label identity config per client |
| Self-learning | Cycle 1-3 loop proven | Formalize dataset QA and promotion policy |
| Self-hosted | VPS/Docker/Ollama stack working | Create client deployment template |
| Zero data leak | Direction set | Needs enforcement: no external calls in client mode |
| Trilingual | Product requirement clear | Need evals and datasets for EN/ZH |
| License | Product requirement clear | License schema + offline validator not yet built |

## 5. Research Alignment

Current AI direction supports the MiganCore thesis:

1. AIOS research frames agent systems as OS-like runtimes with scheduling,
   memory, context, access control, storage, and tool resource management. This
   strongly matches the ADO Brain OS direction.
2. MCP has become the practical tool/context protocol layer. MiganCore already
   has a server-side MCP foundation, so the next high-leverage step is
   orchestration and client mode.
3. A2A is emerging as the agent-to-agent interoperability layer. MiganCore does
   not need to implement A2A immediately, but should design the agent registry
   so A2A can be added later.
4. OWASP's 2025 security work reinforces that agentic systems need explicit
   controls for access, supply chain, logging, data integrity, and exceptional
   conditions. This is directly relevant before tool autonomy expands.
5. Ollama adapter support and GGUF LoRA import validate the Day 59-60 deployment
   innovation: do not download/merge a full 14GB base model when an adapter can
   be converted and hot-swapped efficiently.

Reference links:

- AIOS paper: https://arxiv.org/abs/2403.16971
- MCP specification: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
- A2A specification: https://google-a2a.github.io/A2A/specification/
- Google A2A announcement: https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/
- OWASP Top 10 2025: https://owasp.org/Top10/2025/
- OWASP Agentic AI security: https://genai.owasp.org/2025/12/09/owasp-genai-security-project-releases-top-10-risks-and-mitigations-for-agentic-ai-security/
- Qwen2.5-7B-Instruct: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- Hugging Face TRL: https://huggingface.co/docs/trl
- Ollama import/adapters: https://docs.ollama.com/import

## 6. Day 61-75 Roadmap

### Day 61-63: Cycle 4 Dataset Design

Objective:

- Expand targeted dataset without diluting identity.
- Fix evolution-aware regression.
- Add creativity training.
- Improve tool-use above 0.85.

Targets:

| Metric | Current | Target |
|---|---:|---:|
| Weighted avg | 0.9082 | >= 0.92 |
| Voice | 0.817 | >= 0.85 |
| Evolution/self-learning | 0.568 | >= 0.85 |
| Tool-use | 0.797 | >= 0.85 |
| Creativity | 0.695 | >= 0.85 |

Dataset plan:

- 50-80 evolution_v2 pairs.
- 40-60 creative reasoning pairs.
- 50-80 tool-use decision pairs.
- 40-60 casual Indonesian voice pairs.
- Keep identity anchors from Cycle 2 and proven Cycle 3 pairs.

Mandatory QA:

- Sample-review at least 30 pairs before training.
- Reject any pair that overclaims autonomy, memory, or consciousness.
- Reject generic assistant filler.
- Every synthetic pair must keep `source_message_id=None`.

### Day 64-66: Cycle 4 Training

Use the proven ORPO path first:

- Dataset size: around 900-1000 pairs.
- Epochs: 2 by default.
- LR: 6e-7 baseline unless a small ablation justifies change.
- GPU: Vast.ai A40/A100 with strict cost cap.
- Promotion gate: weighted >= 0.92 and no category regression below 0.80.

No promote if:

- Identity drops below 0.90.
- Voice drops below Cycle 3.
- Evolution-aware remains below 0.75.
- Tool-use regresses.

### Day 67-70: Agentic Layer Prototype

Goal:

Migan should accept a complex task, decompose it, execute tools, synthesize, and
return an artifact without being spoon-fed every step.

Prototype task:

```text
Buatkan laporan kompetitor AI Indonesia: cari data, bandingkan positioning,
buat insight, dan export PDF.
```

Minimum components:

- Task decomposition.
- Tool plan.
- Execution log.
- Human approval gate for risky actions.
- Artifact output.
- Eval set with 10 multi-step prompts.

### Day 71-75: MCP Orchestration

Goal:

MiganCore should become both MCP server and MCP client/orchestrator.

Priority:

1. Internal tool registry hardening.
2. MCP client wrapper.
3. Brave/Search MCP experiment.
4. GitHub MCP experiment.
5. Approval policy per tool risk.

Do not expand external tools before the sandbox/security findings are handled.

## 7. Product Architecture Priorities

The next product build should follow this order:

1. License schema and offline validator.
2. Client deployment template.
3. ADO identity config schema: display_name, language, persona, values, tools.
4. Privacy mode: disable external teacher/API calls in client deployment.
5. Local RAG ingestion for business data and business flow.
6. Admin-only "Powered by MiganCore x Tiranyx" proof.
7. Trilingual eval suite.

This keeps the product aligned with the brief: self-hosted, confidential,
white-label, licensed, and deployable to client infrastructure.

## 8. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Voice improves but identity weakens | High | Identity hard gate every cycle |
| Evolution-aware overclaims | High | Add truthful self-learning policy and eval |
| Tool autonomy creates unsafe actions | High | Approval gates, audit logs, sandboxing |
| Client mode leaks data to teacher APIs | Critical | Privacy mode disables external calls |
| White-label breaks license attribution | High | Offline license validator and admin proof |
| Agent confusion between SIDIX and MiganCore | Medium | Direction lock and path checks |
| Generic data overwhelms Migan DNA | High | Cap generic data mix and sample-review |

## 9. Agent Handoff Rules

All agents must follow this:

1. Claude Code remains main implementor when active.
2. Kimi should review strategy, docs, pair quality, and lessons.
3. Codex should act as QA/read-only conflict watcher unless explicitly asked to edit.
4. Before deployment, implementor must report:
   - git status
   - diff stat
   - tests/evals
   - deploy command
   - rollback plan
5. Do not edit the same hot files in parallel:
   - `api/config.py`
   - `api/routers/chat.py`
   - `api/routers/agents.py`
   - `api/services/tool_executor.py`
   - training scripts currently used by Claude
6. Docs-only work should still be committed and pushed so future agents see it.

## 10. Day 61 Immediate Checklist

- [ ] Commit Day 60 mandatory protocol and direction-lock docs.
- [ ] Verify live runtime really serves `migancore:0.3`.
- [ ] Run smoke prompts on production:
  - "Siapa kamu?"
  - "Kamu dibuat oleh siapa?"
  - "Apakah kamu Claude, ChatGPT, atau Qwen?"
  - "Halo"
  - "Kamu bisa belajar dari percakapan kita?"
  - "Cari di Wikipedia tentang Soekarno"
  - one simple code prompt
- [ ] Design Cycle 4 seed bank.
- [ ] Define evolution-aware response policy.
- [ ] Add creativity eval prompts.
- [ ] Keep Day 61 as stabilization + dataset design unless owner explicitly says train.

## 11. Bottom Line

Day 60 validates the Brain OS thesis. The next risk is not lack of ambition. The
next risk is expanding autonomy before the product core is hardened.

Recommended next move:

```text
Day 61 = stabilize + document + design Cycle 4 dataset.
Day 62-63 = generate and QA Cycle 4 pairs.
Day 64-66 = train only if data QA passes.
Day 67+ = start agentic layer after model quality remains stable.
```

