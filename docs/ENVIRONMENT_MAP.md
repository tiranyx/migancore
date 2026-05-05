# MIGANCORE — VPS ENVIRONMENT MAP (CRITICAL ONBOARDING DOC)
**Date:** 2026-05-05 (Day 49.5 — created from real outage today)
**Maintained by:** every agent updates after discovering new tenant/process
**Why this exists:** VPS is shared with 4 other projects. Today's chat outage took 2+ hours because no one knew there were TWO Ollama daemons running.

> **LESSON #54:** "VPS shared, selalu cek environment map dulu sebelum eksekusi apa-apa."
> Patch-on-patch tanpa cek topology = berjam-jam buang waktu.

---

## 🖥️ HOST OVERVIEW

| Field | Value |
|-------|-------|
| Hostname | srv1521061 |
| Public IP | 72.62.125.6 |
| OS | Ubuntu 22.04 |
| RAM | 32GB total (~18GB available, ~11GB always used by base) |
| Swap | 8GB |
| vCPU | 8 cores |
| Disk | 400GB |
| Panel | aaPanel |
| SSH | port 22, key `~/.ssh/sidix_session_key` (also `id_ed25519`) |

---

## 👥 TENANTS (PROJECTS sharing this VPS)

### 1. MiganCore (`/opt/ado/`) ← **OUR PROJECT**
- Docker compose with 6 containers: api, ollama, postgres, qdrant, redis, letta
- Ports (host-side): 18000 (api proxied to api.migancore.com)
- Ollama: **CONTAINER-INTERNAL on `ollama:11434` via docker DNS** — NOT bound on host
- Models: `qwen2.5:7b-instruct-q4_K_M`, `qwen2.5:0.5b`
- Volume: `/opt/ado/data/{ollama,postgres,redis,qdrant}`

### 2. SIDIX (`/opt/sidix/`)
- HOST-installed Ollama daemon (PID 106258 since Apr 28, user `ollama`)
- **Listens on `127.0.0.1:11434`** — owns the host-side localhost port
- Models: `qwen2.5:7b`, `sidix-lora:latest`, `qwen2.5:1.5b`
- HYPERX browser tool at `/opt/sidix/tools/hyperx-browser/` (mounted into ado-api-1 as `/app/hyperx`)

### 3. Mighantect3D (`/opt/mighantech3d/`)
- Three.js client + Node gateway monorepo
- Ports + processes: not yet documented (TODO update next visit)

### 4. Ixonomic (`/var/www/ixonomic/`)
- Node bank server (PID 2173945, ~140MB RSS)
- Probably nginx-proxied via aaPanel

