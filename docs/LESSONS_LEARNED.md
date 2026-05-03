# MIGANCORE — LESSONS LEARNED
**Living Document — Updated setiap sesi**
**Last Update:** Day 19 | **Author:** Claude Sonnet 4.6

> Ini adalah cognitive ledger proyek — catatan pelajaran berharga dari kegagalan DAN keberhasilan.
> Tujuan: **jangan ulangi kegagalan, lipat gandakan keberhasilan.**
> Format: setiap temuan punya Root Cause, Impact, Fix, dan Generalized Principle.

---

## 🔴 KEGAGALAN & PELAJARAN KRITIS

---

### [F-01] Docker Image Tidak Auto-Update Saat Code Berubah
**Day:** 15 | **Severity:** HIGH | **Category:** Deployment

**Gejala:** Code baru sudah di-commit dan `git pull` berhasil, tapi container masih menjalankan code lama. Perubahan tidak terlihat sama sekali.

**Root Cause:** `docker compose restart api` hanya me-restart container dari **image yang sudah ada**. Jika API menggunakan `build: { context: ./api }`, code di-bake ke dalam image saat build. `git pull` hanya mengubah file di host, BUKAN di dalam running container.

**Impact:** Semua debugging seolah tidak ada hasilnya — kita fikir ada bug di code baru, padahal code baru tidak pernah running.

**Fix:**
```bash
# WAJIB untuk perubahan code:
docker compose build api && docker compose up -d api

# BUKAN ini:
docker compose restart api  ← SALAH untuk code changes
```

**Generalized Principle:**
> **"Git pull ≠ Deploy."** Untuk project dengan Docker `build:` section (bukan `image:`), code change SELALU butuh `docker compose build`. Bedakan: `restart` = restart process, `build` = compile ulang image, `up -d` = recreate container dari image baru.

**Prevention:** Selalu verifikasi code di dalam container setelah deploy:
```bash
docker exec ado-api-1 grep 'keyword_from_new_code' /app/routers/chat.py
```

---

### [F-02] asyncio Task Garbage Collection (Silent Failure)
**Day:** 15 | **Severity:** HIGH | **Category:** Python Async

**Gejala:** Background task (Qdrant indexing, CAI pipeline) tidak jalan sama sekali. Tidak ada log error. Ollama kadang return 499 (client disconnected).

**Root Cause:** `asyncio.create_task()` mengembalikan task object sebagai **weak reference**. Jika task object tidak disimpan di variable yang live, Python GC bisa menghapus task di tengah eksekusi. Ini menyebabkan `GeneratorExit` exception di dalam task, yang menutup httpx connection ke Ollama.

**Impact:** Semua background tasks (Qdrant embed, knowledge extraction, CAI pipeline) silently gagal tanpa log error apapun.

**Fix:**
```python
# Module level:
_background_tasks: set[asyncio.Task] = set()

# Setiap create_task:
_t = asyncio.create_task(run_cai_pipeline(...))
_background_tasks.add(_t)                          # Strong reference
_t.add_done_callback(_background_tasks.discard)    # Auto-cleanup
```

**Generalized Principle:**
> **"asyncio.create_task() is fire-and-forget only if you store the reference."** Setiap background task yang penting HARUS disimpan dalam set/list module-level. `add_done_callback` untuk auto-cleanup.

**COROLLARY:** Jika background task silently tidak jalan → cek apakah task reference tersimpan.

---

### [F-03] `from module import value` Freezes Lazily-Initialized Singletons
**Day:** 15 | **Severity:** HIGH | **Category:** Python Import System

**Gejala:** `AsyncSessionLocal is None` di dalam function yang seharusnya bisa akses DB. Padahal `init_engine()` sudah dipanggil saat startup.

**Root Cause:** `from models.base import AsyncSessionLocal` di module-level **mengikat nilai `None`** pada waktu import (sebelum FastAPI lifespan/startup event memanggil `init_engine()`). Ini adalah Python import binding: yang di-copy adalah VALUE-nya saat import, bukan REFERENCE ke variable.

**Impact:** `_store_preference_pair()` silently return tanpa menyimpan apapun. Pipeline berjalan tapi data tidak tersimpan.

**Fix:**
```python
# SALAH:
from models.base import AsyncSessionLocal  # Freezes None at import time

# BENAR:
import models.base as _models_base
# Then at call time:
if _models_base.AsyncSessionLocal is None:  # Always gets current value
    return
async with _models_base.AsyncSessionLocal() as db:
    ...
```

