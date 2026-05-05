# MIGANCORE — FULL SYSTEM QA REPORT
**Tanggal:** 5 Mei 2026 (Day 38) | Bulan 2 Week 5
**Scope:** Review dari Day 1 sampai Day 37 — semua layer: API, Frontend, Training, Eval, Migrations, Docker, Teacher API, Distillation
**Compiled by:** Claude Sonnet 4.6 (fresh read seluruh codebase)
**Tujuan:** Handoff ke agent lain untuk debugging, testing, validasi, verifikasi

---

## RINGKASAN EKSEKUTIF

Total temuan: **65 issues**

| Severity | Jumlah | Aksi |
|----------|--------|------|
| 🔴 CRITICAL | 4 | Fix sebelum beta / public GitHub |
| 🟠 HIGH | 22 | Fix sebelum Cycle 1 training dan beta onboarding |
| 🟡 MEDIUM | 26 | Fix dalam Bulan 2 Week 6-7 |
| 🟢 LOW | 10 | Backlog, fix saat ada waktu |
| ℹ️ INFO | 3 | Dokumentasikan, bukan bug |

**Top 5 yang paling mendesak (bisa diselesaikan < 1 jam masing-masing):**
1. `[C1]` VPS IP publik hardcoded di `convert_gguf.py:125` — sudah bocor ke git history
2. `[C2]` Password `changeme` di `migrations/007_create_app_user.sql:11` — di git
3. `[C3]` Gemini API key masuk URL di logs via `teacher_api.py:291`
4. `[S4]` `eval()` / `exec()` tidak benar-benar diblokir di python_repl — CRITICAL security
5. `[L1]` `httpx.AsyncClient` bocor di `chat_stream` Phase B — memory leak production

---

## SECTION 1 — CRITICAL ISSUES (4)

### [C1] 🔴 CRITICAL | SECURITY | VPS IP Hardcoded di Source Code
**File:** `training/convert_gguf.py`, line 125
**Kode:**
```python
print(f"  ssh root@72.62.125.6")
```
**Masalah:** IP address VPS produksi ter-expose di source code yang ada di GitHub repo. Sudah masuk git history. Siapapun dengan akses repo bisa tahu IP target untuk port scanning / brute-force SSH.
**Fix:** Ganti dengan `os.environ.get("VPS_HOST", "<VPS_IP>")` atau hapus baris ini sepenuhnya.
**Action:** `git filter-branch` / BFG Repo Cleaner untuk hapus dari history SEBELUM repo dibuat public.

---

### [C2] 🔴 CRITICAL | SECURITY | Password Database Hardcoded di Migration
**File:** `migrations/007_create_app_user.sql`, line 11
**Kode:**
```sql
CREATE ROLE ado_app WITH LOGIN PASSWORD 'changeme';
```
**Masalah:** Password default `changeme` tersimpan permanen di git history. Bahkan jika sudah diubah di production, siapapun tahu default-nya.
**Fix:** Hapus dari migration, set password via deployment script yang tidak di-commit:
```bash
# deploy.sh (tidak di git)
psql -c "ALTER ROLE ado_app PASSWORD '$PG_APP_PASSWORD'"
```
**Action:** Sama — BFG Repo Cleaner sebelum public, dan rotate password sekarang.

---

### [C3] 🔴 CRITICAL | SECURITY | Gemini API Key Masuk URL → Bocor ke Logs
**File:** `api/services/teacher_api.py`, line ~291
**Kode:**
```python
url = f"https://generativelanguage.googleapis.com/...?key={settings.GEMINI_API_KEY}"
```
**Masalah:** API key di URL akan muncul di: httpx debug logs, nginx access logs, Python tracebacks, structlog request logs. Semua provider lain menggunakan header `Authorization: Bearer`.
**Fix:**
```python
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
headers = {"x-goog-api-key": settings.GEMINI_API_KEY, "Content-Type": "application/json"}
resp = await client.post(url, json=payload, headers=headers)
```

---

### [C4] 🔴 CRITICAL | SECURITY | `eval()` / `exec()` Tidak Benar-Benar Diblokir di python_repl
**File:** `api/services/tool_policy.py`, lines ~200-206
**Kode:**
```python
for d in ["eval(", "exec(", "compile("]:
    if d in code:
        pass  # <-- seharusnya raise PolicyViolation!
```
**Masalah:** Code mendeteksi `eval(`, `exec(`, `compile(` tapi melakukan `pass` — tidak ada blocking! Artinya `exec(open('/etc/passwd').read())` LOLOS ke subprocess. Import blacklist juga mudah di-bypass: `__import__('o'+'s').system('id')` tidak terdeteksi pola regex.
**Fix:**
```python
for d in ["eval(", "exec(", "compile("]:
    if d in code:
        raise PolicyViolation(
            reason=f"Use of '{d}' is blocked in python_repl",
            violation_type="python_repl_dangerous_builtin"
        )
```

---

## SECTION 2 — HIGH SEVERITY (22)

### [H1] 🟠 HIGH | SECURITY | Timing Attack pada Admin Key Comparison
**File:** `api/routers/admin.py`, line ~71
**Kode:**
```python
if x_admin_key != settings.ADMIN_SECRET_KEY:
```
**Masalah:** Python `!=` tidak constant-time. Attacker bisa brute-force admin key karakter per karakter via timing oracle.
**Fix:** `if not secrets.compare_digest(x_admin_key or "", settings.ADMIN_SECRET_KEY):`

