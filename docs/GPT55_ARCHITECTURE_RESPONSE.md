# GPT-5.5 Architecture Review Response
**Date:** 2026-05-03  
**Reviewer:** GPT-5.5 (via Fahmi Wol)  
**Implementor:** Kimi Code CLI  
**Status:** Approved for implementation  

---

## EXECUTIVE SUMMARY
Rekomendasi utama: jangan lawan aaPanel nginx. Jadikan nginx sebagai edge resmi untuk VPS ini, matikan Caddy dari jalur produksi, dan publish service MiganCore hanya lewat port 127.0.0.1. Kedua, pertahankan dual Ollama untuk Sprint 1 karena host Ollama adalah production dependency SIDIX, tapi ubah MiganCore Ollama menjadi lazy-loaded dan dikontrol lewat inference gateway. Ketiga, sebelum Day 3 lanjut, lakukan agent-proofing operasional: rotate secret yang sudah terlanjur hardcoded di script, disable Caddy, perbaiki Day 2 script, dan buat guardrail adoctl agar agent tidak menyentuh SIDIX/Ixonomic/aaPanel sembarangan.

---

## 1. REVERSE PROXY: Nginx Edge, MiganCore Local Ingress

### Evaluasi:
- **A**, stop nginx dan pindah ke Caddy: reject. Ini melanggar zero downtime.
- **B**, hapus Caddy dan pakai nginx: pilihan MVP terbaik.
- **C**, nginx forward ke Caddy 8080/8443: bagus nanti, tapi terlalu banyak moving parts sekarang.
- **D**, aaPanel nginx vhost langsung ke MiganCore: recommended for Day 3.
- **E**, creative fallback: Cloudflare Tunnel khusus migancore.com, tanpa menyentuh port 80/443. Ini bagus untuk canary/preview, tapi jangan jadikan dependency utama dulu.

### Implementasi yang dipilih: D sekarang, C/E nanti.

Ubah compose agar service publik bind ke localhost saja:
```yaml
api:
  ports:
    - "127.0.0.1:18000:8000"

langfuse:
  ports:
    - "127.0.0.1:13001:3000"
```

Jangan expose Postgres, Redis, Qdrant, Letta, Ollama ke publik. Untuk app dan studio, jangan buat vhost aktif sampai servicenya benar-benar ada, atau buat placeholder 503 yang eksplisit.

### Contoh nginx block untuk api.migancore.com:
```nginx
server {
    listen 80;
    server_name api.migancore.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.migancore.com;

    ssl_certificate     /www/server/panel/vhost/cert/api.migancore.com/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/api.migancore.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:18000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }
}
```

**Operational rule:** backup nginx config, add only MiganCore vhost, run nginx -t, then reload. Never edit existing SIDIX/Ixonomic vhosts.

---

## 2. OLLAMA STRATEGY: Dual Now, Broker Later

Dual Ollama is sustainable for Sprint 1 if controlled. Host Ollama belongs to SIDIX and must be treated as forbidden production infrastructure. Container Ollama belongs to MiganCore and should stay isolated.

### Change MiganCore Ollama from always-warm to lazy:
```yaml
environment:
  OLLAMA_NUM_PARALLEL: "1"
  OLLAMA_MAX_LOADED_MODELS: "1"
  OLLAMA_KEEP_ALIVE: "10m"
  OLLAMA_MAX_QUEUE: "32"
```

Current KEEP_ALIVE=24h and NUM_PARALLEL=2 are too expensive for a shared 32GB VPS. Ollama docs confirm parallelism increases memory pressure because context allocation scales with parallel requests.

### Long-term: build llm-router inside MiganCore. It routes requests to:
- `migan-local`: container Ollama
- `sidix-host`: host Ollama, read-only integration only if explicitly approved
- `remote-gpu`: RunPod or future GPU endpoint
- `fallback-small`: Qwen 0.5B for classification/tool routing

Do not unify by moving SIDIX to container now. That turns a strategic cleanup into a production migration.

---

## 3. CONTAINER ARCHITECTURE

Nine services are fine conceptually, but not all should run all the time. Split with Docker Compose profiles:

```
always on: postgres, redis, qdrant, ollama, api
profile memory: letta
profile workers: Celery workers
profile observability: langfuse
profile training: MLflow/studio
profile ingress: Caddy, disabled on this VPS
```