**Generalized Principle:**
> **"from X import Y for lazily-initialized singletons = time bomb."** Jika Y di-set setelah startup (seperti DB session factory, connection pool), gunakan `import X as _x` dan akses via `_x.Y` di runtime.

**APPLIES TO:** Database connections, Redis clients, model singletons, any object initialized in FastAPI lifespan.

---

### [F-04] Qdrant RocksDB "Too Many Open Files"
**Day:** 16 | **Severity:** HIGH | **Category:** Infrastructure / OS

**Gejala:** `qdrant.index_failed: Unexpected Response: 500`. Qdrant log: `IO error: Too many open files (os error 24)`.

**Root Cause:** Qdrant menggunakan RocksDB sebagai storage engine. RocksDB membuka **banyak file descriptor per segment per collection** (Options file, SST files, manifest files). Default Docker container soft limit = 1024 file descriptors. Dengan 6+ Qdrant collections, total FDs melebihi limit saat membuat collection baru.

**Impact:** Collection baru tidak bisa dibuat. Existing collections tidak bisa menerima upsert baru. Semua indexing silently gagal. `collection_created` log muncul tapi upsert langsung 500.

**Fix:**
```yaml
# docker-compose.yml, service qdrant:
ulimits:
  nofile:
    soft: 65536
    hard: 65536
```

**Generalized Principle:**
> **"Setiap produk yang pakai RocksDB (Qdrant, Kafka, TiKV, CockroachDB) WAJIB set ulimits nofile ≥65536."** Default Docker limit 1024 selalu tidak cukup untuk RocksDB di production.

**COROLLARY:** Qdrant 500 error pada PUT /collections = selalu cek ulimits sebelum debugging Qdrant code.

**Prevention checklist untuk deploy Qdrant baru:**
```bash
docker exec qdrant-container cat /proc/1/limits | grep "open files"
# Harus menunjukkan soft ≥ 65536
```

---

### [F-05] Score Threshold 0.55 Terlalu Rendah untuk RAG Injection
**Day:** 16 | **Severity:** MEDIUM | **Category:** ML / Research

**Gejala (potential):** Episodic context injection mungkin membawa noise (irrelevant past turns) ke system prompt, yang bisa membingungkan 7B model.

**Root Cause:** Score threshold 0.55 (diset Day 12) cocok untuk `memory_search` tool (user explicitly searching). Tapi untuk PROACTIVE injection ke system prompt, threshold harus lebih ketat.

**Research Finding:** Zep production dan LlamaIndex merekomendasikan 0.70-0.75 untuk English. Untuk Bahasa Indonesia dengan multilingual MPNet, ada 5-8% deflasi → threshold optimal 0.65.

**Fix Applied (Day 16):** `vector_retrieval.py` menggunakan `RETRIEVAL_SCORE_THRESHOLD = 0.65` saat memanggil `search_semantic()`. Tool executor tetap pakai 0.55 (user-initiated search).

**Generalized Principle:**
> **"Threshold untuk proactive injection > threshold untuk user-requested search."** User search = user tahu apa yang mereka cari, bisa handle noise. Proactive injection = model tidak tahu apa yang ada di context, noise langsung merusak respons.

---

### [F-07] Qdrant Query API Membutuhkan ≥ v1.10.0 — Bukan v1.9.x
**Day:** 18 | **Severity:** HIGH | **Category:** Infrastructure / Version Compatibility

**Gejala:** `hybrid search plan: Prefetch + FusionQuery(RRF)` tidak ada di Qdrant v1.9.0. Import `Fusion, FusionQuery, Prefetch` dari `qdrant_client.models` berhasil (client-side), tapi `client.query_points()` throw error "unknown endpoint" atau method tidak ada.

**Root Cause:** Qdrant memisahkan fitur antara **client library** dan **server version**. `qdrant-client==1.12.x` bisa import `Prefetch`, `FusionQuery`, dll. Tapi jika server Qdrant-nya versi 1.9.0, Query API endpoint `/collections/{col}/query` tidak exist di server.

**Impact:** Hybrid search plan gagal sepenuhnya, fallback ke dense-only (tidak ada error crash, tapi kehilangan benefit +30-50% recall).

**Fix:** Upgrade Qdrant server ke v1.12.0 di docker-compose.yml:
```yaml
qdrant:
  image: qdrant/qdrant:v1.12.0  # was: v1.9.0
```