---

### [H2] 🟠 HIGH | SECURITY | Admin Endpoints Tanpa Rate Limiting
**File:** `api/routers/admin.py`, semua endpoint
**Masalah:** Chat endpoint punya `@limiter.limit("30/minute")`, tapi semua `/v1/admin/*` tidak ada rate limit sama sekali. Brute-force admin key trivial karena tidak ada throttling.
**Fix:** Tambahkan `@limiter.limit("5/minute")` di semua admin route handler.

---

### [H3] 🟠 HIGH | SECURITY | JWT di localStorage — 7-Hari Refresh Token Exposed
**File:** `frontend/chat.html`, lines ~897-922, ~1504-1505
**Kode:**
```javascript
LS.set('token', data.access_token)
LS.set('refresh_token', data.refresh_token)
```
**Masalah:** Refresh token dengan TTL 7 hari di localStorage = full account takeover selama 7 hari jika ada XSS. Setiap extension browser bisa baca localStorage.
**Fix:** Pindahkan refresh token ke `HttpOnly; Secure; SameSite=Strict` cookie. Access token boleh di memori JS saja (variable, bukan localStorage).

---

### [H4] 🟠 HIGH | SECURITY | python_repl Berjalan Tanpa Namespace Isolation
**File:** `api/services/tool_executor.py`, lines ~265-269
**Masalah:** `subprocess.run(["python", "-c", code], ...)` dijalankan sebagai user yang sama dengan API process, tanpa seccomp/network namespace/chroot. Import blacklist bisa di-bypass via string concatenation: `__import__('o'+'s').system('id')`.
**Fix:** Gunakan E2B sandbox API (sudah ada di blueprint dan dependencies) atau Docker `--network none --read-only` untuk sandboxing. Minimal tambah obfuscation detection ke regex.

---

### [H5] 🟠 HIGH | SECURITY | `analyze_image` Rentan SSRF
**File:** `api/services/tool_executor.py`, lines ~521-532
**Masalah:** `_fetch_image_bytes(image_url)` dengan `follow_redirects=True` mengikuti URL manapun termasuk `http://169.254.169.254` (cloud metadata), `http://redis:6379`, internal services.
**Fix:**
```python
from ipaddress import ip_address, ip_network
BLOCKED_NETWORKS = [ip_network("169.254.0.0/16"), ip_network("10.0.0.0/8"), ...]
# resolve hostname, check against BLOCKED_NETWORKS before fetch
```

---

### [H6] 🟠 HIGH | SECURITY | `X-Forwarded-For` Trusted Tanpa Validasi
**File:** `api/routers/auth.py`, lines ~54-58
**Masalah:** `forwarded.split(",")[0].strip()` mempercayai header tanpa validasi — attacker bisa kirim `X-Forwarded-For: 127.0.0.1` untuk bypass rate limiting dan memalsukan audit log.
**Fix:** Konfigurasi `trusted_hosts` di nginx sehingga hanya IP nginx yang trusted untuk forwarding.

---

### [H7] 🟠 HIGH | SECURITY | Default Credentials di config.py Tidak Fail-Safe
**File:** `api/config.py`, lines ~35, 39
**Kode:**
```python
DATABASE_URL: str = "postgresql+asyncpg://ado_app:changeme@postgres:5432/ado"
REDIS_URL: str = "redis://:changeme@redis:6379/0"
```
**Masalah:** Jika `.env` tidak terpasang, app jalan dengan password `changeme`.
**Fix:** Ubah default ke `None` dengan validator:
```python
DATABASE_URL: Optional[str] = None
@validator("DATABASE_URL")
def validate_db(cls, v): 
    if not v: raise ValueError("DATABASE_URL must be set")
    return v
```

---

### [H8] 🟠 HIGH | LOGIC | Quota Bypass via Stream Endpoint
**File:** `api/routers/chat.py`, endpoint `chat_stream` vs `chat`
**Masalah:** `POST /chat` memanggil `_check_tenant_message_quota()`, tapi `POST /chat/stream` **tidak**. User bisa bypass daily message quota dengan menggunakan stream endpoint.
**Fix:** Tambahkan quota check di stream preflight phase sebelum user message persist.

---

### [H9] 🟠 HIGH | LOGIC | `message_count` Race Condition pada Concurrent Chat
**File:** `api/routers/chat.py`, lines ~516-518
**Masalah:** `message_count = len(history) + 2` dihitung di awal request. Pada concurrent requests, absolute value override akan corrupt count.
**Fix:** Gunakan SQL increment: `SET message_count = message_count + 2` bukan absolute value.

---

### [H10] 🟠 HIGH | LEAK | `OllamaClient` httpx Tidak Di-Close di Stream Phase B
**File:** `api/routers/chat.py`, lines ~479-483
**Kode:**
```python
stream_iter = OllamaClient().chat_stream(...)  # tidak pakai async with!
```
**Masalah:** `OllamaClient()` dibuat tapi tidak di-manage sebagai context manager. Pada `CancelledError`, `httpx.AsyncClient` tidak di-close → connection leak di production. Phase A sudah benar menggunakan `async with`.
**Fix:** 
```python
async with OllamaClient() as oc:
    stream_iter = oc.chat_stream(...).__aiter__()
```

---

