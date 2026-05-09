# LESSONS LEARNED — MiganCore
**Status:** LIVING DOCUMENT  
**Created:** 2026-05-09 14:30 WIB  
**Owner:** Tiranyx / Chief Engineer  
**Rule:** Setiap kegagalan atau keberhasilan signifikan WAJIB dicatat di sini sebelum dilupakan.

---

## Lesson #178: Alembic Migration dengan asyncpg — JSON Literal & DO Block Pitfalls

**Tanggal:** 2026-05-09  
**Konteks:** Deployment migration `007_schema_hardening` ke production VPS  
**Kesalahan:** Migration gagal 4× berturut-turut dengan error berbeda:
1. `InsufficientPrivilegeError: must be owner of function` — `auth_lookup_user_by_email` sudah ada, dibuat manual oleh superuser
2. `PostgresSyntaxError: syntax error at or near "BEGIN"` — `DO $$ BEGIN ... EXCEPTION ... END $$` tidak bisa dijalankan via `connection.execute(text(...))`
3. `PostgresSyntaxError: syntax error at or near ":"` — `text()` mem-parse `:policy::jsonb` sebagai bind parameter
4. `InvalidRequestError: A value is required for bind parameter 'false'` — JSON literal `{"requires_approval":false}` di-parse sebagai bind param `:false`
5. `AmbiguousParameterError: inconsistent types deduced for parameter $1` — parameter yang sama digunakan di SELECT dan WHERE clause

**Root Cause:**
- `asyncpg` tidak support multiple commands dalam satu prepared statement
- SQLAlchemy `text()` mengenali semua `:` diikuti karakter alfanumerik sebagai bind parameter, bahkan di dalam string literal JSON
- `asyncpg` tidak bisa infer tipe parameter yang digunakan di multiple places dengan tipe berbeda

**Fix:**
| Statement Type | Solusi |
|---|---|
| DDL sederhana (ALTER, CREATE POLICY) | `connection.execute(text("..."))` |
| DO block (PL/pgSQL) | `op.execute("...")` dengan plain string |
| JSON literal dengan `::jsonb` cast | `connection.exec_driver_sql("...")` — bypass SQLAlchemy parsing |
| Parameter binding yang aman | Gunakan parameter binding hanya untuk values tanpa JSON/ colon |

**Prevention:**
- Selalu gunakan `exec_driver_sql()` untuk statement yang mengandung JSON literal atau `::` cast
- Hindari parameter binding untuk static seed data di migration
- Test migration di Docker test runner sebelum deploy ke production

**Referensi Commit:** `9eaa2a1`, `450fade`, `1c48724`, `f6b8dee`, `c3779dd`, `3c9899a`

---

## Lesson #177: Baseline-Gate Coupling → False-Fail

**Tanggal:** 2026-05-06  
**Konteks:** Training Cycle 6-7  
**Kesalahan:** Eval gate membandingkan model baru dengan baseline model sebelumnya. Jika baseline sudah jelek, model baru yang lebih baik tetap "fail" karena gap tidak cukup besar.

**Root Cause:** Gate threshold relative terhadap baseline, bukan absolute quality metric.

**Fix:** Decouple baseline dari gate. Gate = threshold absolute (misal: identity cosine sim > 0.85, tool-use > 80%). Baseline = reference untuk A/B comparison.

**Prevention:** Gate harus absolute. A/B test baru pakai baseline comparison.

**Referensi Commit:** D-002 di `MIGANCORE_ARCHITECTURE_REMAP_v2026.md`

---

## Lesson #176: Signal Density < 15% → Regression

**Tanggal:** 2026-05-04  
**Konteks:** Training Cycle 5-6  
**Kesalahan:** Dataset training mengandung < 15% signal untuk kategori tertentu (misal: voice/tone). Hasil: model belajar kategori lain tapi regression di kategori dengan signal rendah.

**Root Cause:** Curriculum mixing tanpa density check. Kategori dengan data sedikit "drowning" di noise kategori lain.

**Fix:** Minimum signal density ≥ 25% per kategori per cycle. Kalau tidak cukup, skip kategori itu.

**Prevention:** Dataset builder WAJIB cek signal density sebelum training.

---

## Lesson #175: ORPO Wrong Tool untuk Voice/Identity

**Tanggal:** 2026-05-02  
**Konteks:** Training Cycle 3-4  
**Kesalahan:** Menggunakan ORPO untuk voice/identity tuning. Rewards/margins NEGATIF di setiap cycle. Identitas tidak terbentuk, malah semakin fragile.