**Generalized Principle:**
> **"Qdrant client version ≠ Qdrant server version."** Selalu cek server version saat merencanakan fitur baru. Verifikasi via `GET /` endpoint: `{"version": "X.Y.Z"}`. Qdrant 1.10+ untuk hybrid Query API.

**Version Compatibility Table:**
| Feature | Min Server Version |
|---------|-------------------|
| Sparse vectors (basic) | 1.7.0 |
| Query API + Prefetch | **1.10.0** |
| Hybrid RRF fusion | **1.10.0** |

---

### [F-08] BM42 `embed()` vs `query_embed()` — Silent Wrong Results
**Day:** 18 | **Severity:** HIGH | **Category:** ML / Embedding

**Gejala:** Search results untuk query "Fahmi Wol CEO" mengembalikan results yang kurang relevan dari yang diharapkan.

**Root Cause:** BM42 adalah asymmetric embedding — menggunakan **berbeda token weighting** untuk documents vs queries. `model.embed()` = document mode (semua tokens weighted equally). `model.query_embed()` = query mode (IDF-weighted, fokus pada discriminative terms). Menggunakan `embed()` untuk queries = silently menggunakan weighting yang salah.

**Impact:** Search precision turun. Bukan error/crash — hasil tetap keluar, tapi dengan lower relevance. Sulit di-detect tanpa benchmarking.

**Fix Applied:**
```python
async def embed_sparse_document(text: str) -> QdrantSparseVector | None:
    result = model.embed([text], batch_size=1)  # Documents: embed()

async def embed_sparse_query(text: str) -> QdrantSparseVector | None:
    result = model.query_embed(text)  # Queries: query_embed() — WAJIB
```

**Generalized Principle:**
> **"BM42 dan semua asymmetric sparse embedding (SPLADE, etc.) WAJIB pakai query_embed() untuk queries."** Baca model card sebelum pakai. Default `embed()` tidak selalu benar.

---

### [F-06] Sort-by-Recency untuk RAG Injection = Silent Degradasi
**Day:** 16 | **Severity:** MEDIUM | **Category:** ML / Research

**Root Cause / Finding:** Research "Lost in the Middle" (arxiv 2505.15561) menunjukkan bahwa 7B model punya primacy attention bias — informasi di AWAL context mendapat perhatian lebih. Jika retrieved chunks diurutkan by recency (oldest first, most recent last), yang paling relevan mungkin jatuh di tengah → diabaikan.

**Impact:** 30% accuracy degradation pada recall tasks jika sort by recency vs sort by relevance.

**Fix Applied:** `format_episodic_context()` sort by `_retrieval_score` descending — yang paling relevan selalu di posisi [1] (pertama).

**Generalized Principle:**
> **"Untuk 7B injection: sort by relevance descending. Paling relevan = posisi pertama = primacy attention."** Jangan sort by timestamp untuk context injection. Timestamp hanya untuk display kepada user.

---

## ✅ KEBERHASILAN & POLA YANG BISA DILIPAT GANDAKAN

---

### [S-01] Fire-and-Forget Pattern dengan Strong Reference
**Day:** 12-15 | **Category:** Architecture

**Pattern:**
```python
_background_tasks: set[asyncio.Task] = set()  # Module level

async def chat(...):
    # After main response ready:
    _t = asyncio.create_task(heavy_background_work(...))
    _background_tasks.add(_t)
    _t.add_done_callback(_background_tasks.discard)
    # Return response immediately — zero latency impact
```

**Kenapa berhasil:** Zero response latency impact. Background work (embed, extract, critique) berjalan paralel dengan response HTTP. User tidak menunggu 30-60 detik.

**Replicate untuk:** Logging, analytics, indexing, any non-blocking enrichment task.

**Rule:** Background tasks BOLEH gagal. Main response tidak boleh diblock oleh background work.

---

### [S-02] Graceful Degradation di Setiap Layer
**Day:** 13-16 | **Category:** Resilience

**Pattern:** Setiap service external (Letta, Qdrant, Redis) diakses dengan fallback:
```python
# Letta:
letta_blocks = await get_letta_blocks(agent.letta_agent_id) if agent.letta_agent_id else {}
# Qdrant:
results = await asyncio.wait_for(search_semantic(...), timeout=1.5)
# jika timeout → return []
```

**Kenapa berhasil:** API tidak pernah down karena Letta/Qdrant unavailable. Core chat selalu berjalan.

**Principle:** **Setiap external call harus punya default empty/None return, bukan exception.** Exception = 500 ke user. Default empty = degraded but working.