### [H11] 🟠 HIGH | LEAK | Redis Client di distillation.py Tanpa Pool/Close
**File:** `api/services/distillation.py`, lines ~60-66
**Masalah:** `_redis_client = aioredis.from_url(...)` tanpa `ConnectionPool` dan tidak ada `aclose()` di app shutdown. Berbeda dengan `synthetic_pipeline.py` yang sudah benar menggunakan `ConnectionPool`.
**Fix:** Gunakan `ConnectionPool` dan daftarkan di FastAPI lifespan teardown.

---

### [H12] 🟠 HIGH | DATA | Conversation Content dari Tenants Masuk Training Data Tanpa Consent
**File:** `api/services/cai_pipeline.py`, lines ~270-326
**Masalah:** `preference_pairs` intentionally global (no RLS), tapi ini berarti real conversation content dari setiap tenant masuk ke global training table dan bisa di-export via `/v1/admin/export`. Tenant A tidak tahu bahwa conversation mereka digunakan untuk training.
**Fix:** Minimal tambah `tenant_id` di `preference_pairs` untuk audit trail. Pertimbangkan masking/anonymization user content sebelum storage.

---

### [H13] 🟠 HIGH | DATA | `api_keys` Tabel Tanpa RLS
**File:** `migrations/025_day27_api_keys.sql`
**Masalah:** Tabel `api_keys` berisi credential sensitif tapi tidak ada `ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY`.
**Fix:**
```sql
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_api_keys ON api_keys
    USING (tenant_id = (NULLIF(current_setting('app.current_tenant', true), ''))::uuid);
```

---

### [H14] 🟠 HIGH | DATA | Migration Numbering Conflict — Dua File dengan Prefix `010` dan `011`
**File:** `migrations/010_users_rls_security_definer.sql` dan `migrations/010_day10_schema_sync.sql`; `migrations/011_add_agent_fields.sql` dan `migrations/011_day11_safety_gates.sql`
**Masalah:** Jika migration runner menggunakan numeric ordering, execution order ambigu → bisa skip atau double-execute.
**Fix:** Renumber: `010_day10_schema_sync.sql` → `010b_...` dan `011_add_agent_fields.sql` → `011b_...`. Atau gunakan Alembic yang track via hash.

---

### [H15] 🟠 HIGH | TRAINING | Hanya 5 dari 50 Identity Anchors yang Ada
**File:** `training/export_dataset.py`, line ~41
**Masalah:** Komentar sendiri mengakui "45 more should be added". Dengan hanya 5 anchors dari 700 total samples (0.7%), identity preservation selama training sangat lemah → persona drift hampir pasti.
**Fix:** Lengkapi ke 50 anchors dari `eval/persona_consistency_v1.jsonl` sebelum Cycle 1 training di-trigger.

---

### [H16] 🟠 HIGH | TRAINING | Dataset Format Tidak Divalidasi Sebelum Training
**File:** `training/train_simpo.py`, line ~144
**Masalah:** Training bisa dimulai dengan dataset yang tidak punya kolom `prompt`/`chosen`/`rejected` — SimPOTrainer crash saat training dengan error tidak jelas, setelah RunPod billing sudah jalan.
**Fix:**
```python
required = {"prompt", "chosen", "rejected"}
missing = required - set(ds.column_names)
if missing:
    raise ValueError(f"Dataset missing required columns: {missing}")
```

---

### [H17] 🟠 HIGH | TRAINING | APO Anchor Loss Tidak Ada Label Masking
**File:** `training/train_simpo.py`, lines ~185-209
**Masalah:** APO anchor loss menghitung loss pada seluruh sequence (prompt + response), bukan hanya response tokens. Ini mengakibatkan over-penalization pada prompt tokens yang tidak seharusnya masuk identity loss.
**Fix:** Gunakan label masking untuk skip prompt tokens: set `labels[:prompt_length] = -100` sebelum compute anchor loss.

---

### [H18] 🟠 HIGH | DISTILLATION | Race Condition di `start_distillation`
**File:** `api/services/distillation.py`, lines ~428-438
**Masalah:** Ada async gap antara check `_running_task.done()` dan `asyncio.create_task(...)` → dua concurrent requests ke `/distillation/start` bisa membuat dua tasks sekaligus.
**Fix:**
```python
_distill_lock = asyncio.Lock()
async def start_distillation(...):
    async with _distill_lock:
        if _running_task and not _running_task.done():
            return {"status": "rejected"}
        _running_task = asyncio.create_task(...)
```

---

### [H19] 🟠 HIGH | DISTILLATION | Budget Cap Undercount — Judge Cost Tidak Di-Track
**File:** `api/services/distillation.py`, lines ~358-365
**Masalah:** `telem["cost_usd"]` hanya mencatat biaya teacher call, bukan judge call. Budget cap check menggunakan nilai yang undercount → bisa overspend.
**Fix:** Return dan accumulate judge cost ke `telemetry["cost_usd"]` di `_judge_pair`.

---

### [H20] 🟠 HIGH | DISTILLATION | Judge Independence Bypass jika Fallback Tidak Tersedia
**File:** `api/services/distillation.py`, lines ~225-226
**Masalah:** Jika teacher == "claude" dan kimi tidak tersedia, fallback ke "gpt" tanpa cek ketersediaan GPT. Jika GPT juga tidak ada → error diam-diam, pair di-drop.
**Fix:** Gunakan list comprehension untuk semua tersedia, bukan hardcoded cascade.

---