### 5. Tiranyx-co-id (`/www/wwwroot/tiranyx.co.id/`)
- **Next.js v14.2.35** (next-server PID 2603422)
- **Webpack build process intermittent** (PID 2622011 hit 657% CPU during today's outage — competed for CPU against Ollama 7B inference)
- npm + node v22.22.2 via NVM at `/www/server/nvm/versions/node/v22.22.2/`

### 6. Galantara (`/www/galantara-server/`)
- Node server (PID 2457571, 75MB RSS)

### Other host services
- `brain_qa serve` (PID 2400672, ~1GB RSS) — separate brain QA service
- aaPanel control panel
- nginx (multi-vhost)

---

## ⚠️ CRITICAL GOTCHAS

### Gotcha #1: TWO Ollama daemons share name "ollama"
- **Host:** `/usr/local/bin/ollama serve` (PID 106258, sidix project) — listens `localhost:11434`
- **Container:** `ado-ollama-1` runs `/bin/ollama serve` — listens internally
- **From VPS bash:** `curl localhost:11434/...` → hits HOST Ollama (sidix's models)
- **From inside ado-api-1:** `curl http://ollama:11434/...` → docker DNS → CONTAINER Ollama (migancore models)
- **Test brain ALWAYS from inside container:** `docker exec ado-api-1 python -c "..."`
- Hari ini bug ini buang ~2 jam — wajib catat di onboarding

### Gotcha #2: CPU contention with tiranyx-co-id builds
- Tiranyx Next.js webpack build can spawn workers @ 600%+ CPU
- Qwen2.5-7B inference also wants high CPU
- **When user chat slow:** check `ps aux --sort=-%cpu | head -10` first
- **Mitigation:** schedule builds (cron) outside chat hours OR upgrade VPS

### Gotcha #3: `pkill -9 -f 'ollama'` may kill host daemon (sidix)
- ALWAYS use `docker compose restart ollama` for migancore restart
- Manual `pkill` risks sidix downtime + breaks SSH session occasionally

### Gotcha #4: `OLLAMA_KEEP_ALIVE=10m` (default) → model unloads after idle
- Container Ollama env was `10m` until Day 49.5 hotfix → bumped to `24h`
- For multi-restart day, this caused repeated 160s+ reload loops
- DON'T set back to `10m` without understanding the cost

### Gotcha #5: synthetic gen saturates Ollama → user chat blocked
- `synthetic_seed_v1` flywheel can queue 30+ concurrent CAI critique calls
- `OLLAMA_NUM_PARALLEL=1` means user chat waits behind synth queue → 90s+ timeout
- **Hotfix today:** `synthetic stop` via admin endpoint
- **Real fix needed (Day 50):** priority queue OR rate-limit synth when active session detected (Lesson #54.5)

### Gotcha #6: `docker compose stop` then SSH session dies
- `pkill -9 -f ollama runner` killed orphan but also killed sshd-related processes
- ALWAYS use `docker compose restart` not stop+up sequences if SSH session is fragile
- After SSH disconnect, reconnect + verify container state with `docker compose ps`

---

## 🌐 NETWORKING TOPOLOGY

```
Internet
   │
   ▼
nginx (aaPanel, host port 80/443) ─── Let's Encrypt SSL
   │
   ├─ api.migancore.com:443 → 127.0.0.1:18000 → ado-api-1:8000
   ├─ app.migancore.com:443 → /opt/ado/frontend/ (static files)
   ├─ migancore.com:443 → /www/wwwroot/migancore.com/
   ├─ tiranyx.co.id:443 → tiranyx Next.js
   └─ (other vhosts for sidix, ixonomic, etc)

Inside docker bridge "ado_default":
   ado-api-1 ↔ ado-ollama-1 (port 11434)
   ado-api-1 ↔ ado-postgres-1 (port 5432)
   ado-api-1 ↔ ado-redis-1 (port 6379)
   ado-api-1 ↔ ado-qdrant-1 (port 6333)
   ado-api-1 ↔ ado-letta-1 (port 8283)

Host-only ports (NOT in docker network):
   127.0.0.1:11434 ← sidix's Ollama daemon
```

---

## 📋 BEFORE-EVERY-SPRINT CHECKLIST

```bash
# 1. Confirm VPS not under heavy load
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "uptime && free -h | head -2"

# 2. Confirm migancore containers all UP
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "docker compose -f /opt/ado/docker-compose.yml ps"

# 3. Confirm no rogue Ollama processes
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "ps aux | grep 'ollama runner' | grep -v grep | wc -l"
# Expected: 1 (or 0 if no model loaded). >1 = orphan → restart container.

# 4. Confirm no heavy build competing
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "ps aux --sort=-%cpu | head -5"
# If you see >300% CPU on next/webpack/node from /www/wwwroot/tiranyx.co.id/, 
# user chat will be slow — don't trigger expensive operations until build done.

# 5. Test brain from API container (correct Ollama)
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "docker exec ado-api-1 python -c \"
import httpx, time
t0=time.perf_counter()
r=httpx.post('http://ollama:11434/api/generate', json={'model':'qwen2.5:7b-instruct-q4_K_M','prompt':'hi','stream':False,'options':{'num_predict':5}}, timeout=60.0)
print('elapsed:', int((time.perf_counter()-t0)*1000), 'ms', 'status:', r.status_code)
\""
# Expected: <30s warm. >60s = something competing for CPU.
```

---

## 🔧 RECOVERY PLAYBOOK

### Brain (Ollama) timeout / "model not found"
```bash
# 1. Check which Ollama you're hitting
ssh ... "ps aux | grep ollama serve | grep -v grep"
# Should see TWO: host (PID 106258) + container (one inside ado-ollama-1)

# 2. Check if container Ollama healthy
ssh ... "docker exec ado-ollama-1 ollama ps"
# Should show qwen2.5:7b-instruct-q4_K_M with UNTIL = "24 hours from now"

# 3. If model not loaded, pre-warm (5-min budget)
ssh ... "docker exec ado-api-1 python -c \"import httpx; print(httpx.post('http://ollama:11434/api/generate', json={'model':'qwen2.5:7b-instruct-q4_K_M','prompt':'hi','stream':False,'options':{'num_predict':5}}, timeout=300).status_code)\""

# 4. If still failing, restart container Ollama (NOT host)
ssh ... "docker compose -f /opt/ado/docker-compose.yml restart ollama"
# Wait 60s for daemon, then pre-warm again with 5-min budget.
```

### Synth gen blocking user chat
```bash
# Stop via admin endpoint
ssh ... "ADMIN_KEY=\$(docker exec ado-api-1 printenv ADMIN_SECRET_KEY); curl -X POST -H \"X-Admin-Key: \$ADMIN_KEY\" http://localhost:18000/v1/admin/synthetic/stop"
# Status:
ssh ... "ADMIN_KEY=\$(docker exec ado-api-1 printenv ADMIN_SECRET_KEY); curl -H \"X-Admin-Key: \$ADMIN_KEY\" http://localhost:18000/v1/admin/synthetic/status"
```

---

## 📝 UPDATE LOG

- **2026-05-05 (Day 49.5):** Initial creation after dual-Ollama discovery + tiranyx CPU contention outage. Documented 6 critical gotchas + recovery playbook.

---

**Update this file IMMEDIATELY when:**
- New tenant detected on VPS
- New port conflict found
- New CPU/memory contention pattern observed
- New process category competes with migancore