---

### [S-03] Module-Ref untuk Lazily-Initialized Objects
**Day:** 15 | **Category:** Python Best Practice

**Pattern:**
```python
import models.base as _models_base  # NOT: from models.base import AsyncSessionLocal

# Always access at call time:
if _models_base.AsyncSessionLocal is None:
    return
async with _models_base.AsyncSessionLocal() as db:
    ...
```

**Rule:** `import module as _m` untuk semua objek yang diinisialisasi setelah startup. `from module import X` hanya untuk constants dan classes yang tidak berubah.

---

### [S-04] Structured JSON Output untuk Small Model (7B)
**Day:** 15 | **Category:** LLM Engineering

**Pattern:** Critique prompt menggunakan structured JSON format:
```
Balas HANYA dengan JSON valid:
{"score": <1-5>, "violations": [...], "suggestions": [...]}
```

**Kenapa berhasil:** 7B model lebih reliably output JSON saat:
1. Format dideskripsikan dengan contoh konkret
2. Instruksi "HANYA JSON" eksplisit
3. Model tidak diminta menjelaskan reasoning-nya

**Edge case handling:**
```python
start = raw.find("{")
end = raw.rfind("}") + 1
if start == -1 or end == 0:
    logger.warning("cai.critique_no_json", ...)
    return None
parsed = json.loads(raw[start:end])
```

**Generalized:** JSON extraction dengan `find("{")` + `rfind("}")` lebih robust daripada expect output bersih. Model kadang prefix dengan kalimat sebelum JSON.

---

### [S-05] Research-First Before Implementation
**Day:** 16 | **Category:** Process

**What worked:** Sebelum implement RAG retrieval, launch research agent untuk survei arxiv 2024-2026, production systems (Mem0, Zep, LangMem). Temuan langsung mempengaruhi decisions:
- Top-k = 3 (bukan 5 yang pertama direncanakan)
- Score threshold = 0.65 (bukan 0.55)
- Sort by relevance (bukan timestamp)

**Impact:** Keputusan yang lebih baik di pertama kali. Tidak perlu iterasi banyak karena decisions sudah research-backed.

**Generalized:** Untuk setiap feature baru, alokasi 30 menit untuk research sebelum coding. ROI-nya jauh lebih besar dari langsung coding.

---

### [S-07] Zero-Loss Migration via Scroll → Delete → Recreate → Re-upsert
**Day:** 18 | **Category:** Data Migration

**Pattern:** Migrasi collection schema (old unnamed dense → new named dense + sparse) tanpa kehilangan data:
```python
# 1. Fetch all with vectors
scroll_result = await client.scroll(collection_name=name, limit=10000,
    with_payload=True, with_vectors=True)
existing_points = scroll_result[0]

# 2. Delete old
await client.delete_collection(name)

# 3. Recreate hybrid
await _create_hybrid_collection(client, name)

# 4. Recompute sparse from chunk_text (already in payload)
for p in existing_points:
    chunk_text = p.payload.get("chunk_text", "")
    sparse_vec = await embed_sparse_document(chunk_text)
    # ... upsert with {dense: old_dense, sparse: sparse_vec}
```

**Kenapa berhasil:**
- `chunk_text` sudah tersimpan di payload sejak Day 12 (forward-looking design)
- Sparse vectors dihitung fresh dari teks yang sama → hasilnya identik
- Semua metadata/payload preserved as-is

**Generalized Principle:**
> **"Simpan raw text di payload saat indexing — bukan hanya vectors."** Raw text memungkinkan re-embedding ke schema baru tanpa kehilangan data. Ini adalah migration escape hatch.

---

### [S-08] Named Volume untuk Model Cache
**Day:** 18 | **Category:** Infrastructure / Performance

**Pattern:** Gunakan Docker named volume untuk caching AI model files:
```yaml
# docker-compose.yml:
services:
  api:
    volumes:
      - fastembed_cache:/app/.cache/fastembed

volumes:
  fastembed_cache:  # Persists across rebuilds
```

**Result:** BM42 model (90MB ONNX) tidak perlu re-download setiap `docker compose build api`.
- First time: ~4s download
- Subsequent starts: 108,100 it/s (instant cache hit)
- Saves 90MB traffic + 4s startup time per rebuild

**Generalized Principle:**
> **"AI models, pip cache, apt cache → named volumes, bukan bind mounts."** Named volumes survive `docker compose down` dan `docker compose build`. Data volume (`./data/`) untuk persistence. Model cache volume untuk performance.