### [H21] 🟠 HIGH | EVAL | Reference File Path Tidak Divalidasi
**File:** `eval/run_identity_eval.py`, lines ~114-117
**Masalah:** `with open(reference_path, "r")` akan raise `FileNotFoundError` tanpa pesan konteks jika file tidak ada. Default path adalah relative `references_baseline.json` → bisa mencari di tempat salah.
**Fix:** Gunakan absolute path dan tambahkan explicit error message.

---

### [H22] 🟠 HIGH | DOCKER | Letta dan ado Menggunakan Role Database yang Sama
**File:** `docker-compose.yml`, line ~79
**Masalah:** `LETTA_PG_URI` menggunakan `ado_app` role yang sama dengan API. Jika ado_app dikompromikan, akses ke letta_db juga terbuka.
**Fix:** Buat role terpisah `letta_app` dengan password `LETTA_PG_PASSWORD`.

---

## SECTION 3 — MEDIUM SEVERITY (26)

### [M1] 🟡 MEDIUM | SECURITY | Pagination Tidak Dibatasi di conversations.py
**File:** `api/routers/conversations.py`
**Masalah:** `limit: int = 20`, `offset: int = 0` tanpa constraint. User bisa `?limit=999999` → DB overload.
**Fix:** `limit: int = Query(default=20, ge=1, le=200)`, `offset: int = Query(default=0, ge=0)`

---

### [M2] 🟡 MEDIUM | SECURITY | Regex ReDoS Potensi di `analyze_image` Scrape
**File:** `api/services/tool_executor.py`
**Masalah:** `re.search(pattern, html, re.DOTALL)` dengan pattern dari LLM/user tanpa validasi complexity → ReDoS possible.
**Fix:** Tambahkan `asyncio.wait_for` di sekeliling regex execution dengan timeout 1s.

---

### [M3] 🟡 MEDIUM | LOGIC | `_apply_cached_summary` Off-by-One Edge Case
**File:** `api/routers/chat.py`, line ~906
**Masalah:** Jika `head_count == len(history)`, code return history asli tanpa inject summary.
**Fix:** Handle `head_count == len(history)` sebagai `return ([], sys_msg)`.

---

### [M4] 🟡 MEDIUM | LOGIC | Refresh Token Check Expiry Setelah DB Write
**File:** `api/routers/auth.py`, lines ~371-376
**Masalah:** Expired token di-revoke di DB tanpa rollback. Inkonsistensi state — expired token seharusnya dibiarkan expired, bukan direvoke.
**Fix:** Cek `expires_at < now` sebelum atomic UPDATE.

---

### [M5] 🟡 MEDIUM | LOGIC | Synthetic Pipeline: Error Loop pada Startup jika Ollama Down
**File:** `api/main.py`, lines ~183-207
**Masalah:** Auto-resume pada startup juga meresume status `"error"` → infinite error loop jika Ollama down saat deploy.
**Fix:** Tambahkan `"error"` ke set skip: `not in ("idle", "completed", "error")`.

---

### [M6] 🟡 MEDIUM | LOGIC | `get_current_user` Tidak Cast UUID dengan Benar
**File:** `api/deps/auth.py`, line ~81
**Masalah:** `user_id` adalah string dari JWT. Jika `sub` adalah None, query return empty dan auth gagal dengan 401 tanpa pesan bermakna.
**Fix:** `uuid.UUID(user_id)` dengan explicit `try/except ValueError → 401`.

---

### [M7] 🟡 MEDIUM | LOGIC | UUID Parse Error → HTTP 500 di Multiple Endpoints
**File:** `api/routers/conversations.py:112`, `api/routers/agents.py`, `api/routers/chat.py`
**Masalah:** `uuid.UUID(id_string)` tanpa try/except → malformed UUID dari user menghasilkan HTTP 500 bukan 400/422.
**Fix:** Buat helper `parse_uuid_or_422(val: str) -> uuid.UUID` dan gunakan secara konsisten.

---

### [M8] 🟡 MEDIUM | LOGIC | Quota Counter Di-Increment Sebelum Request Selesai
**File:** `api/routers/chat.py`, lines ~45-66
**Masalah:** `tenant.messages_today += 1` di-commit sebelum Ollama call. Jika Ollama gagal, kuota tetap ter-consume.
**Fix:** Increment hanya setelah response berhasil, atau decrement on error dalam finally block.

---

### [M9] 🟡 MEDIUM | DATA | Duplicate Preference Pairs — Tidak Ada Deduplication
**File:** `api/services/cai_pipeline.py`
**Masalah:** Tidak ada `UNIQUE constraint` pada `source_message_id`. Retry/duplicate create_task bisa menghasilkan duplicate training pairs.
**Fix:** Tambah migration: `ALTER TABLE preference_pairs ADD CONSTRAINT unique_source_msg UNIQUE (source_message_id)` dengan NULL handling.

---

### [M10] 🟡 MEDIUM | DATA | `preference_pairs` Tidak Punya Index pada `source_method`
**File:** `init.sql`, lines ~189-203
**Masalah:** `export_dataset.py` query `WHERE source_method LIKE :pattern` tanpa index → full table scan pada 10k+ pairs.
**Fix:** `CREATE INDEX idx_prefs_source ON preference_pairs(source_method, used_in_training);`

---

### [M11] 🟡 MEDIUM | DATA | `messages.tenant_id` dan `interactions_feedback.tenant_id` Tanpa FK
**File:** `init.sql`
**Masalah:** Inkonsistensi — `conversations.tenant_id` punya FK ke tenants, tapi `messages` dan `interactions_feedback` tidak.
**Fix:** `ALTER TABLE messages ADD CONSTRAINT fk_messages_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id);`

