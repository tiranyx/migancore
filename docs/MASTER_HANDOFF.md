# MASTER HANDOFF — MiganCore Project
**Version:** 1.0  
**Last Updated:** 2026-05-03 by Kimi Code CLI  
**Status:** Day 0 → Day 1 Transition  
**Critical Rule:** AGENT YANG MELANJUTKAN WAJIB MEMBACA DOKUMEN INI SEBELUM MULAI KERJA.

---

## 1. EXECUTIVE SUMMARY

**MiganCore** adalah Autonomous Digital Organism (ADO) — ekosistem AI agent yang bisa:
1. **Orkestrasi multi-agent** — Core Brain mengarahkan specialist agents
2. **Self-learning** — Belajar dari setiap interaksi, improve diri setiap minggu
3. **Self-replicating** — Melahirkan child agents dengan persona unik

**Model Bisnis:** Open Core (seperti GitLab, Supabase)
- Engine open source (Apache 2.0)
- Platform monetized (private)
- Community ecosystem (MIT)

**Semua development berlangsung di `migancore.com`.**  
`sidixlab.com`, `mighan.com`, `tiranyx.com` adalah **consumer/distribution channel** yang mengakses API via `api.migancore.com`.

---

## 2. ARSITEKTUR FINAL (WAJIB DIPAHAMI)

### 2.1 Central Hub Model

```
┌─────────────────────────────────────────┐
│         MIGANCORE.COM (Central Hub)     │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│  │ api.    │ │ app.    │ │ lab.      │ │
│  │ migancore│ │ migancore│ │ migancore │ │
│  │ (API GW)│ │ (Studio)│ │ (Observ)  │ │
│  └────┬────┘ └─────────┘ └───────────┘ │
│       │                                 │
│  ┌────┴────────────────────────────────┐│
│  │  Core: LangGraph + Letta + Ollama   ││
│  │  Data: Postgres + Qdrant + Redis    ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
                    │
                    ▼ api.migancore.com
    ┌───────────────┼───────────────┐
    │               │               │
 sidixlab.com   mighan.com    tiranyx.com
(Research UI)  (Platform UI)  (Gov UI)
```

**JANGAN PERNAH SALAH LAGI:**
- ✅ **migancore.com** = host semua backend, model, memory, training
- ❌ **sidixlab.com** = BUKAN host research lab (hanya UI consumer)
- ❌ **mighan.com** = BUKAN host clone platform (hanya UI consumer)
- ❌ **tiranyx.com** = BUKAN host governance (hanya UI consumer)

### 2.2 Subdomain Assignment

| Subdomain | Service | Port (Internal) | Keterangan |
|---|---|---|---|
| `api.migancore.com` | FastAPI | 8000 | API Gateway untuk semua consumer |
| `app.migancore.com` | Next.js / Dashboard | 3000 | Main management UI |
| `lab.migancore.com` | Langfuse | 3000 | LLM observability & tracing |
| `studio.migancore.com` | MLflow / Training UI | 3000 | Model registry & experiment tracking |
| `migancore.com` | redirect | — | Redirect ke `app.migancore.com` |

### 2.3 Tech Stack

| Layer | Teknologi | Kenapa |
|---|---|---|
| **Model** | Qwen2.5-7B-Instruct Q4_K_M | Function-calling kuat, Apache-2.0, muat 32GB RAM |
| **Inference** | Ollama (llama.cpp) | CPU-optimized, OpenAI-compatible API |
| **Orchestration** | LangGraph | Deterministic state machine, circuit breaker |
| **Memory** | Letta + Qdrant + Postgres | Core blocks + semantic search + relational |
| **Training** | Unsloth + QLoRA + SimPO | 2× cepat, 70% hemat VRAM, no reference model |
| **API** | FastAPI + Celery + Redis | Multi-tenant JWT RS256 + async workers |
| **Infra** | Docker Compose + Caddy | Self-hostable, auto-HTTPS |
| **VPS** | 32GB RAM / 8 Core / 400GB | Exact fit, zero headroom — pakai 8GB swap |

---

## 3. STATUS PROYEK SAAT INI

### 3.1 Yang Sudah Selesai ✅