---

### [F-09] Synthetic Training Data Hallucination Transfer
**Day:** 19 | **Severity:** HIGH | **Category:** ML Safety

**Gejala Potensial:** Jika content dari SIDIX (QA pairs, corpus_qa, finetune_sft.jsonl) digunakan sebagai seed data untuk synthetic DPO generation, model yang dilatih akan mengadopsi:
1. Fakta spesifik SIDIX yang mungkin salah (auto-generated hallucinations)
2. Brand identity SIDIX (persona, tone, sidq/sanad/tabayyun terminology)
3. Domain bias SIDIX yang tidak relevan untuk MiganCore

**Root Cause:** Training data kontaminasi — model belajar dari data yang mengandung sinyal salah. Synthetic data menggandakan jumlah pairs, bukan hanya memperkenalkan sedikit noise. Skala besar = amplifikasi hallucination.

**Impact:** Fine-tuned MiganCore model bisa hallucinate fakta SIDIX, menjawab dengan gaya SIDIX, atau confuse brand identity.

**Fix:**
- Import dari SIDIX: **HANYA** category names dan question framing patterns
- **JANGAN** import: `qa_pairs` answers, `corpus_qa` content, `finetune_sft.jsonl`
- Tag semua synthetic pairs: `source_method="synthetic_seed_v1"` → filter jika diperlukan
- Use validation set setelah training: test dengan SIDIX-specific queries untuk deteksi kontaminasi

**Generalized Principle:**
> **"Synthetic ≠ Safe jika seed dari sumber yang biased."** Sebelum import data dari project lain, identifikasi: (1) Apa yang aman (taxonomy, framing)? (2) Apa yang berbahaya (content, facts, persona)? (3) Bagaimana cara membatasi transfer? Tag source_method selalu — ini adalah recovery hatch jika kontaminasi terjadi.

---

### [S-09] Source Method Tagging untuk Multi-Source Training Data
**Day:** 19 | **Category:** ML Operations

**Pattern:** Setiap kali menambahkan sumber baru untuk preference pairs, gunakan `source_method` yang berbeda. Ini memungkinkan:
1. Analisis per-source di `/v1/admin/stats`
2. Filtering di training script: `WHERE source_method = 'cai_pipeline'` untuk real-only training
3. Audit trail: bisa debug masalah model dengan melihat distribusi training data

**Implemented sources:**
- `"cai_pipeline"` — real user conversations yang diproses CAI
- `"synthetic_seed_v1"` — synthetic generation dari Triple-Source seed bank (Day 19)

**Template untuk sumber baru:**
```python
await _store_preference_pair(
    prompt=..., chosen=..., rejected=..., score=score,
    source_message_id=None,          # None jika bukan dari message real
    source_method="new_source_v1",   # Deskriptif + versi
)
```

**Generalized Principle:**
> **"Data provenance adalah fitur, bukan detail."** Schema harus sudah ada kolom `source_method` sejak awal. Setiap sumber baru = tag baru. Ini seperti git blame untuk training data — penting untuk debugging post-training surprises.

---

### [S-06] Ulimits sebagai Checklist Deploy
**Day:** 16 | **Category:** Infrastructure

**Pattern:** Setiap service yang pakai RocksDB atau banyak files → set ulimits di docker-compose sebelum deploy.

```yaml
ulimits:
  nofile:
    soft: 65536
    hard: 65536
```

**Services yang butuh ini:** Qdrant, Kafka, TiKV, RocksDB direct, LevelDB, any embedded DB.

---

## 📊 PERFORMANCE BASELINES YANG TERUKUR

| Component | Metric | Value | Condition |
|-----------|--------|-------|-----------|
| Ollama 7B | Token throughput | 7-14 tok/s | CPU-only, VPS |
| CAI critique | Latency | ~22s | 7B, non-streaming, CPU |
| CAI revision | Latency | ~15s | 7B, ~400 tokens, CPU |
| Embedding (fastembed) | Latency | ~2-5s | paraphrase-multilingual-mpnet, CPU |
| Qdrant search (dense-only) | Latency | <200ms | <10k vectors, cosine, CPU |
| Qdrant search (hybrid RRF) | Latency | <300ms | dual Prefetch + FusionQuery |
| BM42 model load (fresh) | Latency | ~4s | 90MB ONNX download |
| BM42 model load (cached) | Latency | instant | Named volume cache hit |
| BM42 sparse embed | Latency | ~100ms | SparseTextEmbedding CPU |
| Redis ops | Latency | <5ms | local container |
| Letta get_blocks | Latency | ~500ms | httpx to Letta container |
| CAI pipeline total | Latency | ~37s | critique + revision + store |
| HTTP response | Latency | ~30-45s | with tool calling, CPU 7B |
| Synthetic generation (per seed) | Latency | ~60-120s | generate + critique + revise |
| Synthetic full run (120 seeds) | Duration | ~2-4 hours | CPU-only, sequential |

