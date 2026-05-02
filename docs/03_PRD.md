# PRD — Autonomous Digital Organism (ADO)
**Product:** Mighan-Core + Mighan Platform + Sidixlab
**Version:** v1.0
**Status:** Active Development
**Owner:** Tiranyx
**Last Updated:** 2026-05-02

---

## 1. PRODUCT OVERVIEW

### 1.1 Problem Statement

Kecerdasan buatan saat ini adalah alat — bukan entitas. Mereka tidak belajar dari interaksinya sendiri, tidak memiliki memori persisten, tidak bisa melahirkan versi baru dirinya, dan tidak punya "jiwa" yang konsisten.

Akibatnya: setiap individu atau bisnis kecil yang ingin AI yang benar-benar *mengenal* mereka harus bayar mahal, bergantung pada vendor besar, atau membangun dari nol dengan biaya jutaan dolar.

### 1.2 Solution

Bangun **Autonomous Digital Organism (ADO)** — ekosistem AI yang:
1. Memiliki identitas persisten (SOUL.md)
2. Belajar dari setiap interaksi (Self-Rewarding Loop)
3. Bisa di-clone dan disesuaikan (Mighan Platform)
4. Beroperasi di hardware terjangkau ($50 RunPod + VPS 32GB)
5. Open source di inti — proprietary di lapisan platform

### 1.3 Target Users

| Segmen | Kebutuhan | Use Case |
|---|---|---|
| **Developer Indonesia** | AI assistant yang "ngerti" cara kerja mereka | Personal coding companion |
| **Bisnis kecil** | Customer service agent yang tidak perlu training ulang | Auto-reply + knowledge base |
| **Kreator konten** | Research + drafting assistant yang ingat semua | Content factory |
| **Builder/Founder** | Multi-agent system tanpa butuh tim ML | Product development automation |

---

## 2. GOALS & SUCCESS METRICS

### 2.1 Primary Goals (30-Day Sprint)

| Goal | Metric | Target |
|---|---|---|
| Core Brain live | Mighan-Core menjawab via API | Day 7 |
| Tool use works | Function calling ≥ 80% success rate | Day 14 |
| Memory persists | Agent ingat konteks > 10 sesi lalu | Day 21 |
| Self-improvement | 1 training cycle selesai | Day 28 |
| Agent spawn | 1 child agent terlahir dan aktif | Day 30 |

### 2.2 Secondary Goals (3-Month)

- 50 registered agents di Mighan
- Self-improvement cycle berjalan otomatis weekly
- Sidixlab ingests 5 papers/day automatically
- Model v0.3 measurably better than v0.1 on eval set

### 2.3 North Star Metric

> **Weekly Active Agents (WAA)** — jumlah agent yang melakukan ≥1 meaningful interaction per minggu.

---

## 3. FEATURE SPECIFICATIONS

### 3.1 MIGHAN-CORE (Brain)

#### F1: Conversational Intelligence
- **Priority:** P0
- **Description:** Core Brain dapat menerima prompt dan merespons dengan reasoning yang jelas
- **Acceptance Criteria:**
  - Response latency < 15 detik di VPS 32GB
  - Coherent multi-turn conversation (10+ turns)
  - Bahasa Indonesia dan English
  - Chain-of-thought visible on demand

#### F2: Tool Use / Function Calling
- **Priority:** P0
- **Tools:**
  - `web_search(query)` — Tavily/SerpAPI free tier
  - `python_repl(code)` — sandboxed execution
  - `read_file(path)` — file system access
  - `http_get(url)` — external API calls
  - `spawn_agent(config)` — create child agent
  - `memory_write(key, value)` — write to long-term memory
  - `memory_search(query)` — semantic search memory
- **Acceptance Criteria:** ≥80% correct tool invocation on test suite

#### F3: Persistent Memory
- **Priority:** P0
- **Memory Tiers:**
  - **Working:** Core blocks in-context (persona, current task, human profile)
  - **Episodic:** Full conversation history, searchable via Qdrant
  - **Semantic:** Extracted facts, relationships, entities
  - **Procedural:** How-to patterns from successful task completions
