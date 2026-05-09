# CONTEXT.md — MiganCore Project Live State
**Last Updated:** 2026-05-09 02:45 WIB by Kimi Code CLI (Executor Session — SP-104 Test Stabilization Complete)
**Location:** Project root (shared across all repos)
**Protocol:** Baca ini SEBELUM kerja. Update SETELAH kerja.

---

## KOREKSI ARSITEKTUR (Wajib Dipahami)

> **migancore.com = SATU-SATUNYA tempat development & deployment.**
> Semua backend, model, memory, training, dan API berjalan di sini.

**sidixlab.com, mighan.com, tiranyx.com** adalah **consumer/distribution channel** yang mengakses produk via `api.migancore.com`. Mereka TIDAK menghosting services sendiri.

```
migancore.com (Central Hub)
├── api.migancore.com     → API Gateway (FastAPI)
├── app.migancore.com     → Dashboard / Studio
├── lab.migancore.com     → Observability (Langfuse)
└── studio.migancore.com  → Training / MLflow

Consumer Channels (hit api.migancore.com)
├── sidixlab.com          → Research Lab UI
├── mighan.com            → Clone Platform UI
└── tiranyx.com           → Project Governance UI
```

---

## CURRENT STATUS
**Sprint:** Executor Remap Session — Day 0 of New Phase
**Active Milestone:** M0 — Foundation Hardening
**Phase:** INFRASTRUCTURE FIRST (Brain training PAUSED)

### Kenapa Brain Training Dipause?
- 5 cycles gagal berturut-turut sejak Day 60 (Cycles 4, 7, 7b, 7c)
- Root cause: data pipeline rusak (99% synthetic), ORPO wrong tool, identity fragile
- Solusi: Bangun infrastruktur solid DULU, baru train lagi dengan data berkualitas
- Referensi: `docs/MIGANCORE_ARCHITECTURE_REMAP_v2026.md`

---

## WHAT'S WORKING ✅
- **Production Live:** API v0.5.16, migancore:0.3 (Cycle 3) serving traffic
- **FastAPI Gateway:** 12 routers, JWT RS256, multi-tenant RLS
- **Chat:** SSE streaming, tool loop, multimodal (text + image + voice)
- **Memory:** Redis K-V + Qdrant hybrid BM42 + Postgres
- **Training Scripts:** 30+ scripts (SimPO/ORPO/SFT), VastAI/RunPod support
- **License:** HMAC-SHA256 validator, clone deployment endpoint
- **Frontend:** chat.html (3,543 lines), landing.html, dashboard.html
- **MCP Server:** Streamable HTTP, smithery.ai registered
- **VPS:** 72.62.125.6, containers UP, UFW + fail2ban active
- **Domain:** migancore.com, api., app., lab. LIVE

## WHAT'S IN PROGRESS 🔵
- **M0.1:** Alembic migrations (belum mulai)
- **M0.2:** Test suite v1 (belum mulai)
- **M0.3:** CI/CD pipeline (belum mulai)
- **M0.4:** Context preservation protocol (sedang dibuat — dokumen ini)
- **M0.5:** Observability stack (belum mulai)
- **Dokumen:** Architecture remap, roadmap, daily protocol (sedang dibuat)

## WHAT'S BLOCKED 🔴
- **Cycle 5+ Training:** DIPAUSE sampai M2 (Multi-Loss Engine) selesai
- **White-Label Launch:** DIPAUSE sampai M3 (Identity Anchor SFT) selesai
- **Clone Mechanism:** DIPAUSE sampai M5 (Clone & White-Label phase)

## WHAT'S BROKEN / FRAGILE ⚠️
- **User Feedback:** Thumbs UI ada tapi backend worker MISSING. Hanya 1 thumb_up di DB.
- **Owner Data Pathway:** Tidak ada endpoint sama sekali.
- **Self-Growth:** 50% sample rate, idle, 18 pairs total.
- **Teacher Distillation:** Manual, 10 pairs total.
- **Identity:** Tanpa SOUL.md prompt = "Saya Qwen, Alibaba Cloud".
- **Migrations:** Manual SQL only. Alembic imported tapi tidak dipakai.
- **Tests:** 169 passed, 0 failed, coverage 66.12% (Docker Test Runner SP-104 stable)
- **Alembic:** Schema drift (6 discrepancies) documented, not yet migrated
- **Feedback service:** Internal `session.commit()` — caller-managed refactor deferred to M1
- **Platform Repo:** Empty directories. Misleading.
- **CI/CD:** Tidak ada. Deploy manual.