Also verify whether current deploy.resources.limits is enforced in this Docker Compose mode. If not, add explicit runtime limits or use a tested compose invocation. Do not assume memory limits are active.

**Important current mismatch:** api/Dockerfile expects main:app, but api/main.py does not exist yet. docker compose up api will fail until FastAPI scaffold exists.

---

## 4. AGENT-PROOFING

Create a machine-readable boundary contract:

```yaml
forbidden_paths:
  - /opt/sidix
  - /root/sidix
  - /var/www/ixonomic
  - /www/server/panel
forbidden_services:
  - ollama.service
  - redis-server.service
  - postgresql@14-main
  - nginx
allowed_workspace: /opt/ado
allowed_public_ports:
  - 127.0.0.1:18000
```

Then build `scripts/adoctl` as the only blessed interface:
```bash
adoctl ps
adoctl logs api
adoctl deploy api
adoctl nginx-test
adoctl health
adoctl model-status
```

Add preflight checks before every deploy:
- current directory must be /opt/ado
- Caddy must not bind 80/443
- no diff touches forbidden paths
- no systemctl stop/restart nginx/ollama/postgres/redis
- docker compose config passes
- nginx -t passes before reload
- run secret scan before commit

Terraform/Pulumi is premature for aaPanel. GitOps with Argo/Flux is also overkill. Start with versioned scripts, generated nginx snippets, backups, and audit logs.

---

## 5. CREATIVE IDEAS

1. **MiganCore Immune System:** every deploy records RAM, ports, running containers, nginx config hash, and forbidden process status before/after.
2. **Hibernation Scheduler:** unload Ollama, pause Langfuse, and scale workers down when idle.
3. **Inference Broker:** route easy tasks to 0.5B, serious reasoning to 7B, training/eval to RunPod.
4. **Lineage Ledger:** every child agent, model version, prompt constitution, and infra decision becomes an event in Postgres.
5. **Shadow Evolution:** candidate models receive mirrored traffic but never respond to users until eval passes.

---

## 6. RAM OPTIMIZATION

Highest savings:
- Ollama keep-alive 24h -> 10m: saves about 5-7GB when idle.
- OLLAMA_NUM_PARALLEL=2 -> 1: saves KV/context memory.
- Langfuse off by default: saves about 0.5-1.5GB.
- Start only one Celery worker until tools are real: saves about 1-2GB.
- Postgres initial tuning should be conservative, not a reserved 4GB assumption.
- Qdrant can stay small until real vectors exist; enable on-disk/quantization later.
- MLflow/studio should not run before training week.

---

## 7. IMPLEMENTATION ROADMAP

### Day 3 first priorities:
1. Rotate secrets immediately. scripts/day1-setup.sh contains real-looking hardcoded passwords and was committed.
2. Disable Caddy in production compose via profile or remove ports.
3. Fix scripts/day2-setup.sh; it waits for Ollama healthy, but the healthcheck was removed.
4. Add FastAPI api/main.py with /health.
5. Expose API only on 127.0.0.1:18000.
6. Add nginx vhost for api.migancore.com, test, reload.
7. Benchmark MiganCore Ollama with lazy keep-alive and record RAM.

### Day 4-7:
1. Auth + JWT + RLS tests.
2. Add adoctl.
3. Add secret scanning.
4. Add backup script.
5. Add docs/INFRA_BOUNDARY_CONTRACT.md.

---

## 8. RED FLAGS / THINGS MISSED

1. Hardcoded secret in scripts/day1-setup.sh is the biggest immediate security issue.
2. day2-setup.sh is stale after Ollama healthcheck removal.
3. Caddy references frontend and studio, but those services do not exist in compose.
4. api/main.py does not exist, so API container cannot run yet.
5. Letta port may be wrong: docs/env say 8283, audit shows container 8083/tcp. Verify before wiring API.
6. RLS is enabled on some tables without complete policies, which may block app access or behave inconsistently.
7. CONTEXT.md and audit docs disagree on current service state. Treat VPS_ECOSYSTEM_MAP.md as operational source of truth and update CONTEXT.md.

---

*Sources checked: Caddy Automatic HTTPS, Ollama FAQ, Docker Compose profiles, K3s requirements.*
