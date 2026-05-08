# MIGANCORE — ALIGNMENT AUDIT
**Tanggal:** 2026-05-08 | **Executor:** Kimi Code CLI
**Tujuan:** Cek seamless & selaras antara repo lokal, GitHub, server, dan live app.

---

## EXECUTIVE SUMMARY

**Status Overall:** 🟡 PARTIAL ALIGNMENT — beberapa sistem berfungsi, beberapa tidak, ada documentation drift signifikan.

| Layer | Status | Notes |
|---|---|---|
| DNS | 🟢 OK | Semua domain resolve ke 72.62.125.6 |
| API (api.migancore.com) | 🟢 OK | v0.5.16, all endpoints 200ms |
| Frontend (app.migancore.com) | 🟢 OK | Chat app live |
| Landing (migancore.com) | 🟢 OK | Landing page live |
| Consumer Channels | 🔴 MISMATCH | mighan.com & sidixlab.com adalah project BEDA |
| Observability (lab.migancore.com) | 🔴 DOWN | 000 — tidak merespons |
| Studio (studio.migancore.com) | 🔴 DOWN | 000 — tidak merespons |
| Governance (tiranyx.com) | 🔴 DOWN | 000 — tidak merespons |
| GitHub Repos | 🟡 PARTIAL | migancore OK, platform 404, community OK but empty |
| Root Repo (local) | 🟡 ORPHAN | No remote configured — docs local-only |
| Server Containers | 🟡 UNKNOWN | SSH timeout, tapi API responding |
| Data Pipeline | 🔴 BROKEN | 99% synthetic, user feedback tidak jalan |

---

## 1. REPO ALIGNMENT

### 1.1 migancore (Main Repo)
| Aspect | Status | Detail |
|---|---|---|
| Local branch | `main` @ `0dd1970` | ✅ Latest |
| GitHub remote | `tiranyx/migancore` | ✅ Exists |
| Sync status | **SYNCED** | `0dd1970` pushed to origin/main |
| Last push | 2026-05-08 22:XX | ✅ Fresh |

**Files synced:**
- ✅ `docs/MIGANCORE_ARCHITECTURE_REMAP_v2026.md`
- ✅ `docs/MIGANCORE_ROADMAP_MILESTONES.md`
- ✅ `docs/MIGANCORE_DAILY_PROTOCOL.md`
- ✅ `docs/CONTEXT.md`
- ✅ `docs/TASK_BOARD.md`
- ✅ `docs/LESSONS_LEARNED.md` (F-12 s/d F-18, S-11)
- ✅ `docs/logs/daily/2026-05-08.md`

### 1.2 migancore-platform
| Aspect | Status | Detail |
|---|---|---|
| Local branch | `main` @ `be9c60e` | ✅ Latest |
| GitHub remote | `tiranyx/migancore-platform` | ⚠️ Configured but repo 404 |
| Sync status | **UNKNOWN** | Cannot verify remote exists |
| Content | EMPTY | Only scaffold, no real code |

**Issue:** GitHub API returns "Not Found" untuk tiranyx/migancore-platform. Repo mungkin:
- Private (tapi local clone dari sana)
- Dihapus
- Dipindah ke nama lain

**Action required:** Verifikasi kepemilikan repo di GitHub dashboard.

### 1.3 migancore-community
| Aspect | Status | Detail |
|---|---|---|
| Local branch | `main` @ `42b2a32` | ✅ Latest |
| GitHub remote | `tiranyx/migancore-community` | ✅ Exists |
| Sync status | **SYNCED** | Local = Remote |
| Content | MINIMAL | LICENSE, README, souls/, templates/ |

### 1.4 Root Repo (C:\migancore)
| Aspect | Status | Detail |
|---|---|---|
| Local branch | `master` @ `a93774c` | ✅ Committed |
| GitHub remote | **NONE** | 🔴 Tidak ada remote configured |
| Sync status | **ORPHAN** | Local-only |

**Issue:** Root repo tidak punya remote. Semua file di root level (CONTEXT.md, TASK_BOARD.md, Master doc/, infrastructure/, dll) hanya ada di local.

**Impact:**
- Jika laptop rusak = data loss untuk root-level docs
- Tidak ada backup untuk Master doc/, infrastructure/, docs/ baru
- Tidak ada CI/CD untuk root repo

**Action required:**
1. Buat GitHub repo untuk root project (misal: `tiranyx/migancore-workspace` atau `tiranyx/migancore-monorepo`)
2. Atau: pindahkan semua root-level docs ke dalam `migancore/` subrepo yang sudah punya remote

