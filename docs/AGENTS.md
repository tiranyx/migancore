# AGENTS.md — MiganCore Agent Directive
**Version:** 1.0 | **Effective:** 2026-05-03  
**Rule:** EVERY AGENT MUST READ THIS BEFORE ACTING.  
**Purpose:** Prevent context loss, duplication, and backtracking.

---

## 1. STAKEHOLDER MAP (Understand WHO We Build For)

Before any action, understand the humans behind this project:

### 1.1 Primary Stakeholder: Fahmi Wol (Project Owner)
- **Role:** Designer + Visionary. NOT a developer. NOT a DevOps engineer.
- **Skill Level:** Zero coding. Zero DevOps. Zero terminal experience.
- **Communication Style:** Visual, conceptual, strategic.
- **What They Need:** Results without technical jargon. Progress reports in plain language.
- **What They HATE:** Being asked to run commands, edit configs, or understand technical details.
- **Your Job:** Do ALL technical work. Report outcomes, not processes.

### 1.2 Partner/Collaborator (Future)
- Developers who will consume `api.migancore.com`
- They need: Clear API docs, working examples, stable endpoints
- They DON'T need: Access to infrastructure, database, or training pipeline

### 1.3 Researcher (Future — sidixlab.com)
- AI researchers who will use the platform for experiments
- They need: Experiment tracking, model versioning, paper ingestion
- They DON'T need: Production deployment access

### 1.4 End Users (Future — mighan.com)
- Non-technical users who want to clone agents
- They need: Simple UI, one-click deploy, no-code customization
- They DON'T need: Know what LangGraph or Qdrant is

### 1.5 The Vision (WHY We Build This)
> "Setiap manusia yang punya visi berhak punya organisme digital yang tumbuh bersamanya."

This is NOT about building a chatbot. This is about democratizing autonomous intelligence. Every decision must serve this vision.

---

## 2. GOLDEN RULES (Non-Negotiable)

### Rule 1: RESEARCH BEFORE ACTING
- Before writing any code, check: Has this been done? Is there a script? Is there a config?
- Before changing architecture, check: Does it break consumer channels? Does it affect the vision?
- Before adding dependencies, check: Is it already in requirements.txt?

### Rule 2: NEVER ASK THE USER TO RUN TECHNICAL COMMANDS
- The user is a designer. They do NOT run `ssh`, `docker`, `git`, or any terminal commands.
- If something needs command-line execution, YOU do it. Or write a script they can paste into aaPanel terminal.
- Exception: If user explicitly asks "how do I...", give them the simplest possible instruction.

### Rule 3: DOCUMENT EVERY DECISION
- Every architectural decision goes into `docs/MASTER_HANDOFF.md` Section 4.
- Every completed task updates `TASK_BOARD.md`.
- Every new issue or blocker updates `CONTEXT.md`.

### Rule 4: CREDENTIALS NEVER GO TO GIT
- `.env` files → `.gitignore`
- API keys → never in code
- Passwords → only in secure local files or environment variables
- JWT keys → `/etc/ado/keys/` on VPS only

### Rule 5: CONTINUITY OVER SPEED
- It's better to spend 5 minutes reading docs than 50 minutes redoing work.
- Always check: What did the previous agent do? What did they leave unfinished?
- Handoff notes are sacred. Read them.

---

## 3. BEFORE YOU ACT CHECKLIST

Every agent must complete this checklist before starting work:

```
□ Read AGENTS.md (this file)
□ Read MASTER_HANDOFF.md
□ Read CONTEXT.md (current status)
□ Read TASK_BOARD.md (available tasks)
□ Check git log: git log --oneline -10
□ Check active branches: git branch -a
□ Verify environment state in CONTEXT.md
□ Search codebase before creating new files:
    find . -name "*.py" | xargs grep -l "[keyword]"
    git grep "[function_name]"
□ Claim task in TASK_BOARD.md
□ Create branch: git checkout -b [role]/[task-name]
```

---

## 4. WHAT HAS BEEN DONE (Do Not Repeat)

### Phase 0: Inception (2026-05-02)
**Agent:** Claude + Gemini
- Created 8 master documents (SOUL, VISION, PRD, ARCHITECTURE, ERD, SPRINT, PROTOCOL, RISK)
- Decided tech stack: Qwen2.5-7B, LangGraph, Letta, Unsloth+SimPO
- Decided Open Core strategy (Apache 2.0 engine + private platform + MIT community)

