## 🎯 SSOT — SINGLE SOURCE OF TRUTH (BACA SEBELUM APAPUN)

**Live URL:** https://app.migancore.com/backlog.html

Semua vision, backlog, journal, dan lessons MiganCore TERPUSAT di SSOT admin backlog. **Jangan cari di folder lain**.

```
🌟 VISION   (11 docs)  — SOUL, DIRECTION_LOCK, NORTHSTAR, all doctrines
📋 BACKLOG  (142 docs) — SPRINT_*, DAY*_PROGRESS, M15/16/17, CYCLE_*, ROADMAP
📖 JOURNAL  (17 docs)  — FOUNDER_JOURNAL, MASTER_HANDOFF, AGENT_SYNC/
🧠 LESSONS  (20 docs)  — LESSONS_*, _ANALYSIS, EVAL_, POSTMORTEM, RESEARCH
📂 OTHER    (65 docs)  — sisanya
```

**Mandatory protocol untuk SEMUA agent (Claude/Codex/Kimi/future):**

1. **Sebelum strategic decision** → buka tab Vision, baca SOUL/DIRECTION_LOCK/NORTHSTAR.
2. **Sebelum tulis doc baru** → pastikan filename match auto-classify pattern (lihat tab Other supaya doc baru masuk Vision/Backlog/Journal/Lessons).
3. **Setelah selesai kerjaan** → tulis ke `docs/AGENT_SYNC/HANDOFF_YYYY-MM-DD_TOPIC.md` (auto masuk Journal tab).
4. **Saat dapat lessons baru** → tulis ke `docs/LESSONS_TOPIC.md` atau `docs/POSTMORTEM_CYCLE_DATE.md` (auto masuk Lessons tab).
5. **JANGAN bikin admin dashboard duplikat** — extend SSOT existing via tabs/buckets.

Source dir: `/opt/ado/docs/*.md` (canonical) → mounted di container `/app/docs:ro` → served via `api/routers/admin_docs.py`.

API endpoints:
- `GET /v1/admin/docs/stats` — total + per-tab counts
- `GET /v1/admin/docs?tab=vision` — filtered list per tab
- `GET /v1/admin/docs/file?path=PATH` — render markdown content

Auth: `X-Admin-Key` header (sama dengan admin router lain).

---