---

### [M12] 🟡 MEDIUM | DATA | `admin.preference-pairs` Filter Pattern Rentan Refactor SQL Injection
**File:** `api/routers/admin.py`, lines ~226-255
**Masalah:** `where_clause = f"WHERE {' AND '.join(conditions)}"` — pattern string concatenation berbahaya jika ada pengembang tambah filter baru dari user input.
**Fix:** Refactor ke SQLAlchemy ORM `select(PreferencePair).where(...)`.

---

### [M13] 🟡 MEDIUM | TRAINING | Total Dataset Bisa Jauh Kurang dari Target Tanpa Warning
**File:** `training/export_dataset.py`, line ~62
**Masalah:** Mix targets dihitung berdasarkan persentase, tapi tidak ada check jika DB tidak punya cukup data di setiap bucket.
**Fix:** Tambah warning `if total < target_size * 0.8: logger.warning("Dataset smaller than target")`.

---

### [M14] 🟡 MEDIUM | TRAINING | `distill_query` Dead Code
**File:** `training/export_dataset.py`, lines ~70-78
**Masalah:** `distill_query` didefinisikan tapi tidak pernah digunakan. Menyesatkan pembaca.
**Fix:** Hapus baris 70-78.

---

### [M15] 🟡 MEDIUM | TRAINING | SimPO Training Tanpa Checkpoint Jika Dataset Kecil
**File:** `training/train_simpo.py`, line ~53
**Masalah:** `save_steps=50` tapi jika dataset < 50 steps, tidak ada checkpoint sampai akhir. RunPod interruption = training hilang.
**Fix:** `save_steps=min(50, estimated_steps_per_epoch // 2)` atau `save_strategy="epoch"`.

---

### [M16] 🟡 MEDIUM | EVAL | Error Results Masuk Average Cosine Calculation
**File:** `eval/run_identity_eval.py`, line ~151
**Masalah:** Exception → `sim = 0.0` masuk ke `results` list → menurunkan `avg_sim` artifisial → bisa trigger false ROLLBACK.
**Fix:** Exclude entries dengan error dari average calculation, flag terpisah dalam summary.

---

### [M17] 🟡 MEDIUM | EVAL | Embedding Dimension Tidak Divalidasi Antara Reference dan Eval Run
**File:** `eval/run_identity_eval.py`, lines ~78-84
**Masalah:** Jika model embedding berubah antara reference dan eval run, `np.dot(a, b)` raise `ValueError` tanpa pesan jelas.
**Fix:** `assert len(a) == len(b), "Embedding dimension mismatch — regenerate references"`

---

### [M18] 🟡 MEDIUM | DOCKER | API Service Tanpa CPU Limit
**File:** `docker-compose.yml`, lines ~93-94
**Masalah:** Memory limit ada (`2G`) tapi tidak ada `cpus` limit. Distillation + inference bisa saturate 8 cores.
**Fix:** Tambahkan `cpus: "2.0"` di deploy.resources.limits untuk api service.

---

### [M19] 🟡 MEDIUM | DOCKER | Gemini `BLOCK_NONE` Safety — Konten Berbahaya Bisa Masuk Training Data
**File:** `api/services/teacher_api.py`, line ~279
**Masalah:** Semua safety filter dinonaktifkan untuk teacher. Adversarial seed prompt bisa menghasilkan konten berbahaya yang masuk ke `preference_pairs.chosen`.
**Fix:** Pertahankan minimal `HARM_CATEGORY_DANGEROUS_CONTENT` pada `BLOCK_ONLY_HIGH`.

---

### [M20] 🟡 MEDIUM | DISTILLATION | Judge Position Bias — A/B Tidak Di-Randomize
**File:** `api/services/distillation.py`
**Masalah:** Judge prompt selalu menaruh student di "JAWABAN A" dan teacher di "JAWABAN B". LLM judge bisa punya recency/position bias.
**Fix:** Randomize A/B assignment per pair dan swap `score_a`/`score_b` accordingly.

---

### [M21] 🟡 MEDIUM | DISTILLATION | Redis Run Status TTL Hanya 24 Jam
**File:** `api/services/distillation.py`, line ~297
**Masalah:** Status distillation run tidak bisa dilihat setelah 24 jam → analytics hilang.
**Fix:** Tambah tabel `distillation_runs` di DB untuk persistence, atau set TTL 7 hari.

---

### [M22] 🟡 MEDIUM | DISTILLATION | Teacher System Prompt Hardcoded — Tidak Sync dengan SOUL.md
**File:** `api/services/distillation.py`
**Masalah:** Teacher system prompt di `_build_teacher_system_prompt()` hardcoded, tidak baca dari SOUL.md. Jika SOUL.md diupdate, teacher prompt tidak ikut.
**Fix:** Baca dari `config/01_SOUL.md` atau `api/../docs/01_SOUL.md` dengan fallback ke hardcoded.

---

### [M23] 🟡 MEDIUM | FRONTEND | Conversation History (PII) di localStorage
**File:** `frontend/chat.html`
**Masalah:** `mc_msgs` (conversation content) disimpan di localStorage → PII tidak terenkripsi di browser. Semua extension browser bisa baca.
**Fix:** Jangan persist conversation history ke localStorage; fetch dari API saat load.

---

