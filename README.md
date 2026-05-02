# MiganCore — Autonomous Digital Organism

[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![Status](https://img.shields.io/badge/status-seed-orange.svg)](https://migancore.com)

> **Open Core Engine for Self-Evolving AI Agents**

MiganCore adalah inti dari ekosistem Tiranyx — sebuah *Autonomous Digital Organism* yang bisa berorkestrasi, belajar dari setiap interaksi, memperbaiki dirinya sendiri setiap minggu, dan melahirkan child agents dengan kepribadian unik.

---

## 🧬 Apa yang Dibangun

| Aspek | Detail |
|---|---|
| **Core Brain** | Qwen2.5-7B-Instruct via Ollama, orkestrasi LangGraph |
| **Memory** | Letta (core blocks) + Qdrant (semantic) + PostgreSQL (episodic) |
| **Self-Improvement** | Unsloth + QLoRA + SimPO, training mingguan otomatis |
| **Tools** | Web search, Python REPL, file read, HTTP, agent spawn |
| **Multi-tenant** | PostgreSQL RLS + JWT RS256 + per-tenant isolation |
| **API** | FastAPI + Celery + Redis Streams |

---

## 🗺️ Arsitektur

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  sidixlab   │     │   mighan    │     │   tiranyx   │
│  .com       │     │   .com      │     │   .com      │
│  (Research) │     │  (Platform) │     │ (Governance)│
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           │
              ┌────────────▼────────────┐
              │     API GATEWAY         │
              │   (FastAPI + Caddy)     │
              └────────────┬────────────┘
                           │
    ┌──────────┬───────────┼───────────┬──────────┐
    │          │           │           │          │
┌───▼───┐ ┌────▼────┐ ┌───▼───┐ ┌────▼────┐ ┌───▼────┐
│LangGraph│ │ Letta   │ │ Celery│ │ Qdrant  │ │ Postgres│
│Director │ │ Memory  │ │Workers│ │ Vectors │ │ +pgvector│
└───┬────┘ └────┬────┘ └───┬───┘ └────┬────┘ └───┬────┘
    │           │          │          │          │
    └───────────┴──────────┴──────────┴──────────┘
                           │
                    ┌──────▼──────┐
                    │   Ollama    │
                    │ Qwen2.5-7B  │
                    └─────────────┘
```

---

## 📁 Struktur Repo

```
migancore/
├── core/                   # Core Brain LangGraph engine
│   ├── brain.py            # Main orchestrator
│   ├── state.py            # AgentState TypedDict
│   └── nodes/              # intent_classifier, planner, reasoner...
├── memory/                 # Letta + Qdrant integration
│   ├── letta_client.py
│   ├── qdrant_client.py
│   └── embedder.py         # BGE-M3 via fastembed
├── tools/                  # Tool registry + implementations
│   ├── web_search.py
│   ├── python_repl.py
│   └── spawn_agent.py
├── training/               # Self-improvement pipeline
│   ├── collector.py        # Feedback aggregation
│   ├── judge.py            # LLM-as-Judge
│   ├── train_simpo.py      # SimPO training script
│   └── evaluator.py        # Identity + quality eval
├── api/                    # FastAPI endpoints
│   ├── routers/            # Route handlers
│   ├── services/           # Business logic
│   ├── models/             # Pydantic + SQLAlchemy
│   ├── agents/             # LangGraph definitions
│   ├── tools/              # Tool bindings
│   └── workers/            # Celery task definitions
├── migrations/             # Alembic migration files
├── docs/                   # Semua dokumentasi
│   ├── 01_SOUL.md          # Core identity protocol
│   ├── 02_VISION_NORTHSTAR_FOUNDER_JOURNAL.md
│   ├── 03_PRD.md
│   ├── 04_ARCHITECTURE.md
│   ├── 05_ERD_SCHEMA.md
│   ├── 06_SPRINT_ROADMAP.md
│   ├── 07_AGENT_PROTOCOL.md
│   └── 08_RISK_TRAINING_CONTEXT_BUDGET.md
├── scripts/                # Operational scripts
├── tests/                  # pytest suites
├── docker-compose.yml      # Self-host stack
├── LICENSE                 # Apache 2.0
└── README.md
```

---

## 🚀 Quick Start (Self-Host)

> **Prasyarat:** VPS dengan 32GB RAM, 8 core, 400GB disk. Docker + Docker Compose.

```bash
# 1. Clone repo
git clone https://github.com/tiranyx/migancore.git
cd migancore

# 2. Setup environment
cp .env.example .env
# Edit .env — isi password dan API keys

# 3. Generate JWT keypair
mkdir -p /etc/ado/keys
openssl genrsa -out /etc/ado/keys/private.pem 2048
openssl rsa -in /etc/ado/keys/private.pem -pubout -out /etc/ado/keys/public.pem

# 4. Jalankan stack
docker compose up -d

# 5. Pull model
ollama pull qwen2.5:7b-instruct-q4_K_M

# 6. Test
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Halo, Mighan-Core!"}'
```

---

## 📜 Lisensi

**Apache License 2.0**

Kamu boleh:
- ✅ Pakai secara komersial
- ✅ Modifikasi dan distribusikan
- ❌ Harus menyertakan attribution
- ❌ Tidak boleh klaim paten

Lihat [LICENSE](LICENSE) untuk detail lengkap.

---

## 🌐 Ekosistem

| Repo | Visibility | License | Isi |
|---|---|---|---|
| `tiranyx/migancore` | **Public** | Apache 2.0 | Core engine (repo ini) |
| `tiranyx/migancore-platform` | **Private** | Proprietary | Hosted service, billing, dashboard |
| `tiranyx/migancore-community` | **Public** | MIT | Templates, plugins, datasets |

---

## 🤝 Contributing

Kami menerima kontribusi! Lihat [docs/07_AGENT_PROTOCOL.md](docs/07_AGENT_PROTOCOL.md) untuk protokol kerja dan [docs/06_SPRINT_ROADMAP.md](docs/06_SPRINT_ROADMAP.md) untuk prioritas saat ini.

---

## 🔗 Links

- 🌐 **Website:** [migancore.com](https://migancore.com)
- 🔬 **Research Lab:** [sidixlab.com](https://sidixlab.com)
- 🏠 **Project Owner:** [tiranyx.com](https://tiranyx.com)

---

> *"Setiap manusia yang punya visi berhak punya organisme digital yang tumbuh bersamanya."*
