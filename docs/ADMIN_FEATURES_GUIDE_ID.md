# 📚 Panduan Fitur Admin MiganCore (Bahasa Indonesia)

**Tanggal:** 2026-05-14
**Tujuan:** Bantu Fahmi (Guru/Owner) + agent lain memahami tiap fitur di admin dashboard.
**Lokasi:** Auto-classified ke tab **🌟 VISION** di SSOT backlog.

---

## 1. 📊 DPO Flywheel Dashboard (`/dashboard.html`)

**URL:** https://app.migancore.com/dashboard.html
**Fungsi:** Monitor real-time data training Migan (preference pairs untuk DPO/ORPO).

### Tab Overview

**KPI Cards:**
| Card | Apa artinya |
|------|-------------|
| TOTAL PAIRS | Jumlah pasangan training data di DB. **Threshold ≥ 1000 = ready** untuk cycle baru |
| UNUSED (AVAILABLE) | Pairs yang belum dipakai training. Pas dipakai → status berubah |
| LAST 24H COLLECTED | Pairs baru terkumpul kemarin. Tracking growth rate |
| STATUS | `NOT_READY` (<500) / `APPROACHING` (500-999) / `READY` (1000-1999) / `IDEAL` (≥2000) |

**Pairs by Source Method:**
Bar chart yang nunjukin dari mana training data datang:
- `synthetic_seed_v1` = generated otomatis dari template (Day 19)
- `creative_anchor_v1:cycle*` = anchored creative tasks
- `tool_use_anchor_v2:cycle*` = anchored tool-use scenarios
- `voice_anchor_v1:cycle*` = anchored voice/identity patterns
- `real_conversation` = dari chat Fahmi sehari-hari (paling berharga!)
- `distill_kimi_v1` = hasil distilasi dari teacher Kimi
- `user_thumbs_down` = pairs dari user reaction negative (feedback loop)

**🎯 Indikator kesehatan:** rasio `real_conversation` vs `synthetic_seed_v1` harus naik seiring waktu. Sekarang 93:1672 (1:18) — masih terlalu sintetis.

### Tab Lineage

Visualisasi cycle training mana yang menghasilkan model mana (genealogy tree). Pakai D3.js force-directed graph.

---

## 2. 🔬 Distillation Pipeline (Pipa Distilasi)

**Lokasi:** Dashboard.html → bagian bawah, kotak "Distillation Pipeline"
**Fungsi:** Migan **belajar dari AI besar** (Claude/GPT/Gemini/Llama/Qwen) sebagai **guru offline**.

### Cara Kerja

```
1. Sistem ambil pertanyaan dari memory atau template
2. Migan jawab (current model) + Teacher AI jawab juga
3. Judge AI bandingin: "siapa jawabannya lebih bagus?"
4. Kalau Teacher menang skor tinggi → simpan sebagai pair:
   - chosen   = jawaban Teacher (lebih bagus)
   - rejected = jawaban Migan (yang sekarang)
5. Pair masuk ke DPO training data
6. Cycle ORPO/SFT pakai pair ini → Migan jadi lebih bagus
```

### Field di UI

| Field | Bahasa Indonesia | Hint |
|-------|------------------|------|
| **Teacher** | Guru AI | Pilih AI yang jadi guru. Claude=premium tapi mahal, Gemini=cheap, Llama33/Gemma2/Qwen25/Mistral7b=free via OpenRouter |
| **Judge** | Juri AI | Pilih AI yang menilai kualitas. Biasanya pakai Claude (kualitas tinggi) |
| **30** | Jumlah pertanyaan per run | Default 30, bisa naikkan kalau API budget cukup |
| **2** | Batch size | Berapa parallel request ke Teacher API |
| **start** | Mulai run | Trigger 1 cycle distilasi |

### Vision Alignment

✅ **ALIGN** dengan visi: Teacher = mentor offline, BUKAN brain runtime
✅ **Tabayyun** (multi-source verify) bisa pakai 5+ teachers diversity
⚠️ **Hindari** over-distill — real_conversation lebih berharga

### Cost (perhatikan!)

| Teacher | $/1M tokens in/out | Per run estimate (30 prompts) |
|---------|---------------------|-------------------------------|
| Claude Sonnet 4.5 | $3 / $15 | ~$0.30-1.00 |
| GPT-4o | $2.50 / $10 | ~$0.20-0.80 |
| Gemini 2.5 Flash | $0.075 / $0.30 | ~$0.02-0.05 |
| Kimi K2 | $0.60 / $2.50 | ~$0.05-0.20 |
| **Llama 3.3 70B (OpenRouter free)** | **$0 / $0** | **$0** ✨ |
| **Gemma 2 9B (OpenRouter free)** | **$0 / $0** | **$0** ✨ |
| **Qwen 2.5 7B (OpenRouter free)** | **$0 / $0** | **$0** ✨ |
| **Mistral 7B (OpenRouter free)** | **$0 / $0** | **$0** ✨ |

