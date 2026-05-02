# Deployment Test Results — 2026-05-03
**Scope:** Post-GPT-5.5 architecture review implementation testing  
**VPS:** 72.62.125.6 (mail.sidixlab.com)  
**Tester:** Kimi Code CLI (automated)  

---

## 1. Summary

| Component | Status | Detail |
|-----------|--------|--------|
| Git pull latest | ✅ PASS | Commit 5591738 deployed |
| Docker compose config | ✅ PASS | Valid, no syntax errors |
| Caddy port binding | ✅ PASS | No 80/443 binding (safe) |
| API container | ✅ PASS | Built and running on 127.0.0.1:18000 |
| API /health | ✅ PASS | `{"status":"healthy",...}` |
| API /ready | ✅ PASS | `{"status":"ready",...}` |
| API /docs | ✅ PASS | HTTP 200 |
| API / (root) | ✅ PASS | Service metadata returned |
| Ollama lazy-load config | ✅ PASS | KEEP_ALIVE=10m, NUM_PARALLEL=1 |
| Ollama model loaded | ✅ PASS | Qwen 7B loaded, 5.076 GiB |
| Nginx vhost | ✅ PASS | api.migancore.com.conf active |
| HTTPS via nginx | ✅ PASS | Self-signed cert, reverse proxy working |
| External DNS test | ✅ PASS | https://api.migancore.com/health responds |
| Existing services | ✅ PASS | SIDIX, Ixonomic, Mighantect unaffected |

**Overall: ALL TESTS PASS**

---

## 2. Container Status

```
NAME             IMAGE                    STATUS                    PORTS
ado-api-1        ado-api                  Up                        127.0.0.1:18000->8000/tcp
ado-letta-1      letta/letta:0.6.0        Up 56 minutes             8083/tcp
ado-ollama-1     ollama/ollama:latest     Up 5 minutes              11434/tcp
ado-postgres-1   pgvector/pgvector:pg16   Up About an hour (healthy) 5432/tcp
ado-qdrant-1     qdrant/qdrant:v1.9.0     Up About an hour          6333-6334/tcp
ado-redis-1      redis:7-alpine           Up About an hour          6379/tcp
```

**Note:** Caddy container is NOT running (disabled by profile `ingress`).

---

## 3. RAM Analysis

### Before Ollama Model Load (idle)
- Ollama container: ~24 MB
- Total VPS: ~5 GB used (existing services only)

### After Ollama Model Load (Qwen 7B Q4_K_M)
- Ollama container: **5.076 GiB / 12 GiB limit**
- Total VPS: **9.9 GB used / 31 GB**
- Swap: **109 MB used / 8 GB**

### Top RAM Consumers
```
USER         PID    %MEM   RSS      COMMAND
root     2464981  14.9%  4.9 GB   /usr/bin/ollama runner (MiganCore Qwen 7B)
root     2400672   2.7%  901 MB   python3 -m brain_qa serve (SIDIX)
ollama    106258   2.0%  663 MB   /usr/local/bin/ollama serve (Host Ollama)
root     1378365   1.3%  451 MB   next-server (Ixonomic app)
root      355161   1.1%  378 MB   next-server (Ixonomic app)
```

### Projection
- With Ollama loaded: ~10 GB / 32 GB (31%)
- With Ollama idle: ~5 GB / 32 GB (16%)
- **Headroom: 22 GB available when Ollama idle**
- **Headroom: 17 GB available when Ollama loaded**

---

## 4. Ollama Lazy-Load Verification

| Config | Before | After |
|--------|--------|-------|
| KEEP_ALIVE | 24h | **10m** ✅ |
| NUM_PARALLEL | 2 | **1** ✅ |
| MAX_LOADED_MODELS | 1 | 1 (unchanged) |
| MAX_QUEUE | — | **32** ✅ |

**Model status:**
```
NAME                          ID              SIZE      PROCESSOR    CONTEXT    UNTIL
qwen2.5:7b-instruct-q4_K_M    845dbda0ea48    4.6 GB    100% CPU     4096       6 minutes from now
```

**Verdict:** Lazy-load is active. Model will auto-unload after 10 minutes of inactivity.

---

## 5. Nginx Reverse Proxy Test

