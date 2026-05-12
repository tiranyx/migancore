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

---

## Lesson #179: Identity Training Data Contaminated by Competitor References

**Tanggal:** 2026-05-12
**Konteks:** Recovery from migancore:0.8 identity collapse
**Kesalahan:** identity_sft_200.jsonl (Day 0-39 foundation) mengandung referensi Anthropic/Claude. Ketika di-merge ke base Qwen, model bilang  Saya primanya Claude 2.
**Root Cause:** Synthetic data generation pipeline (generate_identity_pairs.py) tidak difilter untuk competitor references. Magpie/self-play menghasilkan data yang memanggil identitas AI lain.
**Fix:**
1. Audit manual SEMUA pasang identitas
2. Blocklist: Anthropic, Claude, OpenAI, ChatGPT, Google, Gemini, Alibaba, Qwen, Moonshot, Kimi, DeepSeek
3. Block meta-instructions: Jangan jawab..., Kamu harus...
4. Generate ulang dari nol kalau < 100 pasang bersih
**Prevention:** Semua dataset WAJIB lewat contamination filter sebelum training.

---

## Lesson #180: Sequential Adapter Merge Fails When Bases Differ

**Tanggal:** 2026-05-12
**Konteks:** Attempted fix for 0.8 identity collapse via sequential merge
**Kesalahan:** Merge identity_adapter (trained on Qwen) lalu DPO_adapter (trained on Qwen) diharapkan berhasil. Tapi DPO gradien relative ke W_base Qwen, bukan ke W_merged_identity.
**Root Cause:** LoRA adapter menghitung B*A relatif terhadap base model training. Sequential merge dari adapter dengan base berbeda = gradien saling lawan.
**Fix:**
1. Semua adapter untuk merge HARUS dilatih dari base yang SAMA
2. Atau: retrain DPO dari checkpoint identitas (bukan dari Qwen base)
3. Atau: gunakan SVD-weighted merge dengan alpha tuning (jika ada RAM)
**Prevention:** Training script WAJIB verifikasi base model sebelum training. Guard: exit if base ≠ production checkpoint.

---

## Lesson #181: Docker Code Changes Need uild, Not Just estart

**Tanggal:** 2026-05-08
**Konteks:** Day 71d deploy attempts
**Kesalahan:** docker compose restart api setelah edit Python file. Container restart dengan image LAMA. Perubahan kode tidak ter-deploy.
**Root Cause:** Docker container menggunakan image, bukan bind mount. Code baru tidak masuk image tanpa docker compose build.
**Fix:** Selalu docker compose build api && docker compose up -d api setelah edit kode.
**Prevention:** Check BUILD_COMMIT_SHA di health endpoint. Must match git rev-parse --short HEAD.

---

## Lesson #182: Semantic Tool Filter = Highest-Impact Perf Fix

**Tanggal:** 2026-05-08
**Konteks:** Day 71d performance optimization
**Kesalahan:** Kirim SEMUA 29 tools ke LLM setiap query. Prompt bloat, latency 60-90s.
**Root Cause:** No tool relevance filtering. LLM harus parse 29 tool descriptions per query.
**Fix:** services/tool_relevance.py — embed query, cosine similarity vs tool descriptions, kirim hanya top-K (default 6) + 2 always-on.
**Result:** 29 → 6 tools, latency 60-90s → 38-46s (-50%).
**Prevention:** Tool relevance mandatory untuk > 10 tools.

---

## Lesson #183: Babel Pre-Compile Cuts 600KB Per Page Load

**Tanggal:** 2026-05-08
**Konteks:** Day 71d frontend optimization
**Kesalahan:** Babel CDN (600KB) di-load setiap page load untuk compile JSX di browser.
**Root Cause:** JSX tidak di-precompile. Browser menjalankan Babel setiap load.
**Fix:** Pre-compile JSX ke JS lokal menggunakan Babel CLI. Hapus Babel CDN dari HTML.
**Result:** 2.1MB → 1.5MB page load.
**Prevention:** Build step mandatory untuk production frontend.

---

## Lesson #184: Ollama keep_alive Default 5min Too Short

**Tanggal:** 2026-05-08
**Konteks:** Day 71d latency investigation
**Kesalahan:** OLLAMA_KEEP_ALIVE=5m. Model unload setelah idle 5 menit. Query berikutnya = cold start 30-60s.
**Root Cause:** Default Ollama terlalu agresif untuk production API.
**Fix:** OLLAMA_KEEP_ALIVE=24h (atau 30m minimum). Model tetap loaded.
**Result:** Eliminates cold start penalty.
**Prevention:** Ollama config review mandatory untuk production deploy.