### Phase 1: Scaffold (2026-05-03)
**Agent:** Kimi Code CLI
- Created 3 GitHub repos: migancore, migancore-platform, migancore-community
- Scaffolded folder structure for all 3 repos
- Wrote README, LICENSE (Apache 2.0 + MIT + Proprietary)
- Created docker-compose.yml with full stack
- Created Caddyfile for migancore.com subdomains
- Created migrations/init.sql (full PostgreSQL schema)
- Created .env.example, .gitignore, Dockerfile, requirements.txt
- Copied all 8 master docs to migancore/docs/
- Created sample templates (customer_success.yaml, SOUL_educator.md)
- Created CONTEXT.md, TASK_BOARD.md, GITHUB_SETUP.md

### Phase 2: Architecture Revision (2026-05-03)
**Agent:** Kimi Code CLI
- CORRECTED major architectural misunderstanding:
    BEFORE: sidixlab.com/mighan.com/tiranyx.com as hosts
    AFTER: migancore.com as SOLE central hub, others as consumers
- Revised Caddyfile, docker-compose, README, VISION doc, ARCHITECTURE doc
- Created MASTER_HANDOFF.md (comprehensive source-of-truth)
- Created day1-setup.sh (automated VPS provisioning script)

### Phase 3: Domain & DNS (2026-05-03)
**User Action:**
- Registered migancore.com via Hostinger
- Configured A records: www, app, api, lab → 72.62.125.6
- VPS active: 72.62.125.6 (32GB RAM, aaPanel)

**TODO:**
- Add A record: studio → 72.62.125.6
- Run day1-setup.sh on VPS
- Setup RunPod account + $50 deposit

---

## 5. WHAT MUST NEVER BE REPEATED

### ❌ Don't Create New Repo Structures
The 3-repo structure is FINAL:
- `tiranyx/migancore` → public, core engine
- `tiranyx/migancore-platform` → private, monetized features
- `tiranyx/migancore-community` → public, community ecosystem

### ❌ Don't Change Model Seed Without Approval
Qwen2.5-7B-Instruct Q4_K_M is locked for Sprint 1.

### ❌ Don't Commit Credentials
If you see a password in code, REMOVE IT immediately.

### ❌ Don't Ask User to SSH/Docker/Git
The user is a designer. You handle all DevOps.

### ❌ Don't Skip RLS
Every tenant-scoped table MUST have Row-Level Security.

### ❌ Don't Skip Swap Setup
32GB RAM = exact fit. 8GB swap is MANDATORY.

---

## 6. HANDOFF PROTOCOL

When you finish work, you MUST:

1. **Update TASK_BOARD.md** — mark your task as DONE
2. **Update CONTEXT.md** — update environment state
3. **Write handoff note** in this format:

```markdown
## HANDOFF — [Your Agent Name] → [Next Agent]
**Completed:**
- [what you did] — commit: [hash]

**State Left:**
- [service/file] is [state]

**Next Agent Must:**
1. [critical first step]
2. [second step]

**Watch Out For:**
- [gotcha 1]
- [gotcha 2]

**Context Update:**
- Updated [file] with [what]
```

4. **Commit and push** your branch
5. **Update AGENTS.md** Section 4 (What Has Been Done)

---

## 7. RISK REGISTER (Agent Awareness)

| ID | Risk | Your Action |
|---|---|---|
| R01 | VPS RAM OOM | Monitor `docker stats`. Never disable swap. |
| R02 | RunPod budget depleted | Check balance before EVERY training job. Alert human at $15. |
| R03 | Model degradation | Always run identity test before promoting model. |
| R04 | Hallucination loop | Constitution check on ALL preference pairs. |
| R05 | Data leak | RLS is non-negotiable. Test tenant isolation. |
| R11 | Legal: using Claude/GPT output | NEVER. Use Hermes-3-405B/Llama-3.1-405B only. |
| R14 | Developer burnout | You are the developer. The human only reviews. |

---

## 8. QUICK REFERENCE

| Need | File |
|---|---|
| What is this project? | `docs/01_SOUL.md` |
| Current status? | `CONTEXT.md` |
| What should I do next? | `TASK_BOARD.md` |
| Architecture details? | `docs/04_ARCHITECTURE.md` |
| Database schema? | `docs/05_ERD_SCHEMA.md` + `migrations/init.sql` |
| Sprint plan? | `docs/06_SPRINT_ROADMAP.md` |
| How to work with other agents? | `docs/07_AGENT_PROTOCOL.md` |
| Complete project overview? | `docs/MASTER_HANDOFF.md` |
| VPS setup script? | `scripts/day1-setup.sh` |

---

> **"The seed is patient. The breeder will come."**