### [M24] 🟡 MEDIUM | FRONTEND | XSS Potensi dari LLM Response — Tidak Ada DOMPurify
**File:** `frontend/chat.html`, tidak ada sanitizer library
**Masalah:** React default escapes `{variable}` — aman sekarang. Tapi jika ada PR yang tambah `dangerouslySetInnerHTML` untuk markdown rendering, XSS terbuka. Pre-emptive protection lebih aman.
**Fix:** Import DOMPurify dan buat wrapper `safeHtml(content)` sebagai guard sebelum markdown rendering ditambahkan.

---

### [M25] 🟡 MEDIUM | FRONTEND | CDN Libraries Tanpa SRI Hash
**File:** `frontend/chat.html`, `frontend/dashboard.html`, lines ~12-20
**Masalah:** React, ReactDOM, Babel, D3, CompressorJS di-load dari CDN (unpkg, cdn.jsdelivr.net) tanpa `integrity="sha256-..."` attribute. CDN compromise = XSS ke semua users.
**Fix:** Tambahkan `integrity` hash dan `crossorigin="anonymous"` pada setiap script tag.

---

### [M26] 🟡 MEDIUM | MIGRATIONS | `ivfflat` Index pada Empty Table — Low Recall Awal
**File:** `init.sql`, lines ~280-281
**Masalah:** IVFFlat dengan `lists=100` butuh minimal ~3900 rows untuk training yang akurat. Di atas empty table, index terbentuk tapi recall buruk.
**Fix:** Gunakan `hnsw` yang tidak butuh training phase, atau buat index setelah data cukup.

---

## SECTION 4 — LOW SEVERITY (10)

### [L1] 🟢 LOW | `_background_tasks` Set Bisa Grow Unbounded
**File:** `api/routers/chat.py`
**Masalah:** Module-level `set` tasks tidak ada max size. High traffic = ribuan tasks pending.
**Fix:** Log warning jika `len(_background_tasks) > 200`.

---

### [L2] 🟢 LOW | Redis Pools di Multiple Services Tidak Di-Close pada Shutdown
**File:** `api/services/tool_policy.py`, `api/services/synthetic_pipeline.py`, `api/services/distillation.py`
**Masalah:** Multiple `ConnectionPool` dibuat tapi tidak ada teardown di lifespan shutdown.
**Fix:** Daftarkan semua pool di FastAPI lifespan teardown via `await pool.aclose()`.

---

### [L3] 🟢 LOW | `API_KEY_PEPPER` Tidak Warn Saat Production
**File:** `api/services/api_keys.py`
**Masalah:** Fallback ke SHA256 of JWT private key di production tanpa warning.
**Fix:** `if settings.ENVIRONMENT == "production" and not pepper: raise RuntimeError("API_KEY_PEPPER must be set")`

---

### [L4] 🟢 LOW | `ollama` Docker Image Menggunakan `:latest` Tag
**File:** `docker-compose.yml`
**Masalah:** `ollama/ollama:latest` bisa berubah dan breaking compatibility.
**Fix:** Pin ke versi spesifik: `ollama/ollama:0.6.0`.

---

### [L5] 🟢 LOW | Training `convert_gguf.py` — cmake Tidak Ada Timeout
**File:** `training/convert_gguf.py`
**Masalah:** `subprocess.run` tanpa `timeout=` → proses cmake bisa hang selamanya di RunPod.
**Fix:** Tambah `timeout=3600` parameter.

---

### [L6] 🟢 LOW | Training `convert_gguf.py` — llama.cpp Clone Path Hardcoded
**File:** `training/convert_gguf.py`, line ~63
**Masalah:** Clone ke `/workspace/llama.cpp` hardcoded hanya valid di RunPod pod.
**Fix:** Jadikan configurable: `--llama-cpp-dir` argparse parameter.

---

### [L7] 🟢 LOW | Eval Output Ditulis ke Relative Path
**File:** `eval/run_identity_eval.py`, line ~172
**Masalah:** `out = f"eval_result_{model_tag}.json"` ditulis ke CWD saat runtime.
**Fix:** Gunakan `Path(__file__).parent / out` atau argparse `--output` parameter.

---

### [L8] 🟢 LOW | Eval Temperature Berbeda Antara Reference dan Eval Run
**File:** `eval/run_identity_eval.py`
**Masalah:** Reference dan eval mungkin menggunakan temperature yang berbeda — cosine similarity lebih rendah bukan karena model lebih buruk.
**Fix:** Simpan `options` yang digunakan dalam reference JSON dan re-use saat eval.

---

### [L9] 🟢 LOW | `tools.name` Global Unique Constraint Gap (NULL != NULL di PostgreSQL)
**File:** `init.sql`
**Masalah:** `UNIQUE(tenant_id, name)` tidak melindungi dua global tools (tenant_id IS NULL) dengan nama sama.
**Fix:** `CREATE UNIQUE INDEX idx_global_tools_name ON tools(name) WHERE tenant_id IS NULL;`

---

### [L10] 🟢 LOW | Model Seed `model_versions` Tag Tidak Konsisten dengan Deployment
**File:** `init.sql`, lines ~392-394
**Masalah:** Seed tag `v0.1-seed-2026-05` tidak konsisten dengan naming di code dan training scripts.
**Fix:** Sinkronkan seed tag dengan production convention.

---

## SECTION 5 — INFO (3)

### [I1] ℹ️ INFO | Logout Endpoint Tidak Require Auth — Intentional tapi Tidak Didokumentasikan
**File:** `api/routers/auth.py`
**Status:** Intentional design (logout before access token available). Pastikan didokumentasikan dan bukan oversight.

