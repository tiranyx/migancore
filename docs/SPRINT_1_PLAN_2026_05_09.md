# 🚀 SPRINT 1 PLAN — Agent Cloning v2 & Knowledge Ingestion

> **Tanggal Rencana:** 9–15 Mei 2026  
> **Status:** Foundation LOCK ✅ | Sprint 0 COMPLETE ✅  
> **Commit Base:** `c201eea` (main)  
> **Version Target:** `0.6.0`

---

## VISION SPRINT 1

> **"Anak bisa lahir, tumbuh, dan kembali ke Induk dengan knowledge-nya."**

Sprint 1 fokus pada **Agent Cloning v2** — sistem di mana:
1. **Parent ADO** (Induk) bisa **spawn Child ADO** (Anak) dengan license
2. **Child ADO** belajar mandiri dan menghasilkan **kontribusi knowledge**
3. **Child ADO** mengembalikan kontribusi ke **Parent ADO** via **Hafidz Ledger**
4. **Parent ADO** bisa **review dan incorporate** kontribusi anak

---

## STORY BREAKDOWN

### Epic 1: Hafidz Ledger Endpoint (SP-007)
**Owner:** Backend  
**Confidence:** 90%  
**Estimasi:** 2 hari

**Acceptance Criteria:**
- [ ] `POST /v1/hafidz/contributions` — child submit kontribusi
- [ ] `GET /v1/hafidz/contributions` — parent list kontribusi
- [ ] `GET /v1/hafidz/contributions/{id}` — detail kontribusi
- [ ] `POST /v1/hafidz/contributions/{id}/review` — parent review (approve/reject)
- [ ] Validasi: license child harus valid, parent harus match
- [ ] Privacy: PII stripped sebelum disimpan
- [ ] Deduplication: SHA-256 hash untuk cek duplikat

**Dependencies:**
- `hafidz_contributions` table (✅ sudah ada via migration)
- License validation service (✅ sudah ada)

---

### Epic 2: Agent Cloning API v2 (SP-008)
**Owner:** Backend  
**Confidence:** 75%  
**Estimasi:** 3 hari

**Acceptance Criteria:**
- [ ] `POST /v1/agents/{id}/clone` — clone agent dengan license baru
- [ ] License child di-generate otomatis saat clone
- [ ] License child ter-link ke parent (genealogy tracking)
- [ ] Child agent start dengan knowledge base parent (initial sync)
- [ ] Child agent punya identity terpisah (tenant terpisah atau sub-tenant)

**Dependencies:**
- License system dengan genealogy (✅ sudah ada)
- Hafidz Ledger (SP-007, harus dulu)

---

### Epic 3: Knowledge Ingestion Pipeline (SP-009)
**Owner:** Backend + Data  
**Confidence:** 60%  
**Estimasi:** 3 hari

**Acceptance Criteria:**
- [ ] Async worker (Redis queue) untuk proses kontribusi
- [ ] Quality scoring: relevance, novelty, accuracy
- [ ] Auto-incorporate: kontribusi high-quality masuk ke parent secara otomatis
- [ ] Manual review: kontribusi medium-quality masuk ke queue review
- [ ] Reject: kontribusi low-quality ditolak dengan alasan

**Dependencies:**
- Redis worker setup (belum ada)
- Hafidz Ledger (SP-007)

---

### Epic 4: Integration Test Setup (SP-010)
**Owner:** QA  
**Confidence:** 85%  
**Estimasi:** 2 hari

**Acceptance Criteria:**
- [ ] TestContainers untuk PostgreSQL + Redis ephemeral
- [ ] pytest fixture untuk DB connection
- [ ] Integration tests untuk: auth, agent CRUD, hafidz flow
- [ ] Coverage target: naik dari 16% ke 40%

**Dependencies:**
- Test infrastructure (✅ pytest sudah setup)
- Docker Compose test profile

---

### Epic 5: Pydantic Deprecation Fix (SP-011)
**Owner:** Backend  
**Confidence:** 95%  
**Estimasi:** 0.5 hari

**Acceptance Criteria:**
- [ ] `class Config` → `ConfigDict` di `config.py`
- [ ] Semua tests tetap pass

---

## SPRINT BOARD

| SP | Epic | Confidence | Estimasi | Status |
|----|------|------------|----------|--------|
| SP-007 | Hafidz Ledger Endpoint | 90% | 2 hari | 🟢 Ready |
| SP-008 | Agent Cloning API v2 | 75% | 3 hari | 🟡 Blocked by SP-007 |
| SP-009 | Knowledge Ingestion Pipeline | 60% | 3 hari | 🟡 Blocked by SP-007 |
| SP-010 | Integration Test Setup | 85% | 2 hari | 🟢 Ready |
| SP-011 | Pydantic Deprecation Fix | 95% | 0.5 hari | 🟢 Ready |

**Total Estimasi:** 10.5 hari  
**Sprint Capacity:** 7 hari (2 engineer × 3.5 hari efektif)  
**Rekomendasi Scope:** SP-007 + SP-010 + SP-011 (4.5 hari) + partial SP-008

---

## RISK REGISTER

| # | Risk | Probability | Impact | Mitigasi |
|---|------|-------------|--------|----------|
| 1 | Redis worker belum pernah di-setup | Medium | High | Gunakan `rq` atau `celery` — pilih yang paling sederhana |
| 2 | Child agent identity model belum jelas | Medium | High | Definisikan dulu: sub-tenant atau tenant terpisah? |
| 3 | Knowledge quality scoring algorithm | Medium | Medium | MVP: rule-based dulu, ML nanti |
| 4 | VPS resource limit untuk multiple agents | Low | Medium | Monitor RAM/CPU, scale up kalau perlu |

---

## DECISIONS NEEDED

1. **Child Agent Identity:** Sub-tenant dalam parent tenant, atau tenant terpisah penuh?
2. **Async Worker:** `rq` (simple) atau `celery` (powerful) atau `arq` (async-native)?
3. **Quality Scoring:** Rule-based heuristik atau embeddings similarity?
4. **Auto-incorporate threshold:** Quality score berapa yang auto-approve?

---

## DEFINITION OF DONE (Sprint 1)

- [ ] Hafidz Ledger CRUD endpoint LIVE di production
- [ ] Agent Cloning v2 bisa di-demo end-to-end
- [ ] Integration tests untuk Hafidz flow pass
- [ ] Coverage naik ke 25%
- [ ] Zero Pydantic deprecation warnings
- [ ] QA Report signed off

---

> **Founder:** Silakan review scope di atas. Apakah ada epic yang perlu di-cut, ditambah, atau di-prioritize ulang?