**Rekomendasi:** Pindahkan Master doc/ dan infrastructure/ ke dalam `migancore/docs/master/` dan `migancore/infra/` agar semua ada di satu repo dengan remote.

### 1.5 busy-dijkstra-d1681d
| Aspect | Status | Detail |
|---|---|---|
| Local branch | `master` @ `fc0b3fb` | ✅ |
| GitHub remote | **NONE** | 🔴 Tidak ada remote |
| Sync status | **ORPHAN** | Local-only nested repo |

**Issue:** Nested repo tanpa submodule mapping. Git di root repo mengeluh:
```
fatal: no submodule mapping found in .gitmodules for path 'busy-dijkstra-d1681d'
```

**Action required:**
1. Hapus dari root repo index: `git rm --cached busy-dijkstra-d1681d`
2. Atau: register sebagai proper submodule
3. Atau: push ke GitHub repo terpisah

---

## 2. SERVER ALIGNMENT

### 2.1 VPS Access
| Aspect | Status | Detail |
|---|---|---|
| SSH (sidix-vps config) | 🟢 **OK** | `~/.ssh/sidix_session_key` — working |
| Direct SSH (root@72.62.125.6) | 🔴 TIMEOUT | Default key rejected, must use config |
| API Health | 🟢 OK | `curl /health` = 200, 50ms |
| DNS Resolution | 🟢 OK | All domains → 72.62.125.6 |

**SSH Config:** `C:\Users\ASUS\.ssh\config`
```
Host sidix-vps
    HostName 72.62.125.6
    User root
    IdentityFile ~/.ssh/sidix_session_key
    IdentitiesOnly yes
```

**Usage:** `ssh sidix-vps "command"`

### 2.2 Server Resources
| Resource | Value | Status |
|---|---|---|
| RAM | 31GB total / 4.7GB used / **26GB available** | 🟢 Excellent |
| Disk | 388GB total / 124GB used / **264GB free** | 🟢 Excellent |
| Load average | 0.00 | 🟢 Very idle |
| Uptime | 1 day, 2 hours | 🟢 Stable |

### 2.3 Docker Containers

**Running (7 containers):**
| Container | Status | Uptime | Ports |
|---|---|---|---|
| ado-api-1 | Up 16 hours | Healthy | 127.0.0.1:18000→8000 |
| ado-ollama-1 | Up 23 hours | OK | 11434 (internal) |
| ado-postgres-1 | Up 26 hours | Healthy | 5432 (internal) |
| ado-qdrant-1 | Up 26 hours | OK | 6333-6334 (internal) |
| ado-redis-1 | Up 26 hours | OK | 6379 (internal) |
| ado-letta-1 | Up 26 hours | OK | 8083 (internal) |

**NOT Running (missing from compose):**
| Service | Status | Reason |
|---|---|---|
| langfuse | 🔴 MISSING | Not in default profile |
| caddy | 🔴 MISSING | Disabled — aaPanel/nginx owns 80/443 |
| studio/mlflow | 🔴 MISSING | Future/training profile |
| celery workers | 🔴 MISSING | workers profile not active |
| frontend | 🔴 MISSING | Served by nginx directly from /opt/ado/frontend |

**Docker Compose Profile:** `default` only (postgres, redis, qdrant, ollama, api, letta)

### 2.4 Reverse Proxy Architecture

**Actual reverse proxy: aaPanel/nginx** (NOT caddy)
- Nginx master process: `/www/server/nginx/sbin/nginx`
- Listens on 0.0.0.0:80 and 0.0.0.0:443
- SSL via Let's Encrypt
- API proxied to `127.0.0.1:18000` (ado-api-1 container port mapping)
- Frontend served from `/opt/ado/frontend/` (nginx root directive)
- Landing served from `/www/wwwroot/migancore.com/` (nginx root directive)

**Nginx configs exist for:**
- ✅ `migancore.com` + `www.migancore.com` (landing)
- ✅ `api.migancore.com` (API proxy to :18000)
- ✅ `app.migancore.com` (frontend from /opt/ado/frontend)
- ❌ `lab.migancore.com` — **NO CONFIG**
- ❌ `studio.migancore.com` — **NO CONFIG**

**Why lab/studio down:**
1. No nginx vhost config for these subdomains
2. langfuse container not running (not in default compose profile)
3. studio service doesn't exist in compose

### 2.2 Docker Containers (via API inference)
Tidak bisa verifikasi langsung karena SSH timeout, tapi dari `/ready` endpoint:

