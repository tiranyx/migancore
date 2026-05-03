# DAY 14 — Knowledge Block Auto-Extraction Research & Architecture
**Date:** 2026-05-03  
**Author:** Claude Sonnet 4.6  
**Status:** Research Complete → Implementation Ready

---

## 1. Problem Statement

Setelah Day 13, setiap MiganCore agent punya 3 Letta memory blocks:
- `persona` — identitas stabil (terisi dari soul_text + overrides)
- `mission` — misi aktif (default, bisa diupdate manual)
- `knowledge` — **"Belum ada pengetahuan spesifik yang tersimpan tentang konteks ini."**

Block `knowledge` adalah **placeholder** — ia tidak pernah bertumbuh secara otomatis. Ini gap kritis: visi ADO adalah organisme digital yang belajar dan berkembang, tapi knowledge block-nya statis.

**Target Day 14:** Setiap conversation turn secara otomatis mengekstrak fakta baru tentang pengguna dan mengappend ke knowledge block. Agent mulai "mengenal" penggunanya.

---

## 2. Dimensi Analisis

### 2.1 Apa yang Worth Extracting?

Bukan semua percakapan mengandung fakta yang layak disimpan. Yang layak:

| Kategori | Contoh |
|----------|--------|
| Identitas pengguna | nama, profesi, asal |
| Proyek & konteks kerja | "sedang bangun platform AI", "sprint 30 hari" |
| Preferensi | "lebih suka jawaban singkat", "pakai Bahasa Indonesia" |
| Tujuan & visi | "ingin deploy sebelum bulan depan", "target 1000 user" |
| Stack & tools | "pakai FastAPI", "deploy di VPS Ubuntu 22.04" |
| Fakta relasional | "tim-nya terdiri dari AI agents", "sudah 13 hari sprint" |

Yang TIDAK perlu disimpan:
- Pertanyaan umum ("apa itu JWT?")
- Jawaban faktual tanpa konteks personal
- Percakapan basa-basi

### 2.2 Pilihan Model untuk Ekstraksi

| Model | RAM Usage | Speed | Accuracy (simple NLP) | Keputusan |
|-------|-----------|-------|----------------------|-----------|
| Qwen2.5-7B-Instruct-Q4_K_M | ~6GB (sudah di VRAM) | 7-14 tok/s | ⭐⭐⭐⭐ | Digunakan untuk chat |
| Qwen2.5-0.5B | ~400MB extra | Sangat cepat | ⭐⭐⭐ | **DIPILIH untuk ekstraksi** |

**Rationale memilih 0.5B:**
1. Tugas ekstraksi adalah structured output task yang sangat terbatas — bukan reasoning
2. Prompt sangat deterministic: "ekstrak fakta, format bullet point"
3. Fire-and-forget background task → latency tidak kritis
4. Menghindari resource contention dengan 7B yang melayani chat concurrent
5. 0.5B sudah ada di Ollama (pulled Day 3)

**Fallback:** Jika 0.5B tidak menghasilkan output valid, function returns None → block tidak diupdate. Graceful degradation.

### 2.3 Format Knowledge Block

**Masalah dengan format flat:**
```
Pengguna bernama Fahmi. Dia adalah founder. Proyek MiganCore adalah ADO...
```
→ Susah di-update, susah di-trim, rentan duplikasi.

**Format date-sectioned (DIPILIH):**
```
[2026-05-03]
- Pengguna adalah Fahmi, founder dan visioner MiganCore
- Proyek: ADO (Autonomous Digital Organism), sprint 30 hari
- Stack: FastAPI, Python, PostgreSQL, Redis, Qdrant, Ollama

[2026-05-03]
- Target deployment: api.migancore.com (sudah live, Let's Encrypt)
- Tim: multi-agent AI (Claude Sonnet, Kimi, GPT)
- Visi: "setiap visi berhak punya organisme digital"
```

**Keunggulan format ini:**
1. Human-readable dan LLM-readable
2. FIFO trimming alami — drop section terlama saat mendekati limit
3. Date context → agent tahu kapan fakta diketahui
4. Modular — update satu section tanpa ganggu yang lain

### 2.4 Strategi Deduplication

**Opsi 1: Full knowledge comparison (kompleks)**
- Embed semua fakta, bandingkan cosine similarity baru vs lama
- Terlalu mahal untuk background task

**Opsi 2: LLM-based deduplication (DIPILIH)**
- Tampilkan 500 chars terakhir knowledge ke extraction LLM
- Instruksikan: "jangan duplikasi fakta yang sudah ada"
- 500 chars = ~5-10 fakta terbaru → cukup untuk dedup yang relevan
- Fakta lama boleh sedikit terduplikasi — acceptable tradeoff

**Opsi 3: Exact string matching (terlalu rigid)**
- Gagal untuk parafrase ("Fahmi adalah founder" vs "founder MiganCore: Fahmi")

→ LLM-based dedup lebih natural dan cukup akurat untuk use case ini.

### 2.5 Knowledge Block Growth & Trimming

```
Initial: "Belum ada pengetahuan spesifik..."  (placeholder)
After turn 1: [2026-05-03]\n- fact1\n- fact2\n- fact3
After turn 5: [2026-05-03]\n- fact1\n... + [2026-05-03]\n- fact4\n- fact5
...
Approaching 4000 chars: TRIM — drop oldest section, append newest
```

**Trim threshold:** 3600 chars (leaves 400 char buffer for new section)

**Trim strategy:** `re.split(r'\n\n(?=\[)', combined)` → list of sections → pop first → rejoin.

