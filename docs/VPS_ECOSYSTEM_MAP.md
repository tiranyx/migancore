# VPS Ecosystem Map — 72.62.125.6
**Date:** 2026-05-03  
**Purpose:** Complete isolation analysis for MiganCore deployment alongside existing SIDIX/Ixonomic/Mighantect stack  
**Auditor:** Agent (deep investigation)  

---

## 1. Discovery: This VPS is NOT Empty

Before MiganCore Day 1, this VPS already hosted a **mature multi-tenant ecosystem**:

```
VPS 72.62.125.6 (mail.sidixlab.com)
├── aaPanel (hosting control panel)
│   ├── nginx (ports 80, 443, 888, 39206)
│   ├── MariaDB (port 3306, 0.0.0.0)
│   ├── Mail server (Poste.io: 110, 143, 993, 995)
│   └── ~10 websites (abrabriket.com, ixonomic.com, etc.)
│
├── SIDIX AI Ecosystem (Islamic LLM)
│   ├── sidix-brain (brain_qa) → port 8765, uses host Ollama
│   ├── sidix-ui → port 4000
│   ├── sidix-next-ui → port 3200
│   └── LoRA adapter: sidix-lora:latest
│
├── Ixonomic Fintech Suite
│   ├── ixonomic-bank → port 3011
│   ├── ixonomic-api, adm, bag, embed, hud, uts, docs
│   └── galantara-mp → port 3005
│
├── Mighantect 3D
│   └── gateway → port 9797
│
├── Other PM2 Apps
│   ├── abra-website, revolusitani, tiranyx, shopee-gateway
│   └── brangkas-dashboard
│
└── MIGANCORE (NEW — Docker Compose)
    ├── Ollama container (internal:11434)
    ├── Postgres pgvector container (internal:5432)
    ├── Redis container (internal:6379)
    ├── Qdrant container (internal:6333)
    └── Letta container (internal:8283)
```

---

## 2. Critical Finding: Ollama Host Owner = SIDIX brain_qa

### Evidence Chain

| Evidence | Source |
|----------|--------|
| Process | `ollama` (PID 106258), systemd service, user `ollama` |
| Memory | **5.4 GB** (model loaded) |
| Config | `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_KEEP_ALIVE=10m` |
| Consumer | `sidix-brain` (PM2, PID 2400672, port 8765) |
| Model | `qwen2.5:7b` or `sidix-lora:latest` (custom LoRA) |
| Code ref | `/opt/sidix/apps/brain_qa/brain_qa/ollama_llm.py` → `http://localhost:11434` |
| Code ref | `/opt/sidix/brain/raudah/core.py` → `OLLAMA_URL=http://localhost:11434` |
| Logs | `journalctl` shows `/api/tags` polled every minute from 127.0.0.1 |
| .env | `/opt/sidix/.env`: `SIDIX_LLM_BACKEND=ollama`, `OLLAMA_MODEL=qwen2.5:7b` |

### Verdict
**DO NOT STOP host Ollama.** It is production infrastructure for SIDIX brain_qa (Islamic AI RAG system).

---

## 3. Isolation Matrix: MiganCore vs Existing Services

### ✅ SAFE — No Conflict

| Resource | Existing | MiganCore | Isolation Mechanism |
|----------|----------|-----------|---------------------|
| **Postgres** | Host PG 14 (`/system.slice/postgresql@14-main`) | Container pgvector (`ado_network`) | Port not exposed to host. Different engines (PG14 vs PG16+vector). |
| **Redis** | Host redis-server (`127.0.0.1:6379`, systemd) | Container redis (`ado_network`) | Port not exposed to host. Container uses internal Docker IP. |
| **Domain** | sidixlab.com, mighan.com, tiranyx.com, ixonomic.com | migancore.com | DNS A records separate. No overlap. |
| **Docker** | 1 compose (jariyah-hub) | ado_network (172.16.1.0/24) | Separate Docker networks. |
| **Data dir** | `/opt/sidix/`, `/var/www/`, `/root/sidix/` | `/opt/ado/` | Separate filesystem paths. |

### ⚠️ REQUIRES ATTENTION

| Resource | Existing | MiganCore | Issue |
|----------|----------|-----------|-------|
| **Ollama** | Host systemd (port 127.0.0.1:11434, 5.4 GB loaded) | Container (internal:11434, 24 MB idle) | **Dual Ollama** = duplicate RAM when both loaded. Total ~10 GB. Still within 32 GB budget. |
| **Reverse Proxy** | nginx aaPanel (ports 80, 443) | Caddy container (wants 80, 443) | **Caddy CANNOT start** — port conflict. Must integrate with nginx or use alternate ports. |
| **RAM Budget** | Existing apps: ~8–10 GB | MiganCore future: ~6–8 GB | Total projected: ~15–18 GB / 32 GB. Tight but workable with 8 GB swap. |

### 🔴 CRITICAL — Must Resolve Before Production