### Nginx Vhost Created
```
File: /www/server/panel/vhost/nginx/api.migancore.com.conf
Cert: /www/server/panel/vhost/cert/api.migancore.com/
      ├── fullchain.pem (self-signed, 365 days)
      └── privkey.pem
```

### Test Results

| Test | Command | Result |
|------|---------|--------|
| Local HTTP | `curl -H "Host: api.migancore.com" http://127.0.0.1/health` | 301 Redirect to HTTPS ✅ |
| Local HTTPS | `curl -sk -H "Host: api.migancore.com" https://127.0.0.1/health` | `{"status":"healthy",...}` ✅ |
| External HTTPS | `curl -sk https://api.migancore.com/health` | `{"status":"healthy",...}` ✅ |

---

## 6. API Endpoints Verified

### GET /health
```json
{
  "status": "healthy",
  "service": "migancore-api",
  "version": "0.1.0"
}
```

### GET /
```json
{
  "name": "MiganCore",
  "version": "0.1.0",
  "tagline": "Every vision deserves a digital organism.",
  "endpoints": {
    "health": "/health",
    "ready": "/ready",
    "docs": "/docs"
  }
}
```

### GET /ready
```json
{
  "status": "ready",
  "checks": {
    "postgres": "pending",
    "redis": "pending",
    "qdrant": "pending"
  }
}
```
> Note: Downstream checks are "pending" because connectivity verification is not yet implemented in Day 3 scaffold.

### GET /docs (Swagger UI)
- Status: HTTP 200 ✅
- Accessible at: `https://api.migancore.com/docs`

---

## 7. Isolation Verification

| Check | Result |
|-------|--------|
| Host Ollama (PID 106258) still running | ✅ Yes, unaffected |
| Host Redis (PID 1369289) still running | ✅ Yes, unaffected |
| Host Postgres (PID 1329833) still running | ✅ Yes, unaffected |
| nginx aaPanel still serving existing sites | ✅ Yes, reloaded successfully |
| SIDIX brain_qa (port 8765) still responding | ✅ Yes |
| MiganCore services bind only to 127.0.0.1 | ✅ Yes (API: 18000, Langfuse: 13001) |
| No forbidden paths touched | ✅ Yes |

---

## 8. Issues Found

| # | Issue | Severity | Action |
|---|-------|----------|--------|
| 1 | SSL cert is self-signed (browser will show warning) | 🟡 Low | Replace with Let's Encrypt cert via aaPanel UI |
| 2 | `/ready` endpoint shows "pending" for downstream checks | 🟡 Low | Implement connectivity checks in Day 4 |
| 3 | `nginx -T` does not show MiganCore vhost (aaPanel uses custom nginx binary) | 🟢 Info | Verified working via actual request test |
| 4 | Ollama model load took ~30-60s on first inference | 🟢 Info | Expected behavior for 5GB model on CPU |

---

## 9. Recommendations for Day 4

1. **Replace self-signed cert with Let's Encrypt** via aaPanel SSL panel for `api.migancore.com`
2. **Implement downstream health checks** in `/ready` endpoint (Postgres, Redis, Qdrant)
3. **Add auth endpoints** (`/auth/register`, `/auth/login`, `/auth/refresh`)
4. **Add JWT middleware** to protect API routes
5. **Test `adoctl`** on VPS and fix any issues
6. **Add nginx vhosts** for `app.migancore.com`, `lab.migancore.com`, `studio.migancore.com` (placeholder 503)

---

## 10. Files Modified During Testing

| File | Action |
|------|--------|
| `/opt/ado/docker-compose.yml` | Updated (lazy Ollama, profiles, localhost binds) |
| `/opt/ado/scripts/day1-setup.sh` | Updated (random passwords, no hardcoded secrets) |
| `/opt/ado/scripts/day2-setup.sh` | Updated (no healthcheck wait, profile memory) |
| `/opt/ado/api/main.py` | Created (FastAPI scaffold) |
| `/opt/ado/scripts/adoctl` | Created (operational controller) |
| `/opt/ado/docs/INFRA_BOUNDARY_CONTRACT.md` | Created |
| `/www/server/panel/vhost/nginx/api.migancore.com.conf` | Created |
| `/www/server/panel/vhost/cert/api.migancore.com/` | Created (self-signed) |

---

*Tested automatically via SSH by Kimi Code CLI. All results verified against actual VPS state.*
