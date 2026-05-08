# SPRINT 0: FOUNDATION LOCK -- 100% Confidence Tasks Only
**Sprint Goal:** Bangun fondasi infrastruktur yang 100% deterministik. Tidak ada eksperimen. Tidak ada training. Hanya engineering yang pass/fail jelas.
**Sprint Duration:** 7 hari (9 Mei -- 15 Mei 2026)
**Committed By:** Executor Day 0 (Kimi Code CLI)
**Lock Date:** 2026-05-08

---

## FILOSOFI SPRINT INI

> Saya yakin 100% bisa menyelesaikan task ini dalam waktu yang dicommit. Kalau gagal, itu karena saya bodoh, bukan karena tasknya ambiguous.

Task yang MASUK sprint ini punya karakteristik:
- Pure engineering (code, config, SQL)
- Deterministic pass/fail
- Tidak bergantung hasil eksperimen ML
- Tidak bergantung perilaku user
- Tidak perlu diagnose masalah yang belum jelas root cause-nya

Task yang KELUAR dari sprint ini:
- Training (SFT/DPO/KTO) -- hasil tidak deterministic
- Fix feedback pipeline -- perlu investigation dulu, root cause belum jelas
- Clone E2E deploy -- perlu VPS test target, belum ada
- Owner data pathway -- perlu understand existing upload flow dulu

---

## SPRINT BACKLOG (Committed)

### SP-001: Alembic Migrations -- Convert init.sql + patches to revisions
**Confidence:** 100% | **ETA:** 2 hari (Day 1-2)
**Owner:** Backend Agent
**DoD:**
- [ ] lembic init di migancore/api/
- [ ] Convert init.sql ke lembic revision --autogenerate baseline
- [ ] Convert patches 004-025 ke sequential revisions
- [ ] lembic upgrade head pass di container lokal
- [ ] lembic downgrade base pass di container lokal
- [ ] Document: MIGRATIONS.md -- cara buat revision baru

**Why 100%:** Alembic adalah tool mature. Schema sudah ada di PostgreSQL. Auto-generate dari SQLAlchemy models = deterministic.

---

### SP-002: Test Suite v1 -- 50+ tests, pytest pass 100%
**Confidence:** 100% | **ETA:** 2 hari (Day 2-3)
**Owner:** QA Agent
**DoD:**
- [ ] pytest runner configured with pytest.ini
- [ ] Test DB setup: SQLite in-memory atau test Postgres container
- [ ] Auth tests: register, login, JWT validation, RLS isolation (expand existing)
- [ ] API tests: health, agents CRUD, chat endpoint (mocked LLM)
- [ ] License tests: mint, validate, tier constraints, expiry grace
- [ ] Clone manager tests: dry-run pipeline, template rendering
- [ ] Coverage >= 40% (report via pytest-cov)
- [ ] All tests pass: pytest -x exit 0

**Why 100%:** FastAPI + pytest adalah kombinasi standard. Endpoint sudah ada. Tinggal tulis assertions. RLS test sudah ada 1 file = template jelas.

---

### SP-003: CI/CD Pipeline -- GitHub Actions
**Confidence:** 100% | **ETA:** 1 hari (Day 4)
**Owner:** DevOps Agent
**DoD:**
- [ ] .github/workflows/ci.yml: test + lint + coverage pada setiap PR
- [ ] .github/workflows/deploy-staging.yml: auto-deploy ke VPS staging (atau Docker Hub push)
- [ ] Secret management: DOCKER_USERNAME, DOCKER_PASSWORD di GitHub Secrets
- [ ] Branch protection: PR harus pass CI sebelum merge ke main
- [ ] Slack/Discord webhook notifikasi (opsional, nice-to-have)

**Why 100%:** GHA adalah standard industri. Pattern sudah jelas. Tidak ada custom logic -- hanya orchestrate pytest + docker build + ssh deploy.

---

### SP-004: Hafidz Ledger -- Migration + Skeleton Endpoint
**Confidence:** 100% | **ETA:** 1 hari (Day 5)
**Owner:** Backend Agent
**DoD:**
- [ ] Alembic revision: CREATE TABLE hafidz_contributions (schema dari locked doc)
- [ ] POST /hafidz/contribute skeleton endpoint (accept JSON, validate license signature, store raw)
- [ ] GET /hafidz/contributions admin endpoint (list dengan filter)
- [ ] GET /hafidz/summary endpoint (aggregate per child)
- [ ] Tests: contribution CRUD, deduplication hash check, unauthorized rejected

**Why 100%:** Schema sudah final di locked doc. FastAPI CRUD endpoint adalah boilerplate. License signature validation sudah ada di license.py. Hanya wiring.

---

### SP-005: Context Preservation Protocol -- Finalize & Lock
**Confidence:** 100% | **ETA:** 0.5 hari (Day 6)
**Owner:** Docs Agent
**DoD:**
- [ ] docs/MIGANCORE_DAILY_PROTOCOL.md sudah ada -- verify completeness
- [ ] CONTEXT.md auto-update script (extract commit messages + task status)
- [ ] Agent onboarding checklist: 6 dokumen wajib dibaca
- [ ] Handoff template: markdown file yang di-generate per session

