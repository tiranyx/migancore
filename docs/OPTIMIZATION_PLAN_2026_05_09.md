# ⚡ OPTIMIZATION PLAN — Full Stack Audit & Execution

> **Tanggal:** 9 Mei 2026, 01:45 WIB (Jakarta Time, UTC+7)  
> **Scope:** Repo → GitHub → VPS → Backend → Frontend  
> **Status:** Audit Complete | Execution In Progress

---

## 📊 AUDIT RESULTS

### 1. REPO LOCAL (Windows)
| Metrik | Nilai | Status |
|--------|-------|--------|
| Git objects | 10.3 MiB | 🟢 Good |
| Working tree | ~96 MB | 🟡 Acceptable |
| .gitignore coverage | Comprehensive | 🟢 Good |
| File besar terlacak | Tidak ditemukan >1MB | 🟢 Good |

**Finding:** Repo sebenarnya bersih. File besar (5MB pydantic_core dll) ada di `.venv` yang sudah di-.gitignore.

### 2. GITHUB
| Metrik | Nilai | Status |
|--------|-------|--------|
| Commit history | Linear, clean | 🟢 Good |
| Workflow files | 2 files | 🟢 Good |
| Docs | 4 files baru | 🟢 Good |
| PAT issue | Fine-grained vs org | 🟡 Workaround via VPS SSH |

### 3. VPS / SERVER
| Metrik | Nilai | Status |
|--------|-------|--------|
| Disk usage | 124G / 388G (32%) | 🟢 Good |
| RAM usage | 4.7G / 31G (15%) | 🟢 Good |
| Load average | 0.06 | 🟢 Idle |
| Docker images | 19GB total | 🔴 Too large |
| Build cache | 3.23GB (api image) | 🔴 Bloated |

### 4. BACKEND (API Container)
| Metrik | Nilai | Target | Status |
|--------|-------|--------|--------|
| Image size | 752MB | <400MB | 🔴 2× target |
| Container RSS | 1.85GB | <1GB | 🔴 2× target |
| Memory limit | 2GB | 4GB | 🔴 Too tight |
| CPU usage | 0.16% | — | 🟢 Idle |
| Startup time | ~25s | <10s | 🔴 Slow |

**Layer Breakdown:**
```
apt-get install + npm install    1.56GB  ← 🔴 biggest bloat
pip install requirements         776MB   ← 🔴 heavy ML deps
python:3.11-slim base            ~135MB  ← 🟢 normal
COPY application code            1.1MB   ← 🟢 tiny
```

**Memory Breakdown (1.85GB RSS):**
```
Python uvicorn main process      ~1.78GB  ← embedding models, langchain, etc.
Node.js hyperx-mcp.js            ~67MB
Overhead                         ~3MB
```

### 5. FRONTEND
| Metrik | Nilai | Status |
|--------|-------|--------|
| Files exist | chat.html, dashboard.html, landing.html | 🟢 Good |
| Web server | None serving them | 🔴 Missing |
| Nginx config | Empty / missing | 🔴 Missing |
| CDN / caching | None | 🔴 Missing |
| Service worker | sw.js exists | 🟢 Good (but not served) |

---

## 🎯 OPTIMIZATION PRIORITIES

### P0 — Critical (Deploy blocker / OOM risk)
1. **Naikkan memory limit API** dari 2GB → 4GB (prevent OOM)
2. **Docker multi-stage build** — pisah build deps vs runtime (target <400MB)
3. **Setup nginx reverse proxy** — serve frontend + API + SSL

### P1 — High (Performance & cost)
4. **Docker prune** — hapus build cache tak terpakai (hemat ~3GB)
5. **Lazy loading embedding models** — jangan load semua di startup
6. **Frontend optimization** — gzip, cache headers, minify

### P2 — Medium (Developer experience)
7. **Git history cleanup** — kalau ada blob besar di history
8. **CI/CD cache** — cache pip deps di GitHub Actions
9. **Health check di docker compose** — auto-restart kalau unhealthy

---

## 📋 EXECUTION CHECKLIST

- [ ] P0.1 Memory limit 2GB → 4GB
- [ ] P0.2 Multi-stage Dockerfile
- [ ] P0.3 Nginx reverse proxy + SSL
- [ ] P1.1 Docker system prune
- [ ] P1.2 Lazy embedding loader
- [ ] P1.3 Frontend gzip + cache
- [ ] P2.1 Git history audit
- [ ] P2.2 CI cache
- [ ] P2.3 Docker healthcheck