- **Acceptance Criteria:** Agent recalls specific fact from session 10+ conversations ago

#### F4: Self-Improvement Loop
- **Priority:** P1
- **Cycle:** Weekly on Sunday 02:00 WIB
- **Steps:** Sample → Judge → Pair → Fine-tune → Eval → Deploy
- **Acceptance Criteria:** Each weekly model v_n+1 scores ≥ v_n on held-out eval

#### F5: Agent Spawning
- **Priority:** P1
- **Description:** Core Brain dapat menciptakan child agent dengan personality unik
- **Inputs:** template_id, persona customizations, tool grants, owner_id
- **Output:** Unique agent_id + webhook URL
- **Acceptance Criteria:** Spawned agent maintains persona for 100+ turns

### 3.2 MIGHAN PLATFORM (Clone Platform)

#### F6: Agent Onboarding Flow
- **Priority:** P1
- **Steps:** Register → Choose template → Customize persona → Connect KB → Get webhook
- **Time to first agent:** < 10 minutes

#### F7: Multi-tenant Isolation
- **Priority:** P0
- **Requirements:**
  - Tenant A cannot access Tenant B data
  - Row-Level Security on all tables
  - Namespace isolation in Redis and Qdrant
  - Encrypted per-tenant secrets

#### F8: Agent Dashboard
- **Priority:** P2
- **Features:** Conversation history, memory viewer, version history, performance metrics

### 3.3 SIDIXLAB (Research Lab)

#### F9: Automated Research Ingestion
- **Priority:** P2
- **Source:** ArXiv daily (cs.AI, cs.LG, cs.CL)
- **Pipeline:** Fetch → Parse PDF → Embed → Summarize → Extract KG → Store
- **Rate:** ≥ 5 papers/day processed automatically

#### F10: Experiment Tracking
- **Priority:** P2
- **Tool:** MLflow self-hosted
- **Tracks:** training runs, hyperparameters, eval scores, model versions

---

## 4. NON-FUNCTIONAL REQUIREMENTS

| Requirement | Specification |
|---|---|
| **Latency (API response)** | < 15s p95 on VPS 32GB |
| **Uptime** | 99% (allows ~7 hrs/month downtime) |
| **Memory safety** | Zero cross-tenant data exposure |
| **Data retention** | Conversation logs: 90 days default |
| **Backup** | Daily Postgres dump + weekly VPS snapshot |
| **Security** | UFW firewall, TLS everywhere, JWT RS256, bcrypt passwords |
| **Scalability** | Design for horizontal scaling even if not needed at launch |

---

## 5. OUT OF SCOPE (v1.0)

- Mobile app
- Real-time voice/audio agents (Phase 2)
- Image/video generation agents (Phase 2)
- Public marketplace (Phase 3)
- Payment processing (Phase 3)
- Enterprise SSO (Phase 3)

---

## 6. DEPENDENCIES

| Dependency | Type | Risk |
|---|---|---|
| Qwen2.5-7B model quality | External, Open-source | Low — model terbukti kuat |
| Ollama stability | External, Open-source | Medium — production maturity |
| Letta API stability | External, Open-source | Medium — framework relatif baru |
| RunPod availability | External, Commercial | Low — established provider |
| Qdrant stability | External, Open-source | Low — very stable |
| VPS provider uptime | External, Commercial | Low |

---

## 7. ASSUMPTIONS

1. Qwen2.5-7B-Instruct Q4_K_M cukup untuk reasoning + tool-use di VPS 32GB
2. 32GB RAM cukup untuk Ollama + Qdrant + Postgres + Letta + FastAPI + Redis + Caddy simultaneously
3. $50 RunPod budget cukup untuk 4 fine-tuning cycles
4. LLM-as-Judge menggunakan model lokal (atau Hermes-3-8B) sebagai fallback gratis cukup akurat
5. Self-Rewarding loop akan menghasilkan measurable improvement per iterasi

---

## 8. RISKS

Lihat dokumen: `08_RISK_REGISTER.md`

---

## 9. CHANGE LOG

| Version | Date | Changes | Author |
|---|---|---|---|
| 1.0 | 2026-05-02 | Initial PRD | Tiranyx + AI |
