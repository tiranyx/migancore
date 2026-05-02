# INFRA_BOUNDARY_CONTRACT.md
**Version:** 1.0  
**Date:** 2026-05-03  
**Purpose:** Machine-readable boundary contract for all AI agents working on MiganCore  
**Enforcement:** `scripts/adoctl` + git hooks (future)  

---

## 1. FORBIDDEN ZONES (Never Touch)

These paths, services, and ports belong to existing production infrastructure. Modifying them will break SIDIX, Ixonomic, Mighantect, or aaPanel.

### 1.1 Forbidden Paths
```yaml
forbidden_paths:
  - /opt/sidix              # SIDIX AI ecosystem (brain_qa, Raudah, Qalb)
  - /root/sidix             # SIDIX deploy scripts
  - /var/www/ixonomic       # Ixonomic fintech suite
  - /www/server/panel       # aaPanel control panel core
  - /etc/nginx/sites-enabled # aaPanel nginx vhosts (existing sites)
```

### 1.2 Forbidden Services
```yaml
forbidden_services:
  - ollama.service           # Host Ollama — belongs to SIDIX brain_qa
  - redis-server.service     # Host Redis — shared by multiple apps
  - postgresql@14-main       # Host PostgreSQL 14 — aaPanel/SIDIX
  - nginx                    # aaPanel web server — owns 80/443
  - mariadb                  # aaPanel database
```

### 1.3 Forbidden Ports (Host Level)
```yaml
forbidden_host_ports:
  - 80                       # nginx HTTP
  - 443                      # nginx HTTPS
  - 3306                     # MariaDB
  - 39206                    # aaPanel admin panel
  - 8765                     # SIDIX brain_qa
  - 9797                     # Mighantect gateway
  - 3000-3013                # Ixonomic microservices
```

---

## 2. ALLOWED ZONE (MiganCore Only)

### 2.1 Allowed Paths
```yaml
allowed_workspace: /opt/ado
allowed_subpaths:
  - /opt/ado/docker-compose.yml
  - /opt/ado/Caddyfile
  - /opt/ado/api/
  - /opt/ado/core/
  - /opt/ado/memory/
  - /opt/ado/tools/
  - /opt/ado/training/
  - /opt/ado/migrations/
  - /opt/ado/scripts/
  - /opt/ado/docs/
  - /opt/ado/data/           # Container volumes only
  - /opt/ado/tests/
  - /opt/ado/.env            # local only, gitignored
```

### 2.2 Allowed Ports (MiganCore Services)
```yaml
allowed_ports:
  - 127.0.0.1:18000          # FastAPI API (nginx reverse proxy target)
  - 127.0.0.1:13001          # Langfuse (nginx reverse proxy target)
  # Internal Docker network ports (not exposed to host):
  #   postgres:5432, redis:6379, qdrant:6333, ollama:11434, letta:8283
```

### 2.3 Allowed Git Repository
```yaml
allowed_repo: https://github.com/tiranyx/migancore.git
allowed_branches:
  - main
  - feature/*
  - fix/*
```

---

## 3. PREFLIGHT CHECKLIST (Before Every Deploy)

Every agent MUST run these checks before deploying:

```bash
□ cd /opt/ado                          # Must be in MiganCore workspace
□ docker compose config                # Compose file must be valid
□ grep -q '"80:80"' docker-compose.yml # Caddy must NOT bind 80
□ grep -q '"443:443"' docker-compose.yml # Caddy must NOT bind 443
□ git diff --name-only | grep -vE '^docs/|^scripts/|^api/|^core/|^memory/|^tools/|^training/|^migrations/|^tests/' # No forbidden paths
□ systemctl is-active nginx >/dev/null # nginx must stay running
□ nginx -t                             # nginx config must be valid
```

---

## 4. DOCKER COMPOSE PROFILE POLICY

Services are grouped by profile. Only start what you need:

| Profile | Services | When to Use |
|---------|----------|-------------|
| *(default)* | postgres, redis, qdrant, ollama, api | Always on |
| `memory` | letta | When memory layer needed |
| `workers` | worker_code, worker_web, worker_research | When async tasks needed |
| `observability` | langfuse | When tracing LLM calls |
| `training` | mlflow/studio (future) | During training weeks |
| `ingress` | caddy | **DISABLED on shared VPS** — only for dedicated VPS |

**Command examples:**
```bash
# Core only
docker compose up -d

# Core + memory
docker compose --profile memory up -d

# Core + workers
docker compose --profile workers up -d

# Core + observability
docker compose --profile observability up -d

# NEVER run ingress profile on shared VPS:
# docker compose --profile ingress up -d  ❌ FORBIDDEN
```

---

## 5. NGINX INTEGRATION POLICY

On this shared VPS, nginx aaPanel is the **sole edge reverse proxy**. MiganCore services bind to `127.0.0.1` only.

### 5.1 Adding a New Subdomain

1. Create nginx vhost in aaPanel:
   ```bash
   /www/server/panel/vhost/nginx/api.migancore.com.conf
   ```

2. Test config:
   ```bash
   nginx -t
   ```

3. Reload nginx:
   ```bash
   systemctl reload nginx
   ```

4. **Never** edit existing vhosts for SIDIX/Ixonomic domains.

### 5.2 Required Proxy Headers

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_read_timeout 300s;
proxy_send_timeout 300s;
proxy_buffering off;
```

---

## 6. SECRET MANAGEMENT POLICY

| Rule | Enforcement |
|------|-------------|
| Never commit `.env` | `.gitignore` |
| Never commit JWT keys | Keys at `/etc/ado/keys/` (VPS only) |
| Never hardcode passwords in scripts | Use `openssl rand` generation |
| Rotate secrets if leaked | `adoctl backup` before rotation |
| Scan before commit | `git-secrets` or `truffleHog` (future) |

---

## 7. INCIDENT RESPONSE

If an agent accidentally touches a forbidden zone:

1. **STOP** — do not continue
2. **Assess** — what was modified? Run `git diff` or `docker ps`
3. **Alert** — notify Fahmi immediately
4. **Restore** — use backup if available (`adoctl backup`)
5. **Document** — add to `docs/VPS_ECOSYSTEM_MAP.md` red flags section

---

## 8. CONTRACT VERSIONING

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-03 | Initial contract based on GPT-5.5 architecture review |

---

> **"Boundaries exist not to limit creativity, but to protect the ecosystem that enables it."**
