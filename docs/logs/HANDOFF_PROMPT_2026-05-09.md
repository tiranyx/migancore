# HANDOFF PROMPT — MiganCore
**Salin seluruh isi file ini ke prompt chat baru.**

---

## IDENTITAS PROYEK
Kamu adalah **Kimi Code CLI Executor** untuk **MiganCore** — Autonomous Digital Organism (ADO) berbasis LLM Qwen2.5-7B dengan arsitektur self-evolving. Tech stack: FastAPI + PostgreSQL 16 (pgvector) + Redis + Qdrant + SQLAlchemy 2.0 (async) + Docker.

**Koreksi arsitektur wajib:**
- `migancore.com` = satu-satunya tempat development & deployment (central hub)
- `sidixlab.com`, `mighan.com`, `tiranyx.com` = consumer channel yang hit `api.migancore.com`
- Semua backend, model, memory, training berjalan di VPS Hetzner Singapore `72.62.125.6`

---

## STATUS TERKINI (2026-05-09 02:45 WIB)

### ✅ BARU SELESAI — SP-104 Docker Test Runner Stabilization
- **169 tests passed, 0 failed, 0 errors**
- **Coverage: 66.12%** (target ≥40%)
- Semua integration tests stabil: `test_rls.py`, `test_feedback.py`, `test_hafidz_integration.py`

### 🔵 ACTIVE MILESTONE — M0 Foundation Hardening
| SP | Task | Status |
|---|---|---|
| SP-001 | Alembic migrations (init.sql + patches 004-025) | ⬜ BELUM MULAI — ini prioritas berikutnya |
| SP-002 | Test suite v1 (169 pass, 66% cov) | ✅ SELESAI |
| SP-003 | CI/CD pipeline (GitHub Actions) | ⬜ BELUM MULAI |
| SP-104 | Docker Test Runner (feedback + hafidz + RLS) | ✅ SELESAI |

### 🔴 M1 IDENTITY ANCHOR SFT (Tertunda)
- 200 pairs, rank 32, cosine sim ≥0.85
- **Blocker:** SP-010 (SFT pipeline code) belum siap

---

## FILE KRITIS YANG BARU DIUBAH

```
api/tests/integration/conftest.py          ← Fixture transaction model (BACA DULU)
api/tests/integration/test_feedback.py     ← Idempotent tenant + RLS re-set
api/tests/test_rls.py                      ← Raw SQL scalar queries
api/scripts/init_test_db.py                ← Idempotent role + DROP POLICY IF EXISTS
api/models/datasets.py                     ← ORM stub untuk FK drift
api/services/feedback.py                   ← Internal commit() masih ada (deferred fix)
docker-compose.test.yml                    ← Test stack (postgres_test, redis_test, qdrant_test)
```

---

## KEPUTUSAN TEKNIS PENTING (Jangan Dilanggar)

1. **TIDAK BOLEH pakai `session.begin()` / `begin_nested()` context manager di test fixture** kalau service layer memanggil `session.commit()`. SQLAlchemy 2.0 akan raise `InvalidRequestError: Can't operate on closed transaction inside context manager`.
   - **Solusi:** Fixture `db_session` pakai model tanpa CM, cleanup via explicit DELETE + rollback safety.

2. **`ado_app` (non-superuser) TIDAK BOLEH `drop_all`** — tabel dibuat oleh superuser `postgres` via `init_test_db.py`, owner = postgres.
   - **Solusi:** `db_engine` fixture TIDAK melakukan `drop_all` di teardown. Database di-reset via container lifecycle.

3. **`NullPool` WAJIB** untuk asyncpg + pytest-asyncio — menghindari `InterfaceError: another operation is in progress`.

4. **Windows dev WAJIB pakai Docker** — Python 3.14 dependency hell. Jangan coba install lokal.

5. **Git workflow:** Push ke `tiranyx/migancore` main → VPS `git pull` → `docker compose -f docker-compose.test.yml up --build api_test --abort-on-container-exit`

---

## TEST COMMAND (Copy-Paste ke VPS)

```bash
ssh sidix-vps "cd /opt/ado && git pull origin main && docker compose -f docker-compose.test.yml up --build api_test --abort-on-container-exit"
```

---

## TODO PRIORITAS (Urut Kerjakan)

1. **SP-001: Alembic migrations** — Convert `init.sql` + patches 004-025 ke proper Alembic revisions. Ini blocker terakhir M0.
2. **SP-003: CI/CD pipeline** — GitHub Actions: test → build → deploy staging.
3. **Fix cosmetic:** `/bin/bash: line 58: [: -ne: unary operator expected` di `docker-compose.test.yml` coverage block.
4. **M1: Identity Anchor SFT** — Setelah SP-010 (SFT pipeline) siap.

---

## WATCH OUT / GOTCHAS

- **Schema drift:** Ada 6 discrepancies antara model ORM dan DB aktual. `init_test_db.py` menangani ini, tapi Alembic perlu aware.
- **PAT GitHub:** Tidak punya `workflow` scope → GHA changes harus via bundle → SCP → VPS import.
- **VastAI budget:** ~$6.90 tersisa (cukup 1-2 training run).
- **Feedback service:** `record_feedback` masih memanggil `session.commit()` internal. Refactor ke caller-managed transaction deferred ke M1.
- **RLS context:** `set_config('app.current_tenant', ..., true)` pakai `true` (local/transaction-level). Setelah `commit`, context hilang — harus re-set.

---

## DOKUMEN WAJIB BACA (Jika Bingung)

1. `docs/MIGANCORE_ARCHITECTURE_REMAP_v2026.md` — Arsitektur remap (mandatory)
2. `docs/MIGANCORE_ROADMAP_MILESTONES.md` — Timeline dan milestones
3. `docs/logs/handoff-2026-05-09.md` — Handoff log lengkap sesi terakhir
4. `docs/EVALUATION_20260509_0800_WIB.md` — Strategic audit 10 poin

---

## INFORMASI KONTAK / AKSES

- **VPS:** Hetzner Singapore `72.62.125.6`, user `root`, SSH config `sidix-vps`
- **aaPanel:** `https://72.62.125.6:39206/a20d5b35`
- **GitHub:** `https://github.com/tiranyx/migancore`
- **Branch aktif:** `main`

---

*Paste prompt ini ke chat baru. Semua konteks ada di sini.*
