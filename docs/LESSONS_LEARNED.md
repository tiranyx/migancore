# MIGANCORE — LESSONS LEARNED
**Living Document — Updated setiap sesi**
**Last Update:** Day 16 | **Author:** Claude Sonnet 4.6

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
| Qdrant search | Latency | <200ms | <10k vectors, cosine, CPU |
| Redis ops | Latency | <5ms | local container |
| Letta get_blocks | Latency | ~500ms | httpx to Letta container |
| CAI pipeline total | Latency | ~37s | critique + revision + store |
| HTTP response | Latency | ~30-45s | with tool calling, CPU 7B |

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