**Why 100%:** Dokumentasi dan template adalah pure writing. Tidak ada runtime dependency.

---

### SP-006: Observability Skeleton -- Prometheus metrics endpoint
**Confidence:** 100% | **ETA:** 0.5 hari (Day 6-7)
**Owner:** DevOps Agent
**DoD:**
- [ ] prometheus-client integrated di FastAPI
- [ ] /metrics endpoint expose: request_count, request_latency, active_agents, db_connections
- [ ] Custom metrics: training_cycle_status, license_validation_total
- [ ] Docker compose update: add prometheus + grafana services (optional flag)

**Why 100%:** Prometheus client adalah library standard. Metrics endpoint adalah boilerplate. Grafana provisioning via config file = deterministic.

---

## SPRINT SCHEDULE

| Hari | Tanggal | Task Utama | Deliverable | Confidence |
|---|---|---|---|---|
| Day 1 | Jumat, 9 Mei | SP-001 start | Alembic init + baseline revision | 100% |
| Day 2 | Sabtu, 10 Mei | SP-001 complete, SP-002 start | All patches converted to revisions | 100% |
| Day 3 | Minggu, 11 Mei | SP-002 continue | 30+ tests written | 100% |
| Day 4 | Senin, 12 Mei | SP-002 complete, SP-003 start | 50+ tests pass, CI/CD config | 100% |
| Day 5 | Selasa, 13 Mei | SP-003 complete, SP-004 start | GHA green, Hafidz table live | 100% |
| Day 6 | Rabu, 14 Mei | SP-004 complete, SP-005 + SP-006 start | /hafidz endpoints tested | 100% |
| Day 7 | Kamis, 15 Mei | SP-005 + SP-006 complete, Sprint Review | All M0 DoD checked | 100% |

**Sprint Review (Day 7):**
- Demo: lembic upgrade head -> pytest -x -> curl /metrics -> curl /hafidz/contribute
- Go/No-Go untuk M1 Data Pipeline

---

## DEFINITION OF DONE (Sprint Level)

- [ ] lembic upgrade head dan lembic downgrade base pass tanpa error
- [ ] pytest exit 0 dengan >= 50 tests, coverage >= 40%
- [ ] GitHub Actions CI pass pada setiap PR ke main
- [ ] POST /hafidz/contribute menerima JSON dan menyimpan ke DB
- [ ] /metrics endpoint expose Prometheus metrics
- [ ] Semua dokumentasi locked dan cross-referenced

---

## EXPLICITLY NOT IN THIS SPRINT (Investigation Required)

| Task | Kenapa Keluar | Apa yang Perlu Investigation |
|---|---|---|
| Fix feedback pipeline (TASK-004) | Root cause belum jelas | Periksa: frontend event handler -> API endpoint -> DB insert -> worker processing. Bisa jadi 4 tempat yang berbeda. |
| Owner data pathway (TASK-005) | Existing upload flow belum dipahami | Periksa: bagaimana kb_ingest bekerja sekarang? Apakah ada celery worker? Queue mana? |
| SFT/DPO/KTO pipelines (M2) | Hasil training tidak deterministic | Bisa tulis script, tapi tidak bisa guarantee eval PASS. Risk terlalu tinggi untuk sprint commitment. |
| Clone E2E deploy (TASK-014) | Butuh VPS test target | Belum ada client VPS untuk test. Dry-run saja tidak cukup validasi. |
| Identity anchor SFT (M3) | ML outcome uncertain | Cosine sim > 0.85 adalah target, bukan guarantee. Perlu eksperimen. |

**Rule:** Task investigation boleh dilakukan PARALEL selama sprint (kalau ada waktu), tapi tidak masuk committed deliverable.

---

## RISK & MITIGATION

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Alembic autogenerate miss indexes/constraints | Low | Medium | Manual review migration file sebelum commit |
| Test DB setup conflict dengan dev DB | Low | Low | Gunakan SQLite in-memory atau test container terpisah |
| GHA runner timeout (Docker build lambat) | Medium | Low | Cache Docker layers, gunakan registry mirror |
| Hafidz endpoint butuh auth logic baru | Low | Medium | Reuse license validation existing, hanya tambah HTTP wrapper |

---

## BUDGET

. Semua task adalah local development / GitHub Actions free tier.

---

## COMMIT CONVENTION SPRINT INI

`
type(scope): message -- WHY not just WHAT

Types:
- feat(migration): Alembic baseline for schema v0.5
- feat(test): Add auth and RLS test suite -- 42 tests, 87% pass
- feat(ci): GitHub Actions workflow for pytest + docker build
- feat(hafidz): POST /hafidz/contribute skeleton endpoint
- feat(obs): Prometheus /metrics endpoint with custom counters
- docs(protocol): Sprint 0 plan and locked architecture reference
`

---

## SIGN-OFF

| Role | Nama | Tanda Tangan Digital |
|---|---|---|
| Product Owner | Fahmi Ghani | _______________ |
| Executor | Kimi Code CLI | Committed 2026-05-08 |

---

*Sprint ini adalah fondasi. Kalau fondasi goyang, semua sprint berikutnya akan goyang.*
*Fokus: deterministik, testable, documented.*
