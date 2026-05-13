# MiganCore — Autonomous Digital Organism

[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![Status](https://img.shields.io/badge/status-seed-orange.svg)](https://migancore.com)

> **Open Core Engine for Self-Evolving AI Agents**

**Current North Star Ping (M1.6 Dev Organ):** MiganCore sedang diarahkan menjadi
ADO yang bukan hanya auto-training model, tapi juga bisa melakukan
self-improvement terkontrol atas tubuhnya sendiri: observe -> diagnose ->
propose -> sandbox patch -> test -> iterate -> validate -> promote -> monitor
-> learn. Baca `docs/SELF_IMPROVEMENT_NORTHSTAR.md`,
`docs/M16_DEV_ORGAN_PROGRESS_2026-05-14.md`, dan `api/services/dev_organ.py`
sebelum mengubah roadmap atau autonomy behavior.

**Cognitive Synthesis Ping:** MiganCore must also act as the bridge between
Fahmi's non-technical vision-language and engineering reality: infer intent,
name the hidden concept, synthesize a strategy, map it to architecture, then
execute the first safe slice. See `docs/COGNITIVE_SYNTHESIS_DOCTRINE.md`.

MiganCore adalah **pusat pengembangan dan produksi** ekosistem Tiranyx — sebuah *Autonomous Digital Organism* yang bisa berorkestrasi, belajar dari setiap interaksi, memperbaiki dirinya sendiri setiap minggu, dan melahirkan child agents dengan kepribadian unik.

**Semua development berlangsung di `migancore.com`.** Domain lain (`sidixlab.com`, `mighan.com`, `tiranyx.com`) adalah **consumer/distribution channel** yang mengakses produk ini via API.

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
┌─────────────────────────────────────────────────────────────────────┐
│                     MIGANCORE.COM — CENTRAL HUB                     │
│              (Development + Production + Core Services)             │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │ api.        │  │ app.        │  │ lab.        │  │ studio.   │ │
│  │ migancore   │  │ migancore   │  │ migancore   │  │ migancore │ │
│  │ (API GW)    │  │ (Dashboard) │  │ (Observab.) │  │ (Training)│ │
│  └──────┬──────┘  └─────────────┘  └─────────────┘  └───────────┘ │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    CORE SERVICE LAYER                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │   │
│  │  │LangGraph │  │  Letta   │  │  Celery  │  │  Qdrant    │  │   │
│  │  │Director  │  │ Memory   │  │ Workers  │  │  Vectors   │  │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │   │
│  │       │             │             │              │         │   │
│  │  ┌────┴─────────────┴─────────────┴──────────────┴──────┐  │   │
│  │  │              POSTGRESQL + REDIS + OLLAMA              │  │   │
│  │  │         (Data + Cache + Qwen2.5-7B Inference)         │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ API Calls
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼─────┐        ┌──────▼──────┐       ┌─────▼──────┐
   │sidixlab  │        │  mighan     │       │  tiranyx   │
   │.com      │        │  .com       │       │  .com      │
   │(Research │        │  (Platform  │       │  (Project  │
   │Consumer) │        │  Consumer)  │       │  Owner)    │
   └──────────┘        └─────────────┘       └────────────┘
```

**Penjelasan:**
- **migancore.com** = Satu-satunya tempat development & deployment. Semua backend, model, memory, dan training berjalan di sini.
- **sidixlab.com** = Consumer untuk research lab. Frontend/UI yang consume `api.migancore.com`.
- **mighan.com** = Consumer untuk clone platform. Frontend/UI yang consume `api.migancore.com`.
- **tiranyx.com** = Consumer untuk project governance. Frontend/UI yang consume `api.migancore.com`.

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

| Repo | Visibility | License | Peran |
|---|---|---|---|
| `tiranyx/migancore` | **Public** | Apache 2.0 | **Central Hub** — engine, API, training, memory |
| `tiranyx/migancore-platform` | **Private** | Proprietary | Dashboard, billing, analytics UI (consumer of migancore) |
| `tiranyx/migancore-community` | **Public** | MIT | Templates, plugins, datasets |

**Consumer Channels** (mengakses `api.migancore.com`):
- 🔬 **sidixlab.com** — Research lab distribution
- 🧬 **mighan.com** — Clone platform distribution
- 🏠 **tiranyx.com** — Project owner / governance distribution

---

## 🤝 Contributing

Kami menerima kontribusi! Lihat [docs/07_AGENT_PROTOCOL.md](docs/07_AGENT_PROTOCOL.md) untuk protokol kerja dan [docs/06_SPRINT_ROADMAP.md](docs/06_SPRINT_ROADMAP.md) untuk prioritas saat ini.

---

## 🔗 Links

- 🌐 **Development Hub:** [migancore.com](https://migancore.com)
- 🔬 **Research Consumer:** [sidixlab.com](https://sidixlab.com)
- 🧬 **Platform Consumer:** [mighan.com](https://mighan.com)
- 🏠 **Project Owner:** [tiranyx.com](https://tiranyx.com)

---

> *"Setiap manusia yang punya visi berhak punya organisme digital yang tumbuh bersamanya."*
