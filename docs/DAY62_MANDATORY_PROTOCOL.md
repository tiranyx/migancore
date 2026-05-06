# DAY 62 — MANDATORY PROTOCOL DOCUMENT
**Date:** 2026-05-07 | **Implementor:** Claude Code | **Version:** v0.5.19 LIVE

---

## BAGIAN 1 — RECAP STATUS HARI INI

### Apa yang Terjadi Day 62

Day 62 adalah hari **deploy, debug, QA, dan validasi** v0.5.19 (ADO License System).
Satu deliverable besar: License System yang sudah diimplementasikan Day 61 **sekarang LIVE**
di production `api.migancore.com/v1/license/*` dengan 9/9 QA tests PASS.

### Juga diselesaikan (Day 62 tambahan):
1. **Genealogy + Knowledge Return** fields ditambahkan ke `mint_license()` — setiap license
   yang diterbitkan sekarang membawa silsilah ADO dan config "Anak Kembali ke Induk"
2. **3 bugs ditemukan & diperbaiki** selama proses deploy (lihat Bagian 2)
3. **Deploy protocol baru** terdokumentasi — `docker compose build` wajib setiap code change

### Current State
```
Production URL     : app.migancore.com + api.migancore.com
API Version        : v0.5.19 (LIVE di VPS)
Production Model   : migancore:0.3 (PROMOTED Day 60, weighted_avg 0.9082)
License System     : LIVE — /v1/license/info|status|mint|batch
License Mode       : DEMO (no license.json = beta mode, semua fitur available)
VPS Git HEAD       : 1e9e96f
Phase              : Phase 2 (Clone + Identity + Training — IN PROGRESS)
```

---

## BAGIAN 2 — TEMUAN DAN BUG HARI INI

### F23: 3 Production Deploy Bugs Ditemukan + Fixed

#### Bug #1 — Router prefix salah (Lesson #123)
- **Symptom**: GET /v1/license/info → 404 Not Found
- **Root cause**: `router = APIRouter(prefix="/license")` — semua router lain pakai `/v1/`
- **Debug path**: Cek OpenAPI /openapi.json → license routes tidak muncul →
  grep auth.py → `prefix="/v1/auth"` → pattern jelas
- **Fix**: `prefix="/v1/license"` → commit `fefe1dd`
- **Time to fix**: 5 menit

#### Bug #2 — `docker compose restart` tidak apply code (Lesson #124)
- **Symptom**: Setelah git pull + restart, route masih 404 → OpenAPI tidak berubah
- **Root cause**: API container pakai `build: { context: ./api }` dengan `COPY . .`
  - Git pull mengubah file di `/opt/ado/api/` di host
  - Tapi container berjalan dengan IMAGE lama (baked saat last `docker compose build`)
  - `docker compose restart` = restart container → image lama → code lama
- **Debug path**: `cat docker-compose.yml | grep -A 15 'api:'` → `build: { context: ./api }`
  → konfirmasi tidak ada volume mount `/opt/ado/api:/app`
- **Fix**: `docker compose build api && docker compose up -d api`
- **Time to fix**: 3 menit (build ~45 detik warm cache)

#### Bug #3 — ENV vars tidak masuk container (Lesson #125)
- **Symptom**: `docker exec ado-api-1 env | grep LICENSE` → kosong
  meski `LICENSE_SECRET_KEY` ada di `.env`
- **Root cause**: `.env` di project root = substitusi template di YML, bukan auto-inject ke container
  - Container hanya menerima vars yang ADA di `environment:` block di docker-compose.yml
  - `ADMIN_SECRET_KEY: ${ADMIN_SECRET_KEY}` → container dapat ✅ (ada di yml)
  - `LICENSE_SECRET_KEY=...` di `.env` tanpa deklarasi di yml → container TIDAK dapat ❌
- **Fix**: Tambah ke `environment:` block:
  ```yaml
  LICENSE_SECRET_KEY: ${LICENSE_SECRET_KEY}
  LICENSE_DEMO_MODE: ${LICENSE_DEMO_MODE:-true}
  ADO_DISPLAY_NAME: ${ADO_DISPLAY_NAME:-Migan}
  LICENSE_INTERNAL_KEY: ${LICENSE_INTERNAL_KEY}
  ```
  Commit `1e9e96f`
- **Time to fix**: 10 menit

### F24: Deploy Protocol yang Benar (Updated)

