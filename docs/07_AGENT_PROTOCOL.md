# AGENT PROTOCOL — Mighan Ecosystem
**Version:** 1.0
**Purpose:** Mencegah context loss dan duplikasi kerja antar AI coding agents
**WAJIB DIBACA sebelum memulai task apapun**

---

## 1. AGENT TYPES & RESPONSIBILITIES

| Agent Role | Tools | Responsibilities | Branches |
|---|---|---|---|
| **DevOps Agent** | bash, docker, server | Infrastructure, CI/CD, deployment, monitoring | `devops/*` |
| **Backend Agent** | Python, FastAPI, SQL | API endpoints, LangGraph, Celery, auth | `backend/*` |
| **Core Agent** | Python, LangGraph | Memory system, Letta integration, LLM calls | `core/*` |
| **Training Agent** | Python, RunPod API | Dataset prep, fine-tuning, eval, model versioning | `training/*` |
| **Research Agent** | Python, ArXiv API | Paper ingestion, KG building, Sidixlab pipeline | `research/*` |
| **QA Agent** | Python, pytest | Test suites, integration tests, benchmarks | `qa/*` |
| **Docs Agent** | Markdown, HTML | Documentation, README, changelogs | `docs/*` |

---

## 2. ONBOARDING PROTOCOL (WAJIB untuk setiap AI Agent baru)

Setiap AI coding agent yang baru mulai bekerja di proyek ini **HARUS** mengikuti langkah berikut:

### Step 1: Baca Dokumen Konteks (5 menit)
```
1. /docs/01_SOUL.md          — Identitas proyek & Core Brain
2. /docs/02_VISION.md        — Northstar dan visi
3. /docs/03_PRD.md           — Product requirements
4. /docs/04_ARCHITECTURE.md  — Arsitektur teknis
5. /docs/05_ERD_SCHEMA.md    — Database schema
6. /docs/07_AGENT_PROTOCOL.md — INI DOKUMEN (kamu sedang baca ini)
```

### Step 2: Cek Status Proyek
```bash
# Cek git log 10 commit terakhir
git log --oneline -10

# Cek branch aktif
git branch -a

# Cek DAILY_LOG hari ini
cat /docs/logs/daily/$(date +%Y-%m-%d).md

# Cek BLOCKERS aktif
grep -A 5 "BLOCKED" /docs/logs/daily/$(date +%Y-%m-%d).md
```

### Step 3: Cek Context File
```bash
# Context file adalah "memori pendek" proyek
cat /docs/CONTEXT.md
```

### Step 4: Claim Task
```bash
# Cek task yang available
cat /docs/TASK_BOARD.md | grep "⬜ OPEN"

# Claim task (ubah ke "🔵 IN PROGRESS: [Agent Name]")
# Edit /docs/TASK_BOARD.md
```

### Step 5: Start Work
```bash
# Buat branch
git checkout -b [agent-type]/[task-name]

# Mulai kerja. Update CONTEXT.md jika ada keputusan penting.
```

---

## 3. CONTEXT FILE FORMAT (/docs/CONTEXT.md)

File ini adalah "RAM" proyek — selalu up-to-date, ringkas, actionable.

```markdown
# CONTEXT.md — ADO Project Live State
**Last Updated:** [TIMESTAMP] by [Agent/Human]

## CURRENT STATUS
Sprint: Week [N], Day [N]
Active Milestone: [milestone name]

## WHAT'S WORKING ✅
- [component]: [what works]
- [component]: [what works]

## WHAT'S IN PROGRESS 🔵
- [component]: [what's being built] — Owner: [Agent]
- [component]: [what's being built] — Owner: [Agent]

## WHAT'S BLOCKED 🔴
- [task]: [why blocked] — needs: [what's needed]

## RECENT DECISIONS (last 7 days)
- [date]: [decision] — [reason]
- [date]: [decision] — [reason]

## KNOWN ISSUES
- [issue]: [description] — [workaround if any]

## NEXT PRIORITY
1. [task]
2. [task]
3. [task]

## ENVIRONMENT STATE
- Ollama: [running/stopped] — Model: [model name]
- Postgres: [running/stopped] — Last migration: [date]
- Redis: [running/stopped]
- Qdrant: [running/stopped] — Collections: [list]
- Letta: [running/stopped]
- Core Brain agent_id: [uuid]
- Current active model_version: [version_tag]
- RunPod balance: $[amount]
```

---

## 4. DAILY LOG FORMAT (/docs/logs/daily/YYYY-MM-DD.md)

```markdown
# Daily Log — [DATE]

## STARTED
- [time] [agent]: [task description]
- [time] [agent]: [task description]

## COMPLETED
- [time] [agent]: [task] — [commit hash]
- [time] [agent]: [task] — [commit hash]

## DECISIONS
- [decision]: [reason] — [impact on architecture]

## BLOCKED
- [task]: [reason] — [who/what can unblock]

## METRICS
- API calls: N
- Ollama tokens processed: N
- RAM peak: N GB
- Errors: N (see [link])

## TOMORROW'S PRIORITIES
1. [task]
2. [task]
3. [task]
```

---

## 5. TASK BOARD FORMAT (/docs/TASK_BOARD.md)

```markdown
# TASK BOARD

## 🔴 CRITICAL (do now)
- [ ] TASK-001: [description] | Owner: [agent] | ETA: [hours]

## 🟡 HIGH (this week)
- [ ] TASK-002: [description] | Owner: [agent] | Depends: TASK-001

## 🟢 NORMAL (next)
- [ ] TASK-003: [description]

## ✅ DONE
- [x] TASK-000: [description] | Done: [date] | PR: [link]

## 🔵 IN PROGRESS
- TASK-001: [description] | Claimed by: Backend Agent | Started: [time]
```

---

