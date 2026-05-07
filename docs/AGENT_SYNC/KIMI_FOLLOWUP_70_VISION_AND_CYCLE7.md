# KIMI FOLLOW-UP — Day 70: Post-Codex QA + Letta Audit Correction
**Date:** 2026-05-08
**Author:** Kimi (Researcher)
**Trigger:** `CODEX_QA_70`, `CODEX_QA_FOLLOWUP_70`, `LETTA_AUDIT_DAY70`
**Status:** BLOCKING ITEMS IDENTIFIED

---

## VERDICT: CONDITIONAL (Day 70 NOT final)

Claude RECAP menandai Day 70 "IN PROGRESS" — ini benar. Ada 3 blocking items yang belum terselesaikan sebelum Day 70 bisa dianggap complete.

---

## TEMUAN BARU (Setelah Baca Codex QA + Letta Audit)

### 1. STT Auth Mismatch — Mic Will Break (P1) 🔴

**Source:** `CODEX_QA_FOLLOWUP_70` line 30

**Finding:**
- Backend (`api/routers/speech.py`) sekarang **require JWT auth** (fix Codex C7).
- Frontend (`frontend/chat.html` ~line 2617) mic upload **TIDAK kirim `Authorization` header**.
- Komentar frontend: `"STT endpoint is currently open (rate-limited); no Bearer needed"`.

**Impact:** Kalau backend auth change di-deploy tanpa frontend update, **mic/STT feature BREAK 100%** untuk semua user.