```bash
# SETIAP CODE CHANGE (py, html, js, requirements.txt):
ssh sidix-vps "cd /opt/ado && git pull origin main && docker compose build api && docker compose up -d api"

# HANYA ENV CHANGE (tambah/ubah .env saja, tidak ada code change):
ssh sidix-vps "cd /opt/ado && docker compose up -d api"
# (docker compose up -d recreates container dengan env baru tanpa rebuild image)

# CHECK: apakah env sudah masuk container?
ssh sidix-vps "docker exec ado-api-1 env | grep LICENSE"

# VERIFY startup log:
ssh sidix-vps "docker logs ado-api-1 --tail 20"
# Harus ada: license.demo_mode atau license.ok atau license.validation.ok
```

### F25: OLLAMA_KEEP_ALIVE 10m → 24h

Ditemukan saat cek docker-compose.yml untuk debug Bug #2:
- `OLLAMA_KEEP_ALIVE: "10m"` — model unload dari memory setiap 10 menit tidak aktif
- Cold-start setelah idle = ~3-5 detik loading delay
- Fix: `OLLAMA_KEEP_ALIVE: "24h"` — model stay di memory sepanjang hari
- Impact: pengguna tidak pernah tunggu model reload saat obrolan jarang

---

## BAGIAN 3 — LESSON LEARNED

### Lesson #123: Cek prefix convention sebelum tambah router
- Tidak ada linting rule untuk ini — harus manual grep
- Command: `grep -r "APIRouter(prefix" api/routers/ | head -5`
- MiganCore pattern: semua `/v1/` prefix

### Lesson #124: MiganCore API = baked image — selalu `build` setelah code change
- Tidak ada volume mount untuk `/app` (kode)
- Volume mount HANYA untuk: `/etc/ado/keys` (JWT) dan `./config` (config files)
- **SETIAP code change = `docker compose build api && docker compose up -d api`**
- Build time warm cache: ~30-60 detik (acceptable)

### Lesson #125: docker-compose env vars: `.env` ≠ container env
- `.env` → template substitution di YML (`${VAR}`)
- Container env → harus EKSPLISIT di `environment:` block atau via `env_file:`
- Untuk tambah env var baru: update `.env` DAN `docker-compose.yml` environment block
- Kemudian `docker compose up -d api` (recreate container, tidak perlu rebuild image)

---

## BAGIAN 4 — QA SCORECARD

### 9/9 Tests PASS

```
T1  GET /v1/license/info (public)                    ✅ DEMO mode, Migan, is_operational=true
T2  GET /v1/license/status (benar admin key)         ✅ DEMO, reason=no_license_file
T3  GET /v1/license/status (wrong key)               ✅ 403 Forbidden
T4  GET /v1/license/status (no key)                  ✅ 403 Forbidden
T5  POST /v1/license/mint (no key)                   ✅ 403 Forbidden
T6  POST /v1/license/mint (SARI PERAK, full fields)  ✅ genealogy + knowledge_return verified
T7  POST /v1/license/batch (2 licenses, opt-in mix)  ✅ 2/2 ok, LEX=opt-in, AVA=opt-out
T8  GET /v1/public/stats (regression)                ✅ existing routes intact
T9  GET /openapi.json (4 license routes)             ✅ /info|status|mint|batch terdaftar
```

### License SARI PERAK yang diterbitkan saat QA:
```
license_id:      8cb708e7-c342-4245-9f77-6a59a0026108
ado_display_name: SARI
tier:            PERAK
expiry:          2026-06-05T19:16:16Z
genealogy.parent_version: v0.3
genealogy.generation:     1
knowledge_return.enabled: true
knowledge_return.endpoint: https://api.migancore.com/hafidz/contribute
crypto: identity_hash ✅, signature ✅, entropy ✅
```

---

## BAGIAN 5 — COMMIT LOG DAY 61-62

```
df6d82e  docs: ADO Knowledge Return — Anak Kembali ke Induk (Day 61)
7e1efed  feat: genealogy + knowledge_return fields di mint_license()
fefe1dd  fix: router prefix /license → /v1/license
91d858e  docs: Kimi strategic review Day 61-62
1e9e96f  infra: LICENSE env vars di docker-compose.yml
```

---

## BAGIAN 6 — STATE VPS SAAT INI