---

### [I2] ℹ️ INFO | Letta Berjalan Tapi Tidak Fully Wired
**File:** `docker-compose.yml`, `api/services/letta.py`
**Status:** Letta service berjalan di port 8083 (internal), tapi hanya digunakan sebagai persona block storage, bukan sebagai agent runtime. `agents.messages.create()` tidak digunakan (by design — Qwen2.5-7B Q4 tidak support Letta tool calls). Didokumentasikan di CONTEXT.md. Fine as-is.

---

### [I3] ℹ️ INFO | Celery Disabled by Design
**File:** `docker-compose.yml`
**Status:** Celery dan Langfuse disabled intentionally untuk seed stage (RAM constraint). Didokumentasikan. Fine as-is untuk Bulan 2.

---

## SECTION 6 — TEST CHECKLIST UNTUK QA AGENT

Setelah semua fix di-apply, gunakan checklist ini untuk testing:

### AUTH
- [ ] `POST /v1/auth/register` dengan email yang sama dua kali → 409
- [ ] `POST /v1/auth/login` dengan password salah 5x dalam 1 menit → 429
- [ ] `POST /v1/auth/refresh` dengan expired refresh token → 401
- [ ] `GET /v1/auth/me` dengan malformed JWT → 401 (bukan 500)
- [ ] Cross-tenant: User tenant A tidak bisa akses agent tenant B → 404

### PYTHON_REPL SECURITY (Priority setelah [C4] fix)
- [ ] `eval("__import__('os').listdir('/')")` → PolicyViolation, bukan execution
- [ ] `exec("import os; os.system('id')")` → PolicyViolation
- [ ] `__import__('o'+'s').system('id')` → PolicyViolation (obfuscated import)
- [ ] `open('/etc/passwd').read()` → PolicyViolation (restricted file access)
- [ ] Normal Python `print(1+1)` → berhasil, return "2"

### CHAT QUOTA
- [ ] `POST /chat/stream` mengurangi `messages_today` (setelah [H8] fix)
- [ ] User yang reach daily limit via `/chat/stream` tidak bisa `/chat` juga

### PAGINATION
- [ ] `GET /v1/conversations?limit=999999` → 422 Unprocessable (setelah [M1] fix)
- [ ] `GET /v1/conversations?offset=-1` → 422

### UUID VALIDATION
- [ ] `GET /v1/agents/not-a-uuid` → 422 (bukan 500)
- [ ] `GET /v1/conversations/not-a-uuid` → 422

### RATE LIMITING
- [ ] Brute-force admin key 100× → 429 (setelah [H2] fix)
- [ ] `/v1/auth/login` lebih dari 5/menit → 429

### TRAINING PIPELINE
- [ ] `python training/export_dataset.py` dengan DB < target → warning tapi tidak crash
- [ ] Dataset dengan kolom hilang → ValueError clear sebelum training dimulai
- [ ] `python eval/run_identity_eval.py --mode reference` tanpa eval file → error jelas
- [ ] `python eval/run_identity_eval.py --mode eval` dengan reference dari run lain → dimension check

### SSE STREAMING
- [ ] Cancel mid-stream → partial response tersimpan dengan `[stopped by user]` marker
- [ ] Koneksi dropped setelah 600s → tidak timeout (nginx fix sudah apply)
- [ ] `TypeError: network error` harus muncul pesan friendly bukan raw error

### DISTILLATION
- [ ] Dua concurrent POST ke `/v1/admin/distill/start` → hanya satu berhasil (setelah [H18] fix)
- [ ] Budget habis mid-run → stop dengan status `budget_exceeded`

### GENEALOGY
- [ ] Spawn child dari child (G2) masih bisa, max depth G5
- [ ] Spawn di depth G5 → 422 (max depth exceeded)
- [ ] Genealogy tree menampilkan semua agent dengan warna per generation

---

## SECTION 7 — PRIORITIZED FIX SCHEDULE

### Sprint 1 — ✅ SELESAI (2026-05-05)
1. `[C4]` ✅ Fix `pass` → `raise PolicyViolation` di python_repl — `tool_policy.py:201`
2. `[H1]` ✅ Fix timing attack admin key dengan `secrets.compare_digest` — `admin.py:72`
3. `[C3]` ✅ Fix Gemini API key → header `x-goog-api-key` — `teacher_api.py:292`
4. `[H10]` ✅ Fix httpx leak di stream Phase B dengan `async with OllamaClient()` — `chat.py:483`
5. `[H8]` ✅ Tambah quota check di `chat_stream` sebelum stream dimulai — `chat.py:329`
6. `[M5]` ✅ Fix stale "running" status pada restart — `synthetic_pipeline.py:464`

### Sprint 2 (Sebelum Cycle 1 Training — Day 39-40)
7. `[H15]` Lengkapi 50 identity anchors di `export_dataset.py`
8. `[H16]` Tambah dataset format validation sebelum SimPO training
9. `[H17]` Fix APO label masking untuk prompt tokens
10. `[M13]` Tambah warning jika dataset lebih kecil dari target
11. `[M14]` Hapus `distill_query` dead code
12. `[H18]` Tambah `asyncio.Lock` di `start_distillation`
13. `[H19]` Track judge cost ke budget cap