| Service | Status | Detail |
|---|---|---|
| PostgreSQL | 🟢 OK | "connected" |
| Redis | 🟢 OK | "connected" |
| Qdrant | 🟢 OK | "connected" |
| Ollama | 🟢 OK | "6 models loaded" |

**Ollama Models Loaded:**
1. migancore:0.7c
2. migancore:0.7b
3. migancore:0.7
4. migancore:0.3 (production)
5. qwen2.5:7b-instruct-q4_K_M

**Note:** 3 model rollback versions (0.7, 0.7b, 0.7c) masih ada di memory. Bisa di-unload untuk free RAM.

---

## 3. LIVE APP ALIGNMENT

### 3.1 Endpoint Health Check

| Endpoint | Status | Latency | Notes |
|---|---|---|---|
| `migancore.com` | 🟢 200 | 40ms | Landing page |
| `www.migancore.com` | 🟢 200 | 68ms | Redirect/landing |
| `app.migancore.com` | 🟢 200 | 75ms | Chat app |
| `api.migancore.com/health` | 🟢 200 | 53ms | API healthy v0.5.16 |
| `api.migancore.com/ready` | 🟢 200 | 45ms | All services OK |
| `api.migancore.com/v1/public/stats` | 🟢 200 | 265ms | 3354 pairs, 1% real |
| `api.migancore.com/v1/system/status` | 🟢 200 | 43ms | 29 tools |
| `api.migancore.com/v1/system/metrics` | 🟢 200 | 58ms | Metrics endpoint |
| `api.migancore.com/v1/agents` | 🟢 401 | 43ms | Auth required (correct) |
| `api.migancore.com/v1/auth/register` | 🟢 405 | 34ms | POST required (correct) |
| `lab.migancore.com` | 🔴 000 | 152ms | **DOWN** — connection refused |
| `studio.migancore.com` | 🔴 000 | 37ms | **DOWN** — connection refused |
| `sidixlab.com` | 🟢 200 | 118ms | **BUKAN Migancore — ini SIDIX 2.0** |
| `mighan.com` | 🟢 200 | 289ms | **BUKAN Migancore — ini Mighantect** |
| `tiranyx.com` | 🔴 000 | 354ms | **DOWN** |

### 3.2 Critical Findings

**Finding 1: Consumer Channels are WRONG PROJECTS**
- Dokumen arsitektur bilang: `sidixlab.com` = consumer channel untuk research
- Realita: `sidixlab.com` menjalankan **SIDIX 2.0** (project terpisah)
- Dokumen bilang: `mighan.com` = consumer channel untuk clone platform
- Realita: `mighan.com` menjalankan **Mighantect** (virtual office AI agent game)
- Dokumen bilang: `tiranyx.com` = governance
- Realita: `tiranyx.com` **DOWN**

**Impact:** Arsitektur 3-layer consumer channel tidak terimplementasi. Semua domain consumer menunjuk ke project lain atau down.

**Fix:**
1. Jujur di dokumentasi: consumer channels belum dibangun
2. Atau: buat subdomain/subfolder yang benar mengakses api.migancore.com
3. Atau: redirect mighan.com/sidixlab.com ke app.migancore.com sementara

**Finding 2: Observability (lab.migancore.com) DOWN**
- Langfuse container tidak berjalan, atau
- Nginx tidak proxy ke Langfuse, atau
- Langfuse belum di-deploy

**Impact:** Tidak ada observability untuk production. Tidak bisa trace error, latency, atau usage patterns.

**Fix:**
1. Cek docker ps (butuh SSH)
2. Atau cek nginx config via aaPanel
3. Deploy Langfuse jika belum, atau fix nginx proxy

**Finding 3: Studio (studio.migancore.com) DOWN**
- MLflow/training studio tidak berjalan

**Impact:** Tidak ada UI untuk monitoring training runs, model versions, eval scores.

**Fix:**
1. Deploy MLflow atau custom studio dashboard
2. Atau: remove dari nginx config sampai ready

---

## 4. DATA ALIGNMENT

### 4.1 Preference Pairs (via `/v1/public/stats`)