**Root Cause:** ORPO adalah "odds ratio preference optimization" — cocok untuk preference pairs (A vs B). Tapi voice dan identity adalah pattern recognition, bukan preference. Perlu SFT (supervised fine-tuning) untuk pattern.

**Fix:** One Problem = One Tool. SFT untuk identity/voice. DPO/SimPO untuk preference. KTO untuk direct user signals.

**Prevention:** Decision matrix loss function di `MIGANCORE_ARCHITECTURE_REMAP_v2026.md` Section 6.

---

## Lesson #174: 99% Synthetic Data = Circular Training

**Tanggal:** 2026-04-28  
**Konteks:** Training Cycle 1-3  
**Kesalahan:** Data training hampir 100% synthetic (dari Magpie/self-play). Model belajar dari output model sendiri → circular degradation. Identitas tidak terbentuk, quality menurun.

**Root Cause:** User feedback pipeline BROKEN, owner data pathway NOT BUILT, teacher distillation MANUAL (10 pairs). Hanya self-growth yang jalan tapi 18 pairs total.

**Fix:**
1. Fix user feedback endpoint + worker (done 2026-05-09)
2. Build owner data pathway (5 endpoints)
3. Automate teacher distillation (cron, $5/day cap)
4. Target: real-data ratio ≥ 20% dalam 2 minggu, ≥ 50% dalam 1 bulan

**Prevention:** Data curator engine dengan MTLD diversity scoring + dedup.

---

## Lesson #173: Identity Prompt ≠ Identity Weights

**Tanggal:** 2026-04-25  
**Konteks:** Identity consistency test  
**Kesalahan:** Mengira SOUL.md sebagai system prompt cukup untuk identitas. Tanpa SOUL.md, model jawab "Saya Qwen" bukan "Saya Mighan-Core".

**Root Cause:** LoRA adapter tidak cukup kuat override base model identity. Base model Qwen2.5-7B punya "identity weight" sendiri yang lebih kuat dari LoRA.

**Fix:** SFT Identity Anchor — 200 pairs pure identity training dengan rank 32, alpha 64, 5 epochs. Target: tanpa system prompt, model tetap bilang "Saya Mighan-Core".

**Prevention:** Identity test MANDATORY sebelum deploy. Cosine similarity > 0.85.

---

## Lesson #172: Docker Test Runner > Local Testing (Windows)

**Tanggal:** 2026-05-07  
**Konteks:** Integration tests  
**Kesalahan:** Coba run pytest di Windows lokal. Python 3.14 dependency hell. asyncpg tidak compile. Waktu terbuang 4+ jam.

**Root Cause:** Windows environment tidak compatible dengan stack Linux-native (asyncpg, pgvector, etc).

**Fix:** `docker-compose.test.yml` dengan `alembic upgrade head` + pytest. Semua testing via Docker.

**Prevention:** Jangan pernah coba run backend tests di Windows. Docker mandatory.

---

## Lesson #171: Manual SQL Patches → Schema Drift Hell

**Tanggal:** 2026-04-20  
**Konteks:** Database schema  
**Kesalahan:** 25 manual SQL patches (001-025) tanpa version control. Production DB dan dev DB punya schema berbeda. Migration tidak reproducible.

**Root Cause:** Tidak pakai Alembic dari hari pertama.

**Fix:** Convert semua patches ke Alembic migration. `007_schema_hardening` konsolidasi patches 005-011 + 024. Semua schema change ke depan via Alembic.

**Prevention:** Alembic MANDATORY. CI gagal kalau tidak ada migration.

---

## Lesson #170: Clone Mechanism Needs Identity Anchor First

**Tanggal:** 2026-04-15  
**Konteks:** Clone endpoint  
**Kesalahan:** Coba implement clone mechanism tapi child agent tidak inherit identity. Child = "Qwen", bukan "Mighan-Core descendant".

**Root Cause:** Cloning butuh DNA (identity weights). Tanpa DNA, clone = shell kosong.

**Fix:** Phase 1 = Identity Anchor SFT. Phase 3 = Clone mechanism. Jangan terbalik.

**Prevention:** Roadmap `MIGANCORE_ARCHITECTURE_REMAP_v2026.md` Section 10.

---

*Catatan: Lesson #001-169 tercatat di `CONTEXT.md` dan `docs/logs/`.*