---

## 🧠 KEPUTUSAN ARSITEKTUR YANG TIDAK BOLEH DIUBAH (sampai ada alasan kuat)

| Keputusan | Alasan Dilock | Risiko Jika Diubah |
|-----------|---------------|-------------------|
| Celery DISABLED | RAM overhead tidak worth it untuk seed stage | Resource contention |
| Letta = PASSIVE STORAGE ONLY | Qwen2.5 Q4 tidak support Letta tool calls | API errors, unpredictable behavior |
| CAI_SAMPLE_RATE = 0.5 | CPU resource management | Queue buildup, response slowdown |
| JUDGE_MODEL = 7B | 0.5B fails Chat Hard (<50% accuracy) | Low quality preference pairs |
| `import module as _m` untuk singletons | Prevent frozen-value bug (F-03) | Silent failures |
| `_background_tasks` set | Prevent asyncio GC bug (F-02) | Silent task failures |
| Qdrant ulimits 65536 | RocksDB needs many FDs (F-04) | 500 errors pada collection ops |
| Score threshold 0.65 untuk injection | Research: 0.55 = noise injection | Model confusion |
| Sort by relevance (not recency) | Lost-in-middle research (F-06) | 30% accuracy drop |
| Qdrant ≥ v1.12.0 | Query API requires ≥1.10.0 (F-07) | Hybrid RRF unavailable |
| BM42 query_embed() untuk queries | Asymmetric embedding (F-08) | Silent precision drop |
| chunk_text di payload saat indexing | Zero-loss migration (S-07) | Data loss on schema change |
| Named volume fastembed_cache | Instant model reload (S-08) | 4s+ cold start per rebuild |
| SIDIX content NOT in seed bank | Hallucination transfer risk (F-09) | Model adopts SIDIX identity |
| source_method tag on all pairs | Multi-source audit trail (S-09) | Can't filter by provenance |
| asyncio.Semaphore(1) synthetic task | CPU-only VPS, no competition | Resource contention with inference |

---

## 🔮 DEBT TEKNIS YANG HARUS DISELESAIKAN SEBELUM BETA

| ID | Priority | Issue | Fix |
|----|----------|-------|-----|
| H4 | HIGH | `.venv` di-track git (membuat repo 1GB+) | `git rm -r --cached api/.venv` |
| H2 | MEDIUM | Raw SQL migrations (no Alembic) | Setup Alembic sebelum schema changes |
| M1 | MEDIUM | Chat rate limit pakai IP (harusnya user ID) | `request.state.user_id` sebagai rate limit key |
| T1 | LOW | `get_db()` duplikat di `models/base.py` | Hapus, gunakan `deps.db.get_db` saja |
| C2 | LOW | `reasoning_trace` tidak ada di `ChatResponse` schema | Add field ke `schemas/chat.py` |

---

## 📋 CHECKLIST SEBELUM DEPLOY (dari lessons learned)

```
Sebelum docker compose build:
□ Test kode lokal jika memungkinkan
□ Verifikasi tidak ada `from module import singleton` pattern

Setelah docker compose up -d api:
□ curl /health → verifikasi version number correct
□ docker exec ado-api-1 grep 'keyword_baru' /app/path/to/changed/file.py
□ Cek tidak ada syntax error di logs: docker logs ado-api-1 --since 30s

Setelah Qdrant restart/recreate:
□ docker exec ado-qdrant-1 cat /proc/1/limits | grep "open files"
  → Harus: 65536

Jika ada background task baru:
□ Verifikasi task disimpan di _background_tasks set
□ Verifikasi add_done_callback untuk cleanup
□ Test dengan 1 chat dan cek log untuk task confirmation

Jika ada import baru yang merupakan singleton:
□ Gunakan `import module as _m` pattern, bukan `from module import value`
```

---

*Dokumen ini adalah cognitive asset terpenting proyek. Update setiap sesi.*