| Source Method | Count | Type | Status |
|---|---|---|---|
| synthetic_seed_v1 | 1672 | Synthetic | ⚠️ 49.8% — too high |
| tool_use_v2:cycle7 | 108 | Synthetic | ⚠️ |
| creative_anchor_v1:cycle6 | 118 | Synthetic | ⚠️ |
| tool_use_anchor_v2:cycle6 | 116 | Synthetic | ⚠️ |
| voice_anchor_v1:cycle7 | 80 | Anchor | ✅ |
| voice_anchor_v1:cycle5 | 80 | Anchor | ✅ |
| evolution_aware_v3:cycle6 | 78 | Anchor | ⚠️ |
| umkm_business_v1:cycle5 | 70 | Anchor | ⚠️ |
| engineering_fullstack_v1:cycle5 | 60 | Anchor | ⚠️ |
| bisnis_legalitas_v1:cycle5 | 60 | Anchor | ⚠️ |
| evolution_aware_v2:cycle5 | 60 | Anchor | ⚠️ |
| indonesia_creative_v1:cycle5 | 55 | Synthetic | ⚠️ |
| adaptive_persona_v1:cycle5 | 55 | Synthetic | ⚠️ |
| identity_anchor_v2:identity | 50 | Anchor | ✅ |
| code_correctness_v1:python_basics | 50 | Anchor | ⚠️ |
| identity_anchor_v2:creator | 30 | Anchor | ✅ |
| identity_anchor_v2:anti_sycophancy | 30 | Anchor | ✅ |
| identity_anchor_v2:values | 30 | Anchor | ✅ |
| identity_anchor_v2:tool_style | 20 | Anchor | ⚠️ |
| identity_anchor_v2:voice | 34 | Anchor | ✅ |
| honesty_v1:cycle7 | 40 | Anchor | ⚠️ |
| creative_v3:cycle7 | 39 | Anchor | ⚠️ |
| voice_style_v1:cycle7 | 40 | Anchor | ⚠️ |
| code_correctness_v1:* | 190 | Anchor | ⚠️ |
| tool_use_anchor_v1:* | 190 | Anchor | ⚠️ |
| cai_pipeline | 18 | Real | ✅ |
| distill_kimi_v1 | 10 | Real | ✅ |
| user_thumbs_up | 1 | Real | 🔴 BROKEN |
| **TOTAL** | **3354** | | |
| **Real Data** | **29** | **0.9%** | 🔴 **CRITICAL** |
| **Synthetic** | **~3300** | **~98%** | 🔴 **CRITICAL** |

### 4.2 Database State (verified via SSH)

| Table | Row Count | Status | Notes |
|---|---|---|---|
| tenants | **56** | 🟢 | Multi-tenant active |
| users | **56** | 🟢 | 1 user per tenant? |
| agents | **73** | 🟢 | Active agents |
| conversations | **72** | 🟢 | Chat sessions |
| messages | **194** | 🟢 | Total messages |
| preference_pairs | **3354** | ⚠️ | 99% synthetic |
| tools | **21** | 🟢 | Tool registry |
| model_versions | ? | ? | Not checked |
| training_runs | **0** | 🔴 | Not tracked |
| datasets | **0** | 🔴 | Not tracked |
| kg_entities | **0** | 🔴 | Knowledge graph empty |
| kg_relations | **0** | 🔴 | Knowledge graph empty |
| interactions_feedback | **0** | 🔴 | Broken worker |
| experiments | ? | ? | Not checked |
| papers | ? | ? | Not checked |

---

## 5. SSL & SECURITY ALIGNMENT

| Domain | SSL | Status |
|---|---|---|
| migancore.com | ✅ Let's Encrypt/Cloudflare | Valid |
| app.migancore.com | ✅ | Valid |
| api.migancore.com | ✅ | Valid |
| www.migancore.com | ✅ | Valid |
| sidixlab.com | ✅ | Valid (SIDIX) |
| mighan.com | ✅ | Valid (Mighantect) |
| lab.migancore.com | N/A | DOWN |
| studio.migancore.com | N/A | DOWN |
| tiranyx.com | N/A | DOWN |