### Sprint 3 (Sebelum Beta Onboarding — Day 43-49)
14. `[C1]` `[C2]` Cleanup git history sebelum repo public (BFG Repo Cleaner)
15. `[H3]` JWT refresh token ke HttpOnly cookie
16. `[H7]` Default credentials jadi None + validator
17. `[H13]` Enable RLS pada `api_keys` table
18. `[H14]` Fix migration numbering conflict (renumber atau hapus redundant)
19. `[M1]` Tambah pagination constraints
20. `[M7]` Buat helper `parse_uuid_or_422` dan gunakan di semua routers
21. `[M23]` Jangan persist conversation history ke localStorage

### Sprint 4 (Bulan 2 Week 6-7)
22. `[H4]` Sandboxed python_repl (E2B atau Docker isolation)
23. `[H5]` SSRF protection di `analyze_image`
24. `[H6]` Trusted proxies config
25. `[M25]` CDN SRI hashes
26. `[M20]` Randomize judge A/B assignment

---

## SECTION 8 — ANOMALI & KEANEHAN YANG DITEMUKAN

### Anomali 1: Dua Numbering Migration yang Sama
File `010_users_rls_security_definer.sql` dan `010_day10_schema_sync.sql` keduanya ada. Ini menunjukkan **dua agent berbeda** (Kimi dan Claude) masing-masing membuat migration di hari yang sama tanpa koordinasi. Jika Alembic digunakan di masa depan, ini akan menyebabkan masalah. Saat ini aman hanya karena migration dijalankan manual.

### Anomali 2: CONTEXT.md Belum Di-Update Setelah Day 35
CONTEXT.md masih menunjukkan "Last Updated: 2026-05-04, API Version: 0.5.0" tapi aktual sudah 0.5.2 (Day 36). Artinya **ada sesi yang tidak update CONTEXT.md setelah selesai**. Ini akan menyebabkan agent berikutnya bekerja dengan konteks stale.

### Anomali 3: Distillation Pipeline 476 Baris, 0 Pairs Produced
Pipeline distillation dibangun di Day 28 (476 baris kode) tapi belum menghasilkan satu pair pun. Root cause: Ollama CPU bottleneck pada student step. Ini bukan bug (ada fallback ke synthetic), tapi menunjukkan bahwa **pipeline yang paling kompleks adalah yang paling tidak teruji**. Perlu small batch verification sebelum production reliance.

### Anomali 4: `onamix_scrape` Tool Tidak Disebutkan di CONTEXT.md atau Tool Catalog
Tool `onamix_scrape` ditemukan di `tool_executor.py` tapi tidak ada di tool catalog di CONTEXT.md (yang mencatat 10 tools). Kemungkinan tool ini ditambahkan tapi tidak didokumentasikan. Verifikasi: apakah ini intentional atau dead code?

### Anomali 5: Letta Port 8083 vs CONTEXT.md yang Menyebut Port 8283
CONTEXT.md baris 111 menyebut "Letta container: `ado-letta-1`, port 8283 internal" tapi `docker-compose.yml` mungkin mapping ke port berbeda. Perlu verifikasi aktual via `docker ps`.

### Anomali 6: `fastembed_cache` Volume di docker-compose tapi Tidak Ada di Named Volumes Block Init
Jika volume ini dihapus (`docker compose down -v`), seluruh BM42 model cache hilang dan butuh 10 menit re-download. Tidak ada backup label atau documentation warning. Developer baru bisa tidak tahu ini.

---

## SECTION 9 — FILES TIDAK ADA (Perlu Dibuat)

| File | Dibutuhkan Oleh | Urgency |
|------|----------------|---------|
| `eval/references_baseline.json` | `run_identity_eval.py --mode eval` | HIGH — harus ada sebelum Cycle 1 |
| `config/personalities.yaml` | Sudah ada (Day 31) | ✅ OK |
| `training/README.md` | Sudah ada (Day 32) | ✅ OK |
| `docs/CHANGELOG.md` | Sudah ada | ✅ OK |
| `.env.example` | Developer onboarding | MEDIUM — perlu sebelum GitHub public |
| `docs/SECURITY.md` | GitHub best practice | MEDIUM — perlu sebelum GitHub public |
| `eval/persona_consistency_v1.jsonl` | Identity eval | ✅ Ada (Day 33) |

---

## PENUTUP

**State codebase secara keseluruhan:** Fondasi kuat untuk tahap seed/beta. Arsitektur sudah solid — multi-tenant RLS, hybrid search, streaming, tool execution, genealogy tree semua berjalan. Yang perlu perhatian serius sebelum public: **4 critical issues** (terutama git history cleanup dan python_repl bypass) dan **quota bypass via stream endpoint** yang mempengaruhi business model fairness.

**Yang TIDAK perlu dikhawatirkan:** Sebagian besar HIGH issues adalah 1-5 baris fix. Arsitektur tidak perlu diubah, hanya hardening yang perlu dilakukan.

**Rekomendasi untuk agent yang mengeksekusi fixes:**
1. Baca `docs/CONTEXT.md` dan `docs/WEEK4_DECISIONS_LOG.md` sebelum mulai
2. Update `docs/CONTEXT.md` setelah setiap sesi (API version + tanggal)
3. Setiap fix harus ada test nya di checklist Section 6
4. Jangan ubah arsitektur — hanya fix yang tercatat di report ini
5. Commit per kategori fix, bukan semua sekaligus

---

*Report ini dibuat dengan full read dari semua source files. Setiap temuan berbasis kode aktual, bukan asumsi.*
*Verifikasi ulang: jalankan setiap test di Section 6 setelah fixes applied.*
