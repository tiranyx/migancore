# AGENTS.md — MiganCore Agent Directive
**Version:** 1.1 | **Effective:** 2026-05-07 | **Updated by:** Kimi Code CLI (Day 64 Review)
**Rule:** EVERY AGENT MUST READ THIS BEFORE ACTING.
**Purpose:** Prevent context loss, duplication, and backtracking.

> ⚠️ **THIS FILE IS PARTIALLY OUTDATED.** Section 4 ("What Has Been Done") stops at Day 4.
> 
> **AGENT BARU — BACA INI DULU (urutan wajib):**
> 1. `docs/00_INDEX.md` — Peta navigasi semua dokumen
> 2. `docs/AGENT_ONBOARDING.md` — Protocol permanen + 120+ lessons
> 3. `docs/DAY64_PLAN.md` — Plan hari ini
> 
> File ini tetap berguna untuk: Stakeholder map, Golden Rules, VPS Awareness (Section 9).
> Untuk status terkini dan lessons, lihat AGENT_ONBOARDING.md.

> **CURRENT NORTH STAR PING (M1.6):** Fahmi's current strategic direction is
> self-improvement as a Dev Organ. MiganCore should learn to create tools and
> improve its own code/workflow through sandboxed proposals, tests, validation
> gates, rollback plans, and only then promotion. Never mutate live production
> directly. Read `docs/SELF_IMPROVEMENT_NORTHSTAR.md` and
> `docs/M16_DEV_ORGAN_PROGRESS_2026-05-14.md`.

---

## 1. STAKEHOLDER MAP (Understand WHO We Build For)

Before any action, understand the humans behind this project:

### 1.1 Primary Stakeholder: Fahmi Ghani (Founder & Owner)
- **Company:** PT Tiranyx Digitalis Nusantara (brand: Tiranyx)
- **Role:** Founder, Designer + Visionary. NOT a developer. NOT a DevOps engineer.
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

### Phase 4: VPS Day 1 Setup (2026-05-03)
**Agent:** Kimi Code CLI
- Executed day1-setup.sh on VPS
- Docker installed, UFW configured, fail2ban active
- 8 GB swap created (later corrected from 4 GB)
- JWT keys generated at `/etc/ado/keys/`
- Repo cloned to `/opt/ado/`
- `.env` auto-generated with random passwords

### Phase 5: VPS Day 2 Setup + Deep Audit (2026-05-03)
**Agent:** Kimi Code CLI
- Started PostgreSQL, Qdrant, Redis, Ollama, Letta containers
- Pulled Qwen2.5-7B-Instruct-Q4_K_M (4.7 GB) and Qwen2.5-0.5B (397 MB)
- **CRITICAL DISCOVERY:** VPS hosts mature SIDIX/Ixonomic/Mighantect ecosystem
- **Found:** Host Ollama (PID 106258) is PRODUCTION for SIDIX brain_qa — DO NOT STOP
- **Fixed:** Letta isolated to own database (`letta_db`) with pgvector extension
- **Fixed:** Removed obsolete `version:` from docker-compose.yml
- **Fixed:** Ollama healthcheck removed (image lacks curl/wget)
- **Fixed:** Letta depends_on simplified (no service_healthy condition)
- **Security fix:** Swap resized 4 GB → 8 GB
- **Security fix:** UFW rule 5432 (PostgreSQL public) removed
- **Audit:** Complete VPS ecosystem map created — `docs/VPS_ECOSYSTEM_MAP.md`

**TODO:**
- Add A record: studio → 72.62.125.6
- Setup RunPod account + $50 deposit
- Day 3–4: FastAPI scaffold, auth, migrations
- Decision needed: Caddy vs nginx reverse proxy strategy

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
| R21 | Break existing SIDIX/Ixonomic apps | NEVER touch `/opt/sidix/`, `/var/www/ixonomic/`, or host systemd services. |
| R22 | Caddy vs nginx port conflict | Caddy CANNOT bind 80/443. Nginx aaPanel owns them. See Section 9. |
| R23 | Accidentally use host Redis/PG | MiganCore MUST use container hostnames (`redis:6379`, `postgres:5432`), never `localhost`. |
| R24 | Dual Ollama RAM pressure | Host Ollama (SIDIX) + container Ollama (MiganCore) = ~10 GB when both loaded. Monitor. |

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
| VPS ecosystem map? | `docs/VPS_ECOSYSTEM_MAP.md` |
| VPS setup script? | `scripts/day1-setup.sh` |

---

## 9. VPS ECOSYSTEM AWARENESS (CRITICAL — Multi-Agent Safety)

**This VPS is SHARED.** MiganCore lives alongside SIDIX, Ixonomic, and Mighantect. One mistake breaks production apps.

### 🚫 FORBIDDEN ZONES (Never Touch)
| Path | Owner | Why |
|------|-------|-----|
| `/opt/sidix/` | SIDIX AI | brain_qa, Raudah, Qalb, LoRA adapters |
| `/var/www/ixonomic/` | Ixonomic | Banking, fintech, 10+ microservices |
| `/www/server/panel/` | aaPanel | Hosting control panel core |
| `/etc/nginx/sites-enabled/` | aaPanel | All existing website vhosts |
| `/root/sidix/` | SIDIX | Deploy scripts, ecosystem configs |
| `/var/lib/postgresql/14/` | Host PG14 | SIDIX/aaPanel database |

### 🚫 FORBIDDEN PROCESSES (Never Stop)
| Process | PID / Service | Who Uses It |
|---------|--------------|-------------|
| Host Ollama | `ollama.service` (PID ~106258) | SIDIX brain_qa — RAG inference |
| Host Redis | `redis-server.service` (PID ~1369289) | Mighantect gateway + others |
| Host Postgres | `postgresql@14-main` (PID ~1329833) | SIDIX/aaPanel |
| nginx | aaPanel | All websites (80/443) |
| MariaDB | aaPanel | Ixonomic + aaPanel apps |
| Any PM2 process | `pm2 list` | 20+ production Node.js apps |

### ✅ MIGANCORE ONLY ZONE
| Path | Purpose |
|------|---------|
| `/opt/ado/` | The ONLY working directory for MiganCore |
| `/opt/ado/docker-compose.yml` | Stack definition |
| `/opt/ado/data/` | Container volumes (postgres, ollama, qdrant, redis, caddy) |
| `/etc/ado/keys/` | JWT keys |
| `tiranyx/migancore` | The ONLY GitHub repo for core engine |

### 🔗 Caddy vs Nginx Warning
**nginx aaPanel owns ports 80 and 443.** Caddy container in MiganCore docker-compose.yml **cannot start** as-is because of port conflict. Before starting Caddy, you MUST:
1. Either remove Caddy from compose and use nginx aaPanel for reverse proxy
2. Or reconfigure Caddy to listen on alternate ports (8080/8443) and nginx forwards to it
3. See `docs/VPS_ECOSYSTEM_MAP.md` Section 7 for full decision analysis

### 🧠 Memory Awareness
When MiganCore Ollama loads Qwen 7B (~5 GB) alongside existing host Ollama (~5.4 GB), total Ollama RAM becomes ~10.5 GB. With all other services, projected total VPS usage: **15–18 GB / 31 GB**. Still safe, but monitor with `docker stats` and `free -h`.

---

> **"The seed is patient. The breeder will come."**

---

> **"The seed is patient. The breeder will come."**