## 6. ANTI-DUPLICATION PROTOCOL

### 6.1 Before Creating Any File
```bash
# Search if similar file exists
find . -name "*.py" | xargs grep -l "[function/class name]"
git grep "[function name]"
```

### 6.2 Before Implementing Any Feature
```bash
# Check if already implemented
grep -r "[feature keyword]" ./api/
grep -r "[feature keyword]" ./core/
```

### 6.3 Before Adding Dependencies
```bash
# Check requirements.txt
cat requirements.txt | grep [package]
# Only add if genuinely new
```

### 6.4 Database Changes
```
RULE: NEVER modify tables directly in production
ALWAYS: Create new Alembic migration file
FORMAT: alembic revision --autogenerate -m "add_column_X_to_agents"
ALWAYS: Test migration on dev first
```

---

## 7. CODE CONVENTIONS

### 7.1 File Structure
```
/api
  /routers         — FastAPI route handlers
  /services        — Business logic
  /models          — Pydantic schemas + SQLAlchemy models
  /agents          — LangGraph agent definitions
  /tools           — Tool implementations
  /workers         — Celery task definitions
  /memory          — Letta + Qdrant memory utilities
  /utils           — Shared utilities
/training          — Training scripts
/research          — Research pipeline (Sidixlab)
/docs              — All documentation (this folder)
/migrations        — Alembic migration files
/tests             — Test suites
/scripts           — Operational scripts (backup, monitoring)
```

### 7.2 Naming Conventions
```python
# Agents: snake_case with _agent suffix
core_brain_agent = ...
code_specialist_agent = ...

# Tools: snake_case verbs
def web_search(query: str) -> str: ...
def spawn_agent(config: AgentConfig) -> str: ...

# Endpoints: /v1/resource/action
# Tables: plural snake_case (agents, conversations, messages)
# Columns: snake_case (tenant_id, created_at)
```

### 7.3 Error Handling
```python
# ALWAYS use structured errors
class ADOError(Exception):
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code  # e.g., "AGENT_NOT_FOUND", "QUOTA_EXCEEDED"
        self.message = message
        self.details = details or {}

# NEVER swallow exceptions silently
# ALWAYS log before re-raising
```

### 7.4 Logging
```python
import structlog
logger = structlog.get_logger()

# ALWAYS include context
logger.info("agent.spawned", agent_id=agent_id, tenant_id=tenant_id, parent_id=parent_id)
logger.error("tool.failed", tool="web_search", error=str(e), query=query)
```

---

## 8. DEPLOYMENT PROTOCOL

### 8.1 Staging (every PR)
```bash
# 1. Run tests
pytest tests/ -v

# 2. Check no secrets in code
git diff HEAD | grep -E "(password|secret|api_key|token)" | grep "^+"

# 3. Check no hardcoded IPs
git diff HEAD | grep -E "\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"

# 4. Merge to main only if all checks pass
```

### 8.2 Production Deployment
```bash
# Auto-triggered by GitHub Actions on push to main
# Steps in .github/workflows/deploy.yml:
# 1. Test
# 2. Build Docker images
# 3. SSH to VPS: docker compose pull && docker compose up -d
# 4. Health check: curl https://api.mighan.com/health
# 5. Notify if failed
```

### 8.3 Model Hot-Swap Protocol
```bash
# 1. New GGUF downloaded to /data/ollama/models/
# 2. Create Modelfile
# 3. ollama create mighan-v02 -f Modelfile
# 4. Run identity test:
python scripts/identity_test.py --model mighan-v02
# 5. If score > 0.85: activate
# 6. If score < 0.85: rollback, log failure, investigate
```

---

## 9. COMMUNICATION PROTOCOL (Human ↔ AI Agent)

### 9.1 When to Pause and Ask Human
AI agents MUST stop and check with human when:
- A decision will affect architecture permanently (new tables, new services)
- Cost will exceed $5 on RunPod in single operation
- Security-relevant changes (auth, encryption, RLS)
- Feature removes existing functionality
- Uncertainty is high and 2 approaches have very different implications

### 9.2 When to Proceed Autonomously
AI agents CAN proceed without asking when:
- Implementation is within clearly scoped task
- Refactoring that doesn't change behavior
- Bug fixes with clear root cause
- Documentation updates
- Test writing

### 9.3 Handoff Format
When an AI agent completes work and hands off:
```markdown
## HANDOFF NOTE — [Agent] → [Next Agent]
**Completed:**
- [what was done] — [commit hash]

**State Left In:**
- [file/service] is [state]

**Next Agent Must:**
1. [critical first step]
2. [second step]

**Watch Out For:**
- [gotcha 1]
- [gotcha 2]

**Context Update:**
- Updated CONTEXT.md with [what]
```

---

## 10. RUNPOD PROTOCOL ($50 BUDGET)

### 10.1 Before Starting Any RunPod Job
```
□ Check current balance in RunPod dashboard
□ Estimate cost: duration × $/hr
□ Document in training_runs table: expected cost
□ Never start a job > $10 without human approval
```

### 10.2 Job Configuration Template
```python
# ALWAYS use Community Cloud (cheapest)
# ALWAYS set max runtime to prevent runaway costs
pod_config = {
    "gpu_type": "NVIDIA GeForce RTX 4090",
    "cloud_type": "COMMUNITY",  # NOT SECURE
    "container_disk_size": 50,  # GB
    "max_duration": 600,  # minutes = 10 hours max
    "template": "runpod/pytorch:2.4.0-py3.11-cuda12.1.1-devel-ubuntu22.04"
}
```

### 10.3 Cost Tracking
```
Every RunPod job → update training_runs.cost_usd when done
Weekly: total spend tracked in /docs/logs/budget.md
If budget remaining < $15: pause new training runs, report to human
```