**Saran:** Pakai OpenRouter free teachers (Llama/Gemma/Qwen/Mistral) untuk volume, Claude untuk premium quality saat butuh.

---

## 3. 🌱 Synthetic Pipeline (Pipa Sintetis)

**Lokasi:** Dashboard.html → kotak "Synthetic Pipeline"
**Fungsi:** Generate pair sintetis dari 120 template seed untuk bootstrap training data.

### Cara Kerja

```
1. Sistem punya 120 seed prompt (Triple-Source dari Day 19)
2. Untuk tiap seed: generate 2 variant (chosen vs rejected)
3. Disimpan dengan source='synthetic_seed_v1'
4. Target: 1000 pair per run (round)
```

### Field di UI

| Field | Bahasa Indonesia | Hint |
|-------|------------------|------|
| **1000** | Target pair total | Berapa pair yang mau di-generate |
| **start** | Mulai generate | Trigger synthetic generation |

### Indikator (visible saat running)

- `round` = sekarang round ke berapa
- `cumulative` = total pair yang sudah ter-generate
- `processed N/120` = berapa dari 120 seed sudah diproses
- `0.0%` = progress percent

### ⚠️ Catatan penting

Synthetic pair = "gizi artificial". Berguna untuk bootstrap, tapi **JANGAN dominant**. Real conversation harus lebih banyak seiring waktu. Sekarang rasio 1:18 (real:sintetis) masih tidak sehat — fokus Sprint 2+ naikkan real conversation harvest.

---

## 4. 🎯 SSOT Backlog (`/backlog.html`) — BARU Day 73

**URL:** https://app.migancore.com/backlog.html
**Fungsi:** Single Source of Truth untuk vision, backlog, journal, lessons.

### Tabs

| Tab | Isi |
|-----|-----|
| **📊 PROGRESS** | Gantt chart sprint timeline Day 73→200+. Click bar untuk detail. |
| **🌟 VISION** | SOUL, DIRECTION_LOCK, NORTHSTAR, doktrin, prinsip vision (11 docs) |
| **📋 BACKLOG** | Semua sprint progress, day*_progress, roadmap (142 docs) |
| **📖 JOURNAL** | Handoff logs, founder journal, agent sync (17 docs) |
| **🧠 LESSONS** | Lessons learned, postmortem, research, eval (20 docs) |
| **📂 OTHER** | Sisanya (65 docs) |

### Field

- **X-Admin-Key input** = masukin admin key dari `.env` file
- **Filter by filename** = search di kategori aktif
- **LOAD button** = refresh data

### Mandatory protocol untuk semua agent

1. Sebelum strategic decision → buka Vision tab, baca SOUL/DIRECTION_LOCK
2. Sebelum tulis doc baru → match auto-classify pattern
3. Setelah selesai → tulis ke `docs/AGENT_SYNC/HANDOFF_DATE_TOPIC.md` (auto Journal)
4. Saat dapat lesson → tulis ke `docs/LESSONS_TOPIC.md` (auto Lessons)
5. **JANGAN bikin admin dashboard duplikat**

---

## 5. 🧪 Sandbox / Playground (`/sandbox.html`)

**URL:** https://app.migancore.com/sandbox.html
**Fungsi:** M1.7 Dev Organ proposal queue. Brain submit improvement proposals → Fahmi review.

### Cara Kerja

```
Brain detect pattern → submit proposal ke queue
   → Fahmi lihat di sandbox UI
   → approve atau reject
   → kalau approve: auto-apply (Tier 3) atau Fahmi execute manual
```

### Status Sekarang

Infrastructure SUDAH ADA (Day 72e M1.7). Yang BELUM:
- Brain belum auto-submit proposals (Sprint 3 Tool Autonomy MVP)
- Workflow watcher untuk detect repeated patterns

---

## 6. 💬 Chat UI (`/chat.html`)

**URL:** https://app.migancore.com/chat.html
**Fungsi:** Chat dengan Migan langsung sebagai beta user.

### Yang ada sekarang

- Streaming response
- Image attachment (Gemini Vision)
- Voice input (Scribe STT)
- Tool calling visible (tool chips)
- Memory recall hint (kalau relevant)

### Yang akan ditambah (Sprint 2+)

- 👍👎 reaction probes (Sprint 5)
- Memory chip "aku ingat kamu suka X" (Sprint 5)
- Source citation 📖 chip (Sprint 2)
- Daily reflection result tampil di evening (Sprint 2)