### 2.6 Integrasi dengan Qdrant Tier 2

Knowledge block (Letta Tier 3) dan Qdrant semantic memory (Tier 2) bukan duplikasi — mereka komplementer:

| Dimensi | Qdrant Tier 2 | Letta Tier 3 Knowledge |
|---------|---------------|----------------------|
| Granularity | Full conversation turns | Extracted facts only |
| Query pattern | Semantic similarity search | Injected ke system prompt setiap chat |
| Persistence | Per-agent Qdrant collection | Cross-session Letta block |
| Kegunaan | "cari percakapan yg mirip ini" | "siapa pengguna ini?" |
| Update freq | Setiap turn (all) | Hanya turn yg ada fakta baru |

→ Qdrant untuk episodic memory, Letta knowledge untuk semantic profile pengguna.

---

## 3. Constraint & Risk Analysis

### C1: Model Quality Risk (MEDIUM)
Qwen2.5-0.5B mungkin menghasilkan output tidak valid atau tidak mengikuti format.

**Mitigasi:**
- Validasi: only keep lines starting with "- "
- "TIDAK ADA" detection (case-insensitive)
- Minimal length check (< 5 chars → skip)
- All errors → silent skip (never update block)

### C2: Resource Contention Risk (LOW)
0.5B dan 7B berjalan di CPU yang sama (no GPU).

**Mitigasi:**
- Fire-and-forget: extraction berjalan SETELAH HTTP response sudah dikirim
- asyncio.create_task → extraction dijadwalkan di event loop, tidak blocking
- Ollama menqueue concurrent requests — tidak ada crash risk
- Worst case: extraction sedikit lebih lambat karena 7B juga digunakan

### C3: Letta Block Corruption Risk (LOW)
Jika update_block gagal, block lama tetap intact (PATCH atomic).

**Mitigasi:**
- `update_block()` sudah handle semua errors dengan silent fail
- Worst case: knowledge tidak terupdate turn ini → retry next turn

### C4: Infinite Growth Risk (RESOLVED)
Knowledge block bisa bertumbuh melewati 4000 char limit.

**Mitigasi:**
- Trim threshold: 3600 chars → trigger FIFO section removal
- Hard cap di `update_block()`: `value[:KNOWLEDGE_LIMIT]`
- Double safety: trim BEFORE update, cap AT update

### C5: Extraction Loop Risk (NONE)
Ini pure fire-and-forget — tidak ada feedback loop ke chat response.

---

## 4. Architecture Decision Record

**Keputusan: Implementasi Knowledge Auto-Extraction di Day 14**

| Aspek | Pilihan | Alasan |
|-------|---------|--------|
| Extraction model | Qwen2.5-0.5B | Fast, low RAM, sufficient for structured extraction |
| Trigger | After every chat turn (sync endpoint only) | Stream endpoint persists async, harder to inject there |
| Block format | Date-sectioned bullet points | Human-readable, FIFO-trimmable, LLM-parseable |
| Dedup strategy | LLM-based with recent knowledge tail | Natural language dedup, low cost |
| Update strategy | Append new section | Never overwrites, preserves history |
| Error handling | Silent fail, never raises | Consistent with entire Letta layer pattern |
| Scope | Sync chat only (stream: future) | 80% of chat volume, safer to scope Day 14 |

---

## 5. Files Affected

### New File
- `api/services/fact_extractor.py`
  - `extract_facts(user_message, assistant_response, existing_knowledge) -> str | None`
  - `maybe_update_knowledge_block(letta_agent_id, user_message, assistant_response, letta_blocks) -> None`
  - `_trim_knowledge_if_needed(current, new_section) -> str`
  - Uses: `OllamaClient` (0.5B), `letta.update_block`

### Modified Files
- `api/routers/chat.py`
  - Import: `from services.fact_extractor import maybe_update_knowledge_block`
  - In `chat()`: after `index_turn_pair` create_task, add knowledge extraction create_task
- `api/main.py`
  - Version: `0.3.2` → `0.3.4`

---

## 6. Tidak Diimplementasikan (Scope Out)

- **Stream endpoint knowledge extraction** — `chat_stream` persists assistant message via background task; adding another nested background task is complex. Defer Day 15+.
- **Mission block auto-update** — mission should be explicit (user sets it). Not auto-derived from conversation. Keep manual.
- **Persona evolution** — persona block explicitly kept stable per architecture decision Day 13.
- **Cross-agent knowledge sharing** — out of scope for Week 2.

---

## 7. Verifikasi E2E Plan

```bash
# 1. Register + login + create agent
TOKEN=$(curl -s -X POST https://api.migancore.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"...","password":"..."}' | jq -r '.access_token')

# 2. Create agent
AGENT_ID=$(curl -s -X POST ... | jq -r '.id')

# 3. Chat — send message with extractable facts
curl -X POST https://api.migancore.com/v1/agents/$AGENT_ID/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Saya Fahmi, saya sedang membangun platform AI bernama ADO. Proyek ini sprint 30 hari dan sudah hari ke-14."}'

# 4. Wait 5s for background extraction to complete
sleep 5

# 5. Check Letta knowledge block via API (or logs)
# Expected: block contains facts about Fahmi, ADO, sprint 30 hari
```

**Success criteria:**
- `fact_extractor.knowledge_updated` log visible ✅
- Knowledge block no longer contains KNOWLEDGE_DEFAULT placeholder ✅
- Facts are relevant to what user said ✅
- HTTP response was NOT delayed (latency same as before) ✅