---

## Lesson #185: nginx add_header Does Not Cascade

**Tanggal:** 2026-05-08
**Konteks:** Day 71d CORS/header debugging
**Kesalahan:** dd_header di nginx location block tidak cascade ke nested blocks.
**Root Cause:** nginx dd_header inheritance behavior — child blocks override parent, tidak merge.
**Fix:** Ulangi header di setiap location block yang membutuhkan.
**Prevention:** nginx config review dengan 
ginx -t sebelum reload.

---

## Lesson #186: DPO Trained from Base Qwen Overwrites Identity

**Tanggal:** 2026-05-12
**Konteks:** migancore:0.8 total identity collapse
**Kesalahan:** DPO adapter dilatih dari Qwen/Qwen2.5-7B-Instruct dengan 951 utility pairs + 5 identity pairs. Identity drowned.
**Root Cause:** 99.5% utility signal = identity statistically irrelevant. Gradien utility pull ke generic assistant space.
**Fix:**
1. DPO harus dilatih dari checkpoint identitas (bukan base Qwen)
2. Minimum 20% identity pairs dalam DPO dataset
3. Atau: train DPO separately, merge via SVD dengan weight identitas > utility
**Prevention:** Dataset builder WAJIB cek category mix sebelum training.

---

## Lesson #187: Production Model is 0.7c, Not 0.3

**Tanggal:** 2026-05-12
**Konteks:** Kimi audit post-handoff
**Kesalahan:** Dokumen handoff Claude menyatakan production = migancore:0.3. Audit live VPS menunjukkan production = migancore:0.7c.
**Root Cause:** Handoff dokumen tidak di-update setelah Cycle 4-7c. 0.7c adalah hasil Cycle 7 series (terakhir sebelum rollback).
**Fix:**
1. Semua handoff WAJIB verifikasi live state via VPS audit
2. Health endpoint harus expose production model name
3. Tracker di-update setiap cycle promote/rollback
**Prevention:** curl http://api/health | jq .model = single source of truth.

---

## Lesson #188: Eval with System Prompt = False Positive for Identity

**Tanggal:** 2026-05-12
**Konteks:** Identity eval methodology review
**Kesalahan:** Eval gate selalu inject SOUL.md sebagai system prompt. Model pass identitas karena parroting prompt, bukan karena weight-embedded identity.
**Root Cause:** Test tidak membedakan prompt-following vs weight-embedded knowledge.
**Fix:**
1. Identity eval MANDATORY tanpa system prompt (EMPTY)
2. Prompt-following eval = terpisah (WITH system prompt)
3. Kedua-duanya harus pass untuk promote
**Prevention:** Eval script harus ada 2 mode: --with-soul dan --without-soul.

---

## Lesson #189: 0.7c WITHOUT System Prompt Falls Back to Qwen by Alibaba

**Tanggal:** 2026-05-12
**Konteks:** Live identity test on migancore:0.7c
**Kesalahan:** 0.7c dianggap stable production model. Tapi tanpa SOUL.md, model bilang Saya Qwen asisten virtual Alibaba Cloud.
**Root Cause:** 0.7c tidak punya identity yang di-embed di weights. Identitas hanya via prompt injection.
**Implikasi:** White-label client yang ganti system prompt = identitas lenyap. Clone = jadi Qwen.
**Fix:** SFT identity anchor (Lesson #173) MANDATORY sebelum white-label.
**Prevention:** Identity weight-embedded = gate promotion.

---

## Lesson #190: Disk Space Crisis Corrupts GGUF Files

**Tanggal:** 2026-05-12
**Konteks:** GGUF conversion during sequential merge fix
**Kesalahan:** Disk 100% penuh (388GB/388GB) saat convert_hf_to_gguf.py berjalan. Output file 15GB ter-create tapi isinya zeros (sparse file).
**Root Cause:** Linux create file dengan allocate — alokasi metadata tanpa write data. Disk penuh = write gagal silently.
**Fix:**
1. Monitor disk sebelum conversion: df -h /
2. Minimum 30GB free untuk 7B model GGUF
3. Cleanup backup lama sebelum conversion
**Result:** Hapus backup lama → 102GB free → conversion sukses.
**Prevention:** Pre-flight disk check mandatory untuk semua model operations.

---

*Lessons #191+ await future failures and successes.*
*Last updated: Day 72e · 2026-05-12 · by Kimi*
