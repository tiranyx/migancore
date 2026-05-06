# 🔒 LOCKED ITEMS — Day 55 Fixes
**Created:** 2026-05-06 by Kimi Code CLI
**Purpose:** Daftar komponen yang SUDAH FIX dan TIDAK BOLEH diubah/direfactor tanpa persetujuan explicit.
**Violation policy:** Jika agent lain mengubah locked item tanpa alasan kuat → revert + lesson learned mandatory.

---

## 1. Frontend — chat.html Link Rendering (BARU — Kimi)
**File:** `frontend/chat.html`
**Commit:** `ed5da81`
**Status:** ✅ LOCKED

**Apa yang di-fix:**
- Markdown links `[text](url)` sekarang dirender sebagai `<a>` clickable
- Bare URLs `http(s)://...` juga di-linkify
- Style: green accent (`var(--green)`), underline, `target="_blank" rel="noopener noreferrer"`
- Helper function: `linkifyContent(text)` di dalam `<script type="text/babel">`

**Kenapa LOCKED:**
- Ini adalah fix UX yang user tunggu (Wikipedia link tidak bisa diklik)
- Regex sudah di-tune untuk menangani markdown + bare URL tanpa breaking existing rendering
- Mengubah ini bisa menyebabkan link tidak jalan lagi atau XSS vulnerability

**Boleh diubah jika:**
- Ada security issue (e.g., XSS via href javascript:)
- User request style change
- Menambahkan support untuk format link lain (e.g., `<url>` angle brackets)

**TIDAK BOLEH diubah:**
- Jangan ganti dengan library markdown full (marked, remark) — terlalu heavy untuk single-file HTML
- Jangan hapus fungsi `linkifyContent` — digunakan di Msg component
- Jangan ubah regex tanpa test comprehensive

---

## 2. Backend — Wikipedia Direct Search (BARU — Claude Day 55)
**File:** `api/services/tool_executor.py`
**Commit:** `8573b03`
**Status:** ✅ LOCKED

**Apa yang di-fix:**
- `_wikipedia_direct_search()` mengakses Wikipedia REST API langsung (bypass HYPERX)
- Returns: `{title, url, snippet, content, lang, source}` dengan full article extract
- Fallback: jika REST API gagal, pakai search API snippet
- Prioritas: `id.wikipedia.org` → `en.wikipedia.org`

**Kenapa LOCKED:**
- HYPERX Wikipedia engine hanya return title+URL (no content) — brain hanya bisa kasih link list
- Direct API fix memastikan brain dapat KONTEN artikel untuk summarisasi
- Tool `onamix_search(engine=wikipedia)` sekarang return `content` field

**Boleh diubah jika:**
- Wikipedia REST API berubah (breaking change)
- Perlu tambahin caching layer
- Rate limit handling perlu diperbaiki

**TIDAK BOLEH diubah:**
- Jangan revert ke HYPERX path sebagai primary untuk Wikipedia
- Jangan hapus `content` field dari return value — brain bergantung padanya

---

## 3. Tool Registration Sync (Lesson #48 — Historical)
**Files:** `config/skills.json` + `config/agents.json`
**Status:** 🔒 PERMANENTLY LOCKED

**Rule:** Kedua file WAJIB sinkron. Drift = empty bubble (brain emits nothing).
**Jika menambah tool baru:** Update KEDUA file. Test chat immediately.

---

## 4. Architecture Decisions (LOCKED PERMANENT — Day 52 Pivot)
**Source:** `docs/VISION_DISTINCTIVENESS_2026.md`

| Decision | Locked Value | Why |
|----------|-------------|-----|
| Primary LLM | Qwen2.5-7B Q4_K_M via Ollama | ADO vision = self-hosted brain |
| Orchestration | LangGraph StateGraph | Controllable, circuit breaker |
| Training algo | SimPO (BUKAN DPO) | Noise-tolerant, no reference model |
| Identity loss | APO λ=0.1 + 50 anchor prompts | Cegah persona drift |
| CAI judge | Kimi K2.6 + Gemini Flash quorum | 30% less bias |
| Memory Tier 2 | Qdrant BM42+dense+RRF | +30-50% recall proper nouns |
| Context window | num_ctx=4096 explicit | Silent truncation prevention |
| Tool calling | stream=False hardcoded | Ollama limitation |
| REPL sandbox | subprocess + import blacklist | Real process boundary |

---

## 5. Security Fixes (Sprint 1 — commit 31acdea)
**Status:** 🔒 LOCKED — security regression = critical incident

| Fix | File | Line |
|-----|------|------|
| eval/exec/compile raise PolicyViolation | `api/services/tool_policy.py:201` | ✅ |
| Admin key secrets.compare_digest() | `api/routers/admin.py:72` | ✅ |
| Gemini API key x-goog-api-key header | `api/services/teacher_api.py:292` | ✅ |
| OllamaClient async with leak fix | `api/routers/chat.py:483` | ✅ |
| Stream quota enforcement | `api/routers/chat.py:329` | ✅ |
| Redis stale "running" auto-correct | `api/services/synthetic_pipeline.py:464` | ✅ |

---

## CHECKLIST BEFORE MODIFYING LOCKED ITEM

```
□ Apa alasan kuat untuk mengubah?
□ Apakah perubahan tested end-to-end?
□ Apakah dokumentasi di-update (changelog + lesson learned)?
□ Apakah user setuju (untuk architectural change)?
□ Apakah regression test dijalankan?
```

**If NO to any → DO NOT MODIFY. Ask first.**

---

*Last updated: 2026-05-06 by Kimi*
*Next review: setelah Cycle 1 training selesai atau beta launch*