| # | Item | Detail |
|---|---|---|
| 1 | **Dokumentasi Lengkap** | 8 master docs di `migancore/docs/` |
| 2 | **Open Core Strategy** | 3 repo: migancore (Public/Apache 2.0), migancore-platform (Private), migancore-community (Public/MIT) |
| 3 | **GitHub Repos** | Semua 3 repo created & pushed: [github.com/tiranyx](https://github.com/tiranyx) |
| 4 | **Domain Registered** | `migancore.com` di Hostinger |
| 5 | **DNS Configured** | A records: www, app, api, lab → `72.62.125.6`. Tinggal `studio` |
| 6 | **VPS Active** | IP `72.62.125.6`, 32GB RAM, aaPanel |
| 7 | **Schema Database** | `migrations/init.sql` — full PostgreSQL + pgvector + RLS |
| 8 | **Docker Compose** | Stack lengkap: Ollama, Postgres, Qdrant, Redis, Letta, API, Workers, Langfuse, Caddy |
| 9 | **Caddyfile** | Reverse proxy untuk subdomain migancore.com |
| 10 | **JWT Keygen Script** | `openssl` commands ready |

### 3.2 Yang Sedang Berlangsung 🔵

| # | Item | Blocker |
|---|---|---|
| 1 | **Day 1 VPS Setup** | Butuh eksekusi SSH commands |
| 2 | **RunPod $50 Deposit** | Butuh kartu kredit |

### 3.3 Yang Belum Mulai ⬜

- Day 2: Ollama + First Token
- Day 3-7: API, auth, tools, SOUL integration
- Week 2: LangGraph Director + Memory
- Week 3: Self-learning loop
- Week 4: Training + Agent Spawn

---

## 4. KEPUTUSAN PENTING (JANGAN DIUBAH TANPA DISKUSI)

### 4.1 Arsitektur
1. **migancore.com = central hub.** Domain lain = consumer only.
2. **Single VPS 32GB** untuk Sprint 1. Horizontal scaling di Sprint 2+.
3. **Ollama CPU-only** untuk production. RunPod GPU hanya untuk training burst.

### 4.2 Model & Training
1. **Seed model:** Qwen2.5-7B-Instruct Q4_K_M (tidak boleh ganti tanpa eval)
2. **Teacher model:** Hermes-3-405B atau Llama-3.1-405B. **JANGAN pakai Claude/GPT-4o output untuk training** (melanggar ToS).
3. **Training method:** Unsloth + QLoRA + SimPO. Budget $50 = max 4-6 runs.
4. **Identity preservation:** 50 anchor samples + SOUL.md re-injection + persona consistency test (>0.85 cosine sim).

### 4.3 Legal & Security
1. **Apache 2.0** untuk core engine. **MIT** untuk community. **Proprietary** untuk platform.
2. **Jangan commit secrets** — `.env` di `.gitignore`, JWT keys di `/etc/ado/keys/`.
3. **RLS mandatory** — semua tabel dengan `tenant_id` wajib punya Row-Level Security.
4. **Hard limit RunPod:** Alert human jika balance ≤ $15. Pause jika ≤ $10. Max $10 per job tanpa approval.

### 4.4 Repo Management
1. **migancore** (public) = core engine + docs + docker-compose
2. **migancore-platform** (private) = billing + dashboard + marketplace UI
3. **migancore-community** (public) = templates + tools + datasets

---

## 5. INFRASTRUCTURE DETAIL

### 5.1 VPS Spec
- **Provider:** Hostinger VPS
- **IP:** `72.62.125.6`
- **RAM:** 32GB
- **CPU:** 8 Core
- **Disk:** 400GB
- **Panel:** aaPanel
- **OS:** Ubuntu 22.04 (asumsi)

### 5.2 DNS Records (Hostinger)

| Tipe | Nama | IP | Status |
|---|---|---|---|
| A | `@` | 72.62.125.6 | ✅ Active |
| A | `www` | 72.62.125.6 | ✅ Active |
| A | `api` | 72.62.125.6 | ✅ Active |
| A | `app` | 72.62.125.6 | ✅ Active |
| A | `lab` | 72.62.125.6 | ✅ Active |
| A | `studio` | 72.62.125.6 | ⬜ **TAMBAH INI** |

### 5.3 Memory Budget (32GB)

| Service | RAM | Catatan |
|---|---|---|
| Ollama (7B Q4) | 12 GB | Model ~5GB + KV cache |
| PostgreSQL | 4 GB | Shared buffers |
| Qdrant | 4 GB | Vector index |
| Redis | 2 GB | Streams + Celery |
| Letta | 3 GB | Agent state |
| API + Workers | 4 GB | 3 workers + API |
| Langfuse | 1 GB | Observability |
| OS + Caddy | 2 GB | System overhead |
| **TOTAL** | **32 GB** | ⚠️ Zero headroom — swap 8GB wajib |

### 5.4 Port Allocation

| Port | Service | External? |
|---|---|---|
| 22 | SSH | ✅ (UFW allowed) |
| 80 | HTTP | ✅ (Caddy redirect HTTPS) |
| 443 | HTTPS | ✅ (Caddy auto-TLS) |
| 11434 | Ollama | ❌ (Docker internal only) |
| 5432 | PostgreSQL | ❌ (Docker internal only) |
| 6333 | Qdrant | ❌ (Docker internal only) |
| 6379 | Redis | ❌ (Docker internal only) |
| 8000 | FastAPI | ❌ (Caddy reverse proxy) |
| 8283 | Letta | ❌ (Docker internal only) |

---

## 6. STRUKTUR REPO

### 6.1 migancore (Public)

```
migancore/
├── core/              # LangGraph engine
│   ├── brain.py
│   ├── state.py
│   └── nodes/
├── memory/            # Letta + Qdrant
│   ├── letta_client.py
│   ├── qdrant_client.py
│   └── embedder.py
├── tools/             # Tool implementations
│   ├── web_search.py
│   ├── python_repl.py
│   └── spawn_agent.py
├── training/          # Self-improvement pipeline
│   ├── collector.py
│   ├── judge.py
│   ├── train_simpo.py
│   └── evaluator.py
├── api/               # FastAPI
│   ├── routers/
│   ├── services/
│   ├── models/
│   ├── agents/
│   ├── tools/
│   └── workers/
├── migrations/        # init.sql (full schema)
├── docs/              # 8 master docs + MASTER_HANDOFF.md
├── scripts/           # Operational scripts
│   └── DAY1_VPS_SETUP.md
├── tests/
├── docker-compose.yml
├── Caddyfile
├── .env.example
├── LICENSE (Apache 2.0)
└── README.md
```

### 6.2 migancore-platform (Private)
```
migancore-platform/
├── app/
│   ├── marketplace/
│   ├── dashboard/
│   └── billing/
├── services/
└── README.md (internal only)
```

### 6.3 migancore-community (Public)
```
migancore-community/
├── templates/         # Agent personality templates
├── tools/             # Community tools
├── souls/             # SOUL.md variants
├── datasets/
├── evals/
├── LICENSE (MIT)
└── README.md
```

---

## 7. SPRINT ROADMAP (30-Day)

### Week 1: THE SEED (Day 1–7)
**Goal:** VPS → Ollama → First Token → API Live

| Day | Task | Owner |
|---|---|---|
| 1 | VPS hardening, Docker, swap, JWT keys | DevOps |
| 2 | DNS + Caddy + TLS | DevOps |
| 3 | Ollama + Qwen2.5-7B + benchmark | DevOps |
| 4 | Postgres + FastAPI hello-world + auth | Backend |
| 5 | Tool registry + 3 tools | Backend |
| 6 | SOUL.md integration + identity test | Core |
| 7 | CI/CD + monitoring + backup | DevOps |

### Week 2: THE DIRECTOR (Day 8–14)
**Goal:** Memory + LangGraph + Multi-tenant

| Day | Task | Owner |
|---|---|---|
| 8 | Full Docker stack up | DevOps |
| 9 | Multi-tenant JWT + RLS | Backend |
| 10 | LangGraph Director MVP | Core |
| 11 | Letta memory integration | Core |
| 12 | Qdrant + BGE-M3 embeddings | Core |
| 13 | Celery workers + specialists | Backend |
| 14 | Week 2 integration test | QA |

### Week 3: THE INNOVATOR (Day 15–21)
**Goal:** Self-learning pipeline wired

| Day | Task | Owner |
|---|---|---|
| 15 | Constitution.md + CAI loop | Core |
| 16 | LLM-as-Judge pipeline | Training |
| 17 | Feedback aggregator | Training |
| 18 | Training pipeline scaffold | Training |
| 19 | Specialist agents full | Backend |
| 20 | A/B framework | Backend |
| 21 | Week 3 integration test | QA |

### Week 4: THE BREEDER (Day 22–30)
**Goal:** First training cycle + first clone + demo

| Day | Task | Owner |
|---|---|---|
| 22 | Magpie data generation | Training |
| 23 | First real training run (RunPod) | Training |
| 24 | Model v0.2 deployment | Training |
| 25 | SimPO preference training | Training |
| 26 | Agent spawn endpoint | Backend |
| 27 | Sidixlab research pipeline | Research |
| 28 | Full system test | QA |
| 29 | Documentation + public assets | Docs |
| 30 | Demo + retrospective | Human |

---

## 8. AGENT ONBOARDING CHECKLIST

Agent yang melanjutkan WAJIB:

1. **Baca dokumen ini** (MASTER_HANDOFF.md)
2. **Baca SOUL.md** (`docs/01_SOUL.md`)
3. **Baca Architecture** (`docs/04_ARCHITECTURE.md`)
4. **Cek CONTEXT.md** — status terkini
5. **Cek TASK_BOARD.md** — task yang available
6. **Cek git log** — apa yang sudah dikerjakan
7. **Claim task** — update TASK_BOARD.md
8. **Buat branch** — `git checkout -b [role]/[task-name]`

### 8.1 Anti-Duplication Protocol
```bash
# Sebelum membuat file baru:
find . -name "*.py" | xargs grep -l "[function_name]"
git grep "[feature_keyword]"

# Sebelum menambah dependency:
cat requirements.txt | grep [package]
```

### 8.2 Database Change Protocol
```bash
# NEVER modify tables directly in production
# ALWAYS create Alembic migration:
alembic revision --autogenerate -m "add_column_X_to_agents"
# Test on dev first
```

---

## 9. COMMON PITFALLS (JANGAN TERSesat)

### Pitfall #1: Salah Paham Domain
> "Sidixlab.com adalah host research lab."

**SALAH.** Sidixlab.com hanya frontend consumer. Semua research backend berjalan di `migancore.com/lab`.

### Pitfall #2: Mengganti Model Seed
> "Qwen2.5-7B kurang bagus, ganti ke Llama-3.1-8B."

**JANGAN.** Qwen2.5-7B sudah dipilih karena: function-calling terbaik, Apache-2.0, 32GB RAM exact fit. Ganti model = restart eval dari nol.

### Pitfall #3: Commit Secrets
> "Saya tambahin API key ke .env.example biar mudah."

**JANGAN.** `.env.example` hanya placeholder. Real keys di `.env` (tidak di git). JWT keys di `/etc/ado/keys/`.

### Pitfall #4: Lupa Swap
> "32GB RAM cukup kan? Skip swap aja."

**JANGAN.** 32GB = exact fit dengan **zero headroom**. Swap 8GB adalah safety net. Tanpa swap, OOM = crash semua services.

### Pitfall #5: Training dengan Claude/GPT-4o Output
> "Claude lebih bagus untuk generate training data."

**JANGAN.** Melanggar ToS Anthropic/OpenAI. Gunakan Hermes-3-405B atau Llama-3.1-405B sebagai teacher.

### Pitfall #6: Deploy tanpa RLS
> "RLS ribet, nanti aja pas production."

**JANGAN.** RLS wajib dari Day 1. Multi-tenancy tanpa RLS = data leak.

### Pitfall #7: RunPod Tanpa Budget Check
> "Training butuh 12 jam, gas aja."

**JANGAN.** Max $10 per job tanpa human approval. Alert human jika balance ≤ $15.

---

## 10. RESOURCE & CONTACT

- **GitHub Org:** [github.com/tiranyx](https://github.com/tiranyx)
- **Central Hub:** `migancore.com` (72.62.125.6)
- **API Endpoint:** `https://api.migancore.com`
- **Project Owner:** Fahmi Wol (fahmiwol@gmail.com)
- **VPS Panel:** aaPanel (Hostinger)

---

## 11. CHANGELOG HANDOFF

| Date | Agent | What Changed |
|---|---|---|
| 2026-05-02 | Claude + Gemini | Initial blueprint, 8 master docs created |
| 2026-05-03 | Kimi Code CLI | Repo scaffold, GitHub setup, architecture revision (migancore.com = central hub), DNS config, Day 1 guide |
| 2026-05-03 | ??? | Day 1 VPS provisioning (SSH, Docker, swap, JWT) |

---

> **"Kode bisa dicopy. Yang tidak bisa dicopy adalah ekosistem, reputasi, dan data training yang sudah mature."**