| Issue | Severity | Details |
|-------|----------|---------|
| **Caddy port conflict** | 🔴 HIGH | nginx already binds 80/443. Caddy container will fail to start. MiganCore HTTPS needs nginx integration. |
| **MariaDB on 0.0.0.0:3306** | 🟡 MEDIUM | Not in UFW, but ideally bind to localhost only. Risk of exposure if UFW misconfigured. |

---

## 4. PM2 Process Inventory (Complete)

```
┌────┬───────────────────────┬─────────┬──────────┬──────────┬─────────┐
│ id │ name                  │ status  │ cpu      │ mem      │ purpose │
├────┼───────────────────────┼─────────┼──────────┼──────────┼─────────┤
│ 21 │ sidix-brain           │ online  │ 0%       │ 835 MB   │ SIDIX AI RAG (uses Ollama host) │
│ 23 │ gateway               │ online  │ 0%       │ 352 MB   │ Mighantect 3D gateway │
│ 2  │ abra-website          │ online  │ 0%       │ 443 MB   │ Abrabriket website │
│ 25 │ mighan-web            │ online  │ 0%       │ 59 MB    │ Mighan website │
│ 26 │ sidix-next-ui         │ online  │ 0%       │ 60 MB    │ SIDIX Next.js UI │
│ 4  │ sidix-ui              │ online  │ 0%       │ 76 MB    │ SIDIX UI (port 4000) │
│ 5  │ tiranyx               │ online  │ 0%       │ 77 MB    │ Tiranyx website │
│ 0  │ revolusitani          │ online  │ 0%       │ 112 MB   │ Revolusitani website │
│ 1  │ shopee-gateway        │ online  │ 0%       │ 80 MB    │ Shopee integration │
│ 13 │ ixonomic-bank         │ online  │ 0%       │ 165 MB   │ Ixonomic banking │
│ 3  │ galantara-mp          │ online  │ 0%       │ 71 MB    │ Galantara marketplace │
│ 11 │ ixonomic-api          │ online  │ 0%       │ 62 MB    │ Ixonomic API │
│ ...│ (10 more ixonomic)    │ online  │ 0%       │ ~60 MB ea│ Ixonomic microservices │
└────┴───────────────────────┴─────────┴──────────┴──────────┴─────────┘
```

**Total PM2 RAM:** ~2.5–3 GB

---

## 5. Docker Container Inventory (Complete)

### MiganCore (ado_network — 172.16.1.0/24)
```
Container          Internal IP      Status
ado-ollama-1       172.16.1.3       Up (24 MB idle)
ado-postgres-1     172.16.1.4       Up Healthy (94 MB)
ado-qdrant-1       172.16.1.5       Up (57 MB)
ado-redis-1        172.16.1.6       Up (13 MB)
ado-letta-1        172.16.1.7       Up (172 MB)
```

### Other Docker
```
Container          Image               Status
jariyah-ollama     ollama/ollama:0.3.12  (not running currently — example only)
```

---

## 6. Network Port Matrix

| Port | Protocol | Process | Owner | Exposed to Internet? |
|------|----------|---------|-------|----------------------|
| 80 | TCP | nginx | aaPanel | ✅ Yes |
| 443 | TCP | nginx | aaPanel | ✅ Yes |
| 21 | TCP | pure-ftpd | aaPanel | ✅ Yes |
| 22 | TCP | sshd | System | ✅ Yes |
| 3306 | TCP | mariadbd | aaPanel | ❌ No (UFW blocks, but bind is 0.0.0.0) |
| 5432 | TCP | postgresql | Host PG14 | ❌ No (bind 127.0.0.1, UFW cleaned) |
| 6379 | TCP | redis-server | Host Redis | ❌ No (bind 127.0.0.1) |
| 11434 | TCP | ollama | Host Ollama | ❌ No (bind 127.0.0.1) |
| 39206 | TCP | aaPanel web | aaPanel | ✅ Yes (panel admin) |
| 8765 | TCP | sidix-brain | SIDIX | ❓ Via nginx reverse proxy? |
| 9797 | TCP | gateway | Mighantect | ❓ Via nginx reverse proxy? |
| 3000–3013 | TCP | ixonomic/next | Various | ❓ Via nginx reverse proxy? |
| 3200, 4000–4001 | TCP | sidix/mighan | Various | ❓ Via nginx reverse proxy? |

---

## 7. Architectural Decision Log

### Decision 1: Ollama Strategy — DUAL OLLAMA (Accepted)
**Context:** Host Ollama (PID 106258) is production for SIDIX brain_qa. Cannot stop.  
**Decision:** Keep both host Ollama (for SIDIX) and container Ollama (for MiganCore).  
**Impact:** +~5 GB RAM when MiganCore 7B is loaded. Total Ollama RAM: ~10 GB.  
**Mitigation:** Monitor RAM. If pressure, consider unified Ollama in future (MiganCore uses host Ollama with separate model).  
**Owner:** Fahmi (awareness) + Agent (monitoring)