```
/opt/ado/
├── api/
│   ├── services/license.py   ← BARU: mint/validate/batch + genealogy + knowledge_return
│   ├── routers/license.py    ← BARU: /v1/license/info|status|mint|batch
│   ├── config.py             ← UPDATED: LICENSE_PATH, LICENSE_SECRET_KEY, LICENSE_DEMO_MODE
│   └── main.py               ← UPDATED: step 10 license validation + router registration
├── docker-compose.yml        ← UPDATED: LICENSE env vars + OLLAMA_KEEP_ALIVE 24h
└── .env                      ← UPDATED: LICENSE_SECRET_KEY, LICENSE_DEMO_MODE=True,
                                          ADO_DISPLAY_NAME=Migan, LICENSE_INTERNAL_KEY

Containers: 6/6 UP (api rebuilt with v0.5.19 baked code)
```

---

## BAGIAN 7 — ACTION ITEMS NEXT

### Day 63-66 — Cycle 4 Dataset Expansion
- [ ] Analisis weakness Cycle 3 eval (evolution-aware 0.568, creative 0.695)
- [ ] Generate 20 evolution-aware pairs (fix regression — model masih "lupa" style awal)
- [ ] Generate 30 creative pairs (kategori baru — narasi, brainstorm, imajinatif)
- [ ] Generate 50 tool-use discrimination pairs (target: 0.797 → 0.85)
- [ ] Generate 50 voice pairs (target: 0.817 → 0.85, udah bagus tapi bisa lebih)
- [ ] Export Cycle 4 JSONL (~950 pairs total)
- [ ] Training Vast.ai (~$0.10-0.12)
- [ ] Eval: target weighted_avg ≥ 0.92

### Day 62-70 (Phase A Hafidz Ledger)
- [ ] DB migration: CREATE TABLE hafidz_contributions (schema dari ADO_KNOWLEDGE_RETURN_DESIGN.md)
- [ ] Skeleton: POST /v1/hafidz/contribute (log ke DB, no processing yet)
- [ ] Update mint_license() + MintRequest: sudah ada genealogy dan knowledge_return ✅

### Day 71-75 (Phase 2 P0 — Clone Mechanism)
- [ ] `ado_config.json` schema: persona, display_name, model, tools, language
- [ ] Config-driven identity injection ke system prompt
- [ ] Per-org Docker Compose template (parameterized env vars)

---

## BAGIAN 8 — LOG AKTIVITAS DAY 62

```
[sesi mulai]  Context loaded dari summary kompaksi Day 61
00:05         Commit ADO_KNOWLEDGE_RETURN_DESIGN.md (belum ter-commit di akhir sesi kemarin)
00:10         Update mint_license(): tambah genealogy + knowledge_return params
              batch_mint() + MintRequest ikut diupdate
00:15         AST syntax check PASS. Smoke test local PASS.
              Commit + push: 7e1efed
00:20         Pre-flight VPS: git HEAD=Day60, containers 6/6 UP, no LICENSE vars
00:25         git pull VPS: fast-forward, 16 files masuk
              Inject LICENSE_SECRET_KEY, LICENSE_DEMO_MODE, ADO_DISPLAY_NAME ke .env
              docker compose restart api
00:30         BUG #1 DITEMUKAN: 404 pada GET /v1/license/info
              Debug: OpenAPI spec → license routes tidak terdaftar
              Root cause: prefix="/license" bukan "/v1/license"
              Fix commit fefe1dd → git push
00:35         git pull + restart → BUG #2 DITEMUKAN: masih 404
              Debug: docker-compose.yml → build pattern, tidak ada volume mount
              Fix: docker compose build api → 45 detik → docker compose up -d api
00:40         License log kelihatan: "license.demo_mode" ✅
              BUG #3 DITEMUKAN: env vars tidak masuk container
              Debug: docker exec env | grep LICENSE → kosong
              Root cause: environment block di docker-compose tidak ada LICENSE vars
              Fix: sed inject 4 lines ke docker-compose.yml
              Generate + set LICENSE_INTERNAL_KEY
              docker compose up -d api (recreate, tidak perlu rebuild)
00:50         All env vars verified di container
              TEST 1-9: ALL PASS
01:00         Commit infra changes dari VPS, rebase + push → 1e9e96f
              git pull di lokal → synced
              Update docker-compose.yml di lokal juga (sudah via pull)
01:05         Tulis day62_progress.md + update MEMORY.md
              Tulis DAY62_MANDATORY_PROTOCOL.md

Day 62 Cost: $0 (deploy + QA, no GPU)
Lessons Added: #123-125 (3 new)
Total Lessons Cumulative: 125
Version Live: v0.5.19
```

---

*Dokumen ini adalah mandatory protocol Day 62.*
*Next checkpoint: Day 63 — Cycle 4 dataset expansion (evolution-aware + creative fixes).*