---

## RECENT DECISIONS (last 7 days)
- **2026-05-08:** STOP brain training, fokus infrastructure (Executor remap)
- **2026-05-08:** Multi-loss arsenal: SFT/DPO/KTO/SimPO (bukan ORPO-only)
- **2026-05-08:** SFT identity anchor FIRST sebelum white-label
- **2026-05-08:** 30% old / 70% new replay buffer
- **2026-05-08:** Teacher distillation $5/day cap
- **2026-05-08:** Qwen2.5-7B tetap base (upgrade ke Qwen3-8B di Phase 5)
- **2026-05-07:** Cycle 4 ROLLBACK — migancore:0.3 stays production
- **2026-05-07:** KB v1.3 committed
- **2026-05-05:** Beta Launch — 12-dimension QA PASS

---

## KNOWN ISSUES
- Docker Compose YAML anchor (`*api_env`) needs fixing for worker services
- Letta 0.6.0 deferred, Redis used for Tier 1 memory
- VPS shared with sidix/tiranyx — CPU contention during synthetic generation + user chat
- Schema drift risk: no Alembic yet; manual SQL migration discipline required
- Context loss risk: 150+ docs, no single source of truth untuk operational status
- Platform/community repos empty — investor/contributor misleading
- Documentation inflation: 150+ markdown docs vs 1 test file

---

## NEXT PRIORITY (M0 — Foundation Hardening)
1. **Hari 1-2:** Alembic migrations + test suite v1 ✅ TEST SUITE DONE (169 pass, 66% cov)
2. **Hari 3:** CI/CD pipeline (GitHub Actions)
3. **Hari 4:** Context preservation system + daily protocol
4. **Hari 5-7:** Observability stack (Prometheus + Grafana)
5. **Hari 8-14:** Data pipeline plumbing (M1)

---

## ENVIRONMENT STATE
- Ollama: RUNNING (migancore:0.3 production)
- Postgres: RUNNING (healthy)
- Redis: RUNNING
- Qdrant: RUNNING
- API: v0.5.16 LIVE
- Core Brain agent_id: LIVE
- Current active model_version: migancore:0.3 (Cycle 3, weighted_avg 0.9082)
- Vast.ai credit: ~$6.90 remaining
- GitHub repos: ✅ SYNCED
- Domain: ✅ REGISTERED (Hostinger)
- VPS IP: 72.62.125.6
- aaPanel: https://72.62.125.6:39206/a20d5b35
- RunPod: $0.16 remaining (backup only)

---

## DOCUMENTATION SOURCE OF TRUTH
**Root Master doc/:** Strategic foundation (SOUL, VISION, PRD, ARCHITECTURE, ERD, SPRINT, PROTOCOL, RISK)
**docs/MIGANCORE_ARCHITECTURE_REMAP_v2026.md:** Arsitektur remap baru — MANDATORY baca sebelum eksekusi
**docs/MIGANCORE_ROADMAP_MILESTONES.md:** Roadmap dan milestones — update weekly
**migancore/docs/:** Daily operational docs, plans, retros, research
**migancore/docs/logs/daily/:** Daily activity logs
**Jika konflik:** docs/MIGANCORE_ARCHITECTURE_REMAP_v2026.md wins untuk arsitektur; docs/MIGANCORE_ROADMAP_MILESTONES.md wins untuk timeline.

---

## AGENT HANDOFF TEMPLATE
```markdown
## HANDOFF — [Agent Lama] → [Agent Baru]
**Tanggal:** [YYYY-MM-DD HH:MM]
**Branch:** [branch name]
**Commit:** [hash]

**Yang Selesai:**
- [task] — [file yang diubah]

**State Sekarang:**
- [service] : [running/stopped/error]
- [file] : [state]

**Yang Harus Dilanjutkan:**
1. [task pertama]
2. [task kedua]

**Watch Out:**
- [gotcha 1]
- [gotcha 2]

**Keputusan Baru:**
- [decision] — [reasoning singkat]

**Context Updated:**
- CONTEXT.md di-update dengan [apa]
```

---

*File ini HARUS dibaca oleh setiap agent sebelum mulai kerja. Update minimal sekali sehari. Jangan biarkan outdated.*