### Decision 2: Reverse Proxy — INTEGRATE WITH NGINX (Pending)
**Context:** Caddy wants 80/443 but nginx aaPanel already holds them. Caddy cannot start.  
**Options:**
- A) Stop nginx, use Caddy exclusively (breaks all aaPanel sites — **REJECTED**)
- B) Remove Caddy, use nginx for MiganCore too (simplest, but less flexible)
- C) Caddy on alternate ports (8080/8443), nginx forwards to Caddy (elegant but complex)
- D) aaPanel nginx vhosts for migancore.com subdomains → forward to Docker containers

**Recommendation:** Option D for MVP, Option C for long-term elegance.  
**Owner:** Fahmi (decision needed) + Agent (implementation)

### Decision 3: Database Isolation — CONTAINER-ONLY (Accepted)
**Context:** Host has PG14 and Redis. MiganCore has pgvector and Redis containers.  
**Decision:** MiganCore uses container databases exclusively. No shared state with host DBs.  
**Verification:** ✅ Container DBs on `ado_network`, no port forwarding to host.  
**Owner:** Agent (enforced via docker-compose)

### Decision 4: Domain Strategy — SEPARATE SUBDOMAINS (Accepted)
**Context:** Existing domains: sidixlab.com, mighan.com, tiranyx.com, ixonomic.com, abrabriket.com  
**MiganCore domains:** api.migancore.com, app.migancore.com, lab.migancore.com, studio.migancore.com  
**Decision:** All migancore.com subdomains → nginx → MiganCore containers. No overlap.  
**Owner:** Fahmi (DNS already configured) + Agent (nginx config)

---

## 8. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | OOM when Ollama 7B + all services peak | Medium | High | Swap 8 GB. Monitor. Disable Langfuse under load. |
| R2 | nginx config conflict when adding MiganCore vhosts | Medium | High | Test in staging. Backup nginx configs before change. |
| R3 | Host Redis accidentally used by MiganCore | Low | Medium | MiganCore .env hardcodes `redis://redis:6379` (container hostname). |
| R4 | Host Postgres accidentally used by MiganCore | Low | Medium | MiganCore .env hardcodes `postgres:5432` (container hostname). |
| R5 | Caddy accidentally started, breaks nginx | Medium | High | Remove or disable Caddy service in docker-compose until decision made. |
| R6 | Agent modifies host configs, breaks existing apps | Low | Critical | AGENTS.md rule: NEVER touch /var/www/, /root/sidix/, aaPanel configs. |

---

## 9. Multi-Agent Safety Protocol

### Rules for ALL Future Agents (GPT, Claude, etc.)

1. **NEVER touch these paths:**
   - `/var/www/ixonomic/` — Ixonomic production
   - `/opt/sidix/` — SIDIX ecosystem
   - `/root/sidix/` — SIDIX deploy scripts
   - `/www/server/panel/` — aaPanel core
   - `/etc/nginx/sites-enabled/` (unless explicitly for MiganCore)

2. **NEVER stop these processes:**
   - `ollama.service` (PID 106258) — SIDIX brain depends on it
   - `redis-server.service` (PID 1369289) — host Redis
   - `postgresql@14-main` (PID 1329833) — host Postgres
   - Any PM2 process (`sidix-brain`, `gateway`, `ixonomic-*`)

3. **MiganCore workspace ONLY:**
   - `/opt/ado/` — the only permitted working directory
   - `docker compose` commands only in `/opt/ado/`
   - Git repo: `tiranyx/migancore` only

4. **Before any change:**
   - Read `docs/VPS_ECOSYSTEM_MAP.md`
   - Read `docs/AGENTS.md`
   - Verify with `docker compose ps` before modifying compose

---

## 10. Honest Assessment: Continue vs Handoff

### Can I (current agent) continue?
**Yes.** I have:
- ✅ Full SSH access with key + passphrase
- ✅ Complete ecosystem understanding
- ✅ All fixes applied (swap, UFW, Letta database)
- ✅ Ollama models pulled and verified

### Should Fahmi open GPT-5.5 or Claude Code?
**GPT-5.5:** Recommended for **architecture brainstorming** — give it this document + MASTER_HANDOFF.md and ask for creative review. GPT cannot access the VPS, so it's safe. Good for "what if" scenarios.

**Claude Code:** If limit resets, excellent for **code review** and **refactoring**. Claude is strong at spotting bugs in FastAPI/SQLAlchemy. But cannot access VPS either.

**Current agent (me):** Best for **execution** — scaffolding, deployment, debugging, server config. I can iterate on the VPS directly.

### Recommended Workflow
1. **Me (now):** Day 3–4 scaffold (FastAPI, auth, migrations)
2. **GPT-5.5 (parallel):** Review architecture decisions (Caddy vs nginx, Ollama strategy)
3. **Me (after GPT input):** Implement agreed changes
4. **Claude Code (when available):** Code review of FastAPI endpoints before production

---

*This document is the single source of truth for VPS state. Update after any infrastructure change.*