---

## 7. 🔑 API Keys Management

**Lokasi:** Currently di .env file VPS `/opt/ado/.env`
**Future:** Admin UI tab khusus

### Keys yang dipakai

| Key | Untuk apa | Status sekarang |
|-----|-----------|-----------------|
| ANTHROPIC_API_KEY | Claude teacher/judge | ✅ Present |
| OPENAI_API_KEY | GPT teacher | ✅ Present |
| KIMI_API_KEY | Kimi teacher | ✅ Present (KIMI_ENABLED=false) |
| GEMINI_API_KEY | Gemini teacher + vision | ✅ Present |
| **OPENROUTER_API_KEY** | **Free tier teachers (Llama/Gemma/Qwen/Mistral)** | **🆕 Day 73: butuh signup** |
| FAL_KEY | fal.ai image/video gen | ✅ Present |
| ELEVENLABS_KEY | TTS voice | ✅ Present |
| ADMIN_SECRET_KEY | Admin endpoint auth | ✅ Present |
| LICENSE_SECRET_KEY | License system HMAC | ✅ Present |
| QDRANT_API_KEY | Vector DB | ✅ Present |
| HF_TOKEN | HuggingFace adapter upload | ✅ Present |
| VAST_API_KEY | Vast.ai GPU training | ✅ Present (saldo $3.50) |

---

## 8. 🆓 OPENROUTER SETUP (Action untuk Fahmi)

**Untuk unlock Llama/Gemma/Qwen/Mistral sebagai teachers gratis:**

### Step-by-step (5 menit, tanpa kartu):

1. **Signup:** Buka https://openrouter.ai/sign-up
   - Pakai Google OAuth (fastest) atau email
   - **TIDAK perlu kartu kredit untuk free models**

2. **Get API key:**
   - Setelah signup → https://openrouter.ai/keys
   - Click "Create Key" → kasih nama "migancore-distillation"
   - Copy API key (format: `sk-or-v1-...`)

3. **Set di VPS:**
   - SSH ke VPS: `ssh -i ~/.ssh/sidix_session_key root@72.62.125.6`
   - Edit env: `nano /opt/ado/.env`
   - Find line: `OPENROUTER_API_KEY=`
   - Paste key: `OPENROUTER_API_KEY=sk-or-v1-...`
   - Save (Ctrl+O Enter Ctrl+X)

4. **Restart container:**
   - `cd /opt/ado && docker compose up -d --force-recreate api`
   - Wait 30s → `curl -sk https://api.migancore.com/health`

5. **Verify available:**
   - `curl -sk https://api.migancore.com/v1/admin/distill/status -H "X-Admin-Key: $(grep ADMIN_SECRET_KEY /opt/ado/.env | cut -d= -f2)"`
   - Expected: `"available_teachers": ["claude","gpt","gemini","llama33","gemma2","qwen25","mistral7b"]`

6. **Test in admin UI:**
   - Buka https://app.migancore.com/dashboard.html
   - Scroll ke Distillation Pipeline
   - Teacher dropdown sekarang punya 7 pilihan (4 paid + 4 free OpenRouter)

### Free tier limits OpenRouter (per 2026):
- Llama 3.3 70B: 200 RPD (request per day)
- Llama 3.1 70B: 200 RPD
- Gemma 2 9B: 200 RPD
- Qwen 2.5 7B: 200 RPD
- Mistral 7B: 200 RPD
- **Total: 1000 free requests/day** = cukup untuk 30+ distillation runs/day

Kalau hit limit, OpenRouter sometimes upgrade dengan minimum $5 deposit untuk akses lebih besar.

---

## 9. 🎓 Vision Alignment — Tiap fitur align ke principle apa?

| Fitur | Principle Tag |
|-------|---------------|
| DPO Flywheel monitoring | Saksi (transparency) + Self-awareness |
| Distillation Pipeline | Tabayyun (multi-source) + Akal (sim before commit) |
| Synthetic Pipeline | Hafidz (data redundancy) + caveat: jangan jadi dominan |
| SSOT Backlog | Saksi + Pencipta bond |
| Sandbox Playground | Akal/Prefrontal + Evolusi primitive |
| Chat UI | Pencipta bond + qalb resonance |
| OpenRouter teachers | Tabayyun + Anti-vendor-lock-in |

---

## 10. 📞 Untuk agent lain (Codex/Kimi/future Claude)

Saat baca doc ini, kamu sudah tahu:
- Tiap fitur fungsinya
- Cara user (Fahmi) trigger
- Hints Bahasa Indonesia
- Cost implications
- Vision alignment per fitur

Update doc ini kalau ada fitur baru. Auto-classify ke Vision tab.