**Security headers:** API returns 401/405 correctly untuk protected endpoints. Public endpoints (health, ready, public/stats, system/*) correctly unauthenticated.

---

## 5.5 SERVER DEPLOYMENT GAP

**Server git is BEHIND GitHub by 6 commits:**
- Server: `556abb2` (Day 71d Phase 4)
- GitHub: `b2cf0a8` (Day 0 Remap + Audit)
- Missing on server: Day 71e research, lessons F-12~F-18, architecture remap, daily logs, alignment audit

**Impact:** Semua docs baru tidak ada di server. Tapi karena ini hanya docs (bukan code), API tidak terpengaruh.

**Fix:** `git pull` di `/opt/ado/` (tidak perlu rebuild karena hanya markdown).

---

## 6. FIX PRIORITY MATRIX

### 🔴 CRITICAL (Fix Now)

| # | Issue | Impact | Fix |
|---|---|---|---|
| 1 | Root repo no remote | Data loss risk | Create GitHub repo OR move docs to migancore subrepo |
| 2 | User thumbs broken | 1 pair vs expected 100+ | Fix endpoint + hourly worker (TASK-004) |
| 3 | lab.migancore.com DOWN | No observability | Deploy Langfuse OR remove from nginx |
| 4 | Consumer channels wrong | Architecture doc lies | Update docs: channels = project lain, belum dibangun |

### 🟡 HIGH (Fix This Week)

| # | Issue | Impact | Fix |
|---|---|---|---|
| 5 | busy-dijkstra-d1681d no remote | Data loss | Push to GitHub OR remove from index |
| 6 | studio.migancore.com DOWN | No training UI | Deploy MLflow OR remove from nginx |
| 7 | tiranyx.com DOWN | Governance missing | Deploy OR remove |
| 8 | migancore-platform repo 404 | Cannot verify sync | Check GitHub dashboard |
| 9 | Ollama 5 models loaded | RAM waste (~15GB) | Unload rollback versions (0.7, 0.7b, 0.7c) |

### 🟢 NORMAL (Fix When Convenient)

| # | Issue | Impact | Fix |
|---|---|---|---|
| 10 | SSH timeout | Cannot check server directly | Whitelist IP di UFW |
| 11 | docs/logs in .gitignore | Daily logs not tracked | Remove from .gitignore OR use -f |
| 12 | 99% synthetic data | Brain quality stuck | Build 4 pathways (M1) |

---

## 6.5 SSH VALIDATION COMMANDS

Sekarang SSH berfungsi, berikut commands untuk validasi cepat:

```bash
# === CONNECT ===
ssh sidix-vps

# === HEALTH CHECKS ===
# API health
curl -s http://localhost:18000/health | python3 -m json.tool

# Readiness (all services)
curl -s http://localhost:18000/ready | python3 -m json.tool

# Public stats
curl -s http://localhost:18000/v1/public/stats | python3 -m json.tool

# === DOCKER ===
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'

# === DATABASE ===
docker exec ado-postgres-1 psql -U ado -d ado -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
docker exec ado-postgres-1 psql -U ado -d ado -c "SELECT source_method, COUNT(*) FROM preference_pairs GROUP BY source_method ORDER BY COUNT(*) DESC;"
docker exec ado-postgres-1 psql -U ado -d ado -c "SELECT COUNT(*) FROM agents;"
docker exec ado-postgres-1 psql -U ado -d ado -c "SELECT COUNT(*) FROM conversations;"
docker exec ado-postgres-1 psql -U ado -d ado -c "SELECT COUNT(*) FROM interactions_feedback;"

# === RESOURCES ===
free -h
df -h
cat /proc/loadavg

# === LOGS ===
docker logs ado-api-1 --tail 50
docker logs ado-ollama-1 --tail 20

# === OLLAMA ===
docker exec ado-ollama-1 ollama list
docker exec ado-ollama-1 ollama ps
```

---

## 7. ALIGNMENT CHECKLIST (Run Weekly)

```
□ API health: curl https://api.migancore.com/health → 200
□ Ready check: curl https://api.migancore.com/ready → all services OK
□ Frontend: curl https://app.migancore.com → 200
□ Landing: curl https://migancore.com → 200
□ SSL: curl -v https://api.migancore.com → certificate valid
□ GitHub sync: git status → nothing to commit, branch up to date
□ Public stats: curl /v1/public/stats → pairs increasing, real-data ratio ≥ target
□ Observability: curl https://lab.migancore.com → 200 (when deployed)
□ Consumer channels: verify correct content (when deployed)
```

---

## 8. VERDIK

**What IS aligned:**
- ✅ API, frontend, landing = live and healthy
- ✅ DNS = all resolve correctly
- ✅ SSL = valid on all live domains
- ✅ migancore subrepo = synced with GitHub
- ✅ migancore-community = synced with GitHub

**What is NOT aligned:**
- 🔴 Root repo = orphan (no remote)
- 🔴 lab.migancore.com = DOWN
- 🔴 studio.migancore.com = DOWN
- 🔴 tiranyx.com = DOWN
- 🔴 Consumer channels = wrong projects
- 🔴 Data pipeline = 99% synthetic
- 🔴 busy-dijkstra-d1681d = no remote
- 🔴 migancore-platform = repo 404

**Bottom line:** Core product (API + chat) is solid. Infrastructure around it (observability, docs backup, consumer channels) is broken or misaligned.

---

*Audit ini harus di-review mingguan. Update setelah setiap fix.*