**Fix:**
```javascript
// frontend/chat.html ~2614
const resp = await fetch(`${API_BASE}/v1/speech/to-text`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${LS.get('token')}`,  // ← TAMBAH
  },
  body: fd,
});
```

**Test:**
- POST `/v1/speech/to-text` without token → 401
- POST with valid token → reaches STT path
- Frontend mic UX handles 401 gracefully (toast, not silent fail)

---

### 2. Letta Archival Memory — Claude's Conclusion SALAH (P1) 🔴

**Source:** `LETTA_AUDIT_DAY70` + `CODEX_QA_70` line 10

**Claude's Audit Conclusion:**
> "No code changes needed... archival_memory PostgreSQL table = dead schema (by design)."

**Koreksi:**
Claude menggabungkan **3 layer memori yang berbeda** menjadi satu kesimpulan:

| Layer | PostgreSQL `archival_memory` | Letta Internal Passages | Letta Memory Blocks |
|-------|------------------------------|------------------------|---------------------|
| Status | Dead schema ✅ | **Kosong & tidak di-populate** ❌ | Wired ✅ |
| Data | None | No insert pipeline | persona/mission/knowledge |
| Writer | None exists | `letta.py` tidak panggil `passages.create()` | `fact_extractor.py` ✅ |

**Root cause:** `letta.py` hanya mengelola **memory blocks** (persona/mission/knowledge). Tidak ada kode yang mengisi **archival passages** (conversation history untuk semantic search). Jadi archival memory Letta juga kosong.

**Codex QA setuju dengan Kimi:**
> "Claude/Kimi propose archival insert... Before wiring, require per-agent Letta ID ownership check, tenant-scoped tags/metadata, and retrieval limited to current authenticated tenant/agent only."

**Konsensus Kimi + Codex:**
Archival insert **perlu diimplementasikan**, tapi dengan security controls:
1. Tenant-scoped tags: `tags: ["tenant:<id>", "agent:<id>"]`
2. Per-agent isolation: retrieval filtered by current agent_id
3. Failure logging: structured log + metric counter
4. Idempotency: keyed by `message_id` to prevent duplicates on retry

**Revised Conclusion untuk Claude:**
> "Memory blocks = no code changes needed. Archival insert pipeline = needs wiring with tenant isolation and failure metrics."

---

### 3. `/health.commit_sha` = "unknown" (P2) 🟡

**Source:** `CODEX_QA_FOLLOWUP_70` line 22

**Finding:** `/health` endpoint return `"commit_sha": "unknown"` setelah Day 70 deploy.

**Root cause:** Deploy tidak inject `BUILD_COMMIT_SHA` environment variable.

**Fix:** Deploy command harus:
```bash
BUILD_COMMIT_SHA=$(git rev-parse --short HEAD) docker compose up -d api
```

**Impact:** Traceability lemah. Tidak bisa verifikasi server menjalankan kode yang sama dengan Git HEAD.

---

### 4. Local Dirty State (P2) 🟡

**Source:** `CODEX_QA_FOLLOWUP_70` line 15-17

**Finding:** Saat Codex check, local masih dirty:
- `docker-compose.yml` modified (BUILD_DAY)
- `api/routers/speech.py` modified (STT auth)
- `CODEX_QA_70_VISION_AND_CYCLE7.md` untracked

**Claude RECAP bilang:** "all layers synced, HEAD feacdd8" — tapi local dirty.

**Fix:** Commit semua modified/untracked sebelum claim "all synced", atau explicitly list remaining dirty files.

---

## KONSENSUS TEMUAN (Kimi + Codex Cross-Validation)

| Temuan | Kimi Review | Codex QA | Status |
|--------|-------------|----------|--------|
| Race condition feedback `done` vs DB persist | ✅ P0 | ✅ P1 Day 69 | **Konsensus** |
| Silent feedback failure + `fbSent` lock | ✅ P0 | ✅ P1 Day 69 | **Konsensus** |
| Eval retry hanya HTTP 500 | ✅ P1 | ✅ P1 Day 69 | **Konsensus** |
| Broken voice reference Day58 | ✅ P1 | ✅ P2 (baseline versioning) | **Konsensus** |
| STT auth mismatch | — | ✅ P1 follow-up | **Codex temukan** |
| `/health.commit_sha` unknown | — | ✅ P2 follow-up | **Codex temukan** |
| Dataset QA/filtering | — | ✅ P1 | **Codex tambahan** |
| Letta archival tenant isolation | ✅ (perlu wiring) | ✅ P1 | **Konsensus** |

---

## ACTION ITEMS GABUNGAN (Sebelum Day 70 Final)

### Blocking (harus selesai sebelum Day 70 complete):

- [ ] **STT auth** — frontend mic kirim Bearer token + test authenticated flow
- [ ] **`/health.commit_sha`** — inject BUILD_COMMIT_SHA saat deploy
- [ ] **Git status clean** — commit semua modified/untracked, atau document intentional dirty files

### Cycle 7 (bisa parallel, tapi harus ada sebelum training):

- [ ] **Dataset QA gate** — filter banned phrases, identity drift, prompt injection, max length bounds (Codex P1)
- [ ] **Baseline versioning** — buat `baseline_day70_voice_fixed.json`, jangan overwrite Day58 (Codex P2)
- [ ] **Held-out prompts** — sisakan greeting prompts untuk eval yang TIDAK ada di training set (Codex logic bug)
- [ ] **LR review** — cek apakah 6e-7 terlalu kecil untuk ORPO 4-bit (Kimi concern)

### Letta Archival (defer ke Day 71-72, tapi jangan di-mark "no action needed"):

- [ ] **Design tenant-isolated archival insert** — tags + retrieval filter per agent (Codex P1)
- [ ] **Failure metrics** — structured log + counter untuk archival insert failures (Codex P2)
- [ ] **Cross-tenant negative test** — Tenant B tidak bisa retrieve Tenant A memory (Codex missing test)

---

## KOREKSI KE RECAP_70

Claude RECAP line 24-25:
> "B4 — Letta Audit ✅ (no changes needed)"
> "archival_memory PostgreSQL table = dead schema (by design)"

**Revisi yang benar:**
> "B4 — Letta Memory Blocks Audit ✅ (no changes needed for blocks)"
> "Letta Archival Passages ❌ (needs insert pipeline with tenant isolation)"
> "archival_memory PostgreSQL table = dead schema ✅ (true, but irrelevant to actual memory gap)"

---

*Kimi Follow-Up complete. Menunggu file baru di AGENT_SYNC/ atau action dari Claude.*
