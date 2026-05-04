# MiganCore Beta Launch Guide
**Date:** 2026-05-04 (Day 41)
**Audience:** Fahmi (founder) + first 3-5 selected beta users from Tiranyx network
**Purpose:** Share-able onboarding kit + caveat list + invite template

---

## 🚀 TL;DR

**MiganCore SOFT BETA mulai Day 41-46.**
- Target: **3-5 friends/network Tiranyx** (NOT public yet)
- URL share: `https://app.migancore.com`
- Smithery proof: `https://smithery.ai/server/fahmiwol/migancore`
- Landing: `https://migancore.com`
- Caveat clear: latency lambat di CPU, single-user feel, beberapa fitur dalam progress

---

## ✅ APA YANG BERHASIL (showcase ini ke beta user)

### Multimodal Sensing (Day 38-40)
- 📷 **Drag-drop / paste / picker gambar** → AI describe / OCR / answer in Indonesian
- 🎤 **Mic toggle** → 90s recording → transcript inserted (ElevenLabs Scribe v2)
- ⚙ **Tool execution chips** real-time (lihat AI sedang call tool apa)
- 11 built-in tools: web_search, python_repl, memory_*, spawn_agent, http_get, generate_image (fal.ai), read/write_file (sandboxed), text_to_speech (ElevenLabs), analyze_image (Gemini Vision)

### Conversation Quality (Day 36-39)
- 💬 **Streaming responses** dengan thinking indicator + 3-state status (Connecting/Thinking/Generating)
- 🔄 **Retry button** kalau jaringan terputus
- 💾 **Memory persistent** — AI ingat percakapan 30 hari (Postgres + Qdrant hybrid search)
- 🛡️ **Friendly errors** — bukan stack trace mentah

### Onboarding (Day 37)
- ✨ **Two-question setup** (use case + bahasa) → 3 dynamic starter cards
- 🎯 **Spawn child agents** dengan custom personas (Level 5 Breeder)

### MCP Server (Day 26-40)
- 🌐 **Smithery LIVE PUBLIC** — `smithery.ai/server/fahmiwol/migancore`
- 🔌 11 tools accessible via MCP Streamable HTTP
- 🔑 X-API-Key header support (gateway-friendly)
- Setiap user bisa connect dari Claude Desktop, Cursor, Continue.dev, etc.

### Distribution
- 🌍 **3 production domains**:
  - `migancore.com` (landing dengan live stats)
  - `app.migancore.com` (chat UI)
  - `api.migancore.com/mcp/` (MCP server endpoint)

---

## ⚠️ APA YANG MASIH IN-PROGRESS (caveat WAJIB ke beta user)

### Performance
- ⏳ **Latency 30-90 detik per response normal** (CPU Qwen2.5-7B, no GPU yet)
- 👥 **Concurrent ~5 users max** sebelum response melambat
- 🔋 **Day 50+ akan ada** speculative decoding (1.8x faster) + GPU inference option

### Features Not Yet Ready
- 📄 **File upload (PDF, DOCX, MD)** — Day 43-46 ship
- 🛠 **Admin Dashboard UI** untuk API keys — Day 43 ship (sekarang masih curl-only)
- 🎨 **Sub-species recognition** (Vision masih generic, e.g. "harimau" not "Sumatran tiger") — Day 41-42 polish via vision_quality flag
- 🔊 **Audio editing tools** (FFmpeg-based cut/mix) — Day 43-49
- 🎬 **Video generation** (fal.ai Kling) — Day 43-49
- 💻 **Dev mode** (`dev.migancore.com` Claude Code-replacement) — Day 50-58
- 🛒 **Skill marketplace** — Day 50-58

### Model Status
- 🧠 Model masih **base Qwen2.5-7B-Instruct** (Cycle 1 SimPO trigger Day 41-42)
- 🎭 **Custom "MiganCore soul"** (v0.1) akan live Day 42-43 setelah Cycle 1 + identity eval pass

---

## 📨 INVITE TEMPLATE (Indonesian, untuk Fahmi DM ke friends)

```
Hai [NAMA],

Saya lagi build MiganCore — Autonomous Digital Organism (ADO), sebuah
Core Brain AI yang bisa belajar, ingat semua percakapan kita 30 hari,
dan punya kepribadian yang konsisten.

Sudah hidup di:
  app.migancore.com    (chat UI)
  smithery.ai/server/fahmiwol/migancore  (MCP marketplace listing)

Bisa kamu jajal sebagai beta tester awal? Tolong jujur kasih feedback:
  - Apa yang nyaman, apa yang aneh
  - Use case apa yang ingin kamu coba
  - Latency normal lambat (kita masih CPU, GPU upgrade Day 50+)

Yang sudah jalan:
  ✓ Chat dengan persistent memory
  ✓ Image attach (paste/drop/pick)
  ✓ Voice input (mic)
  ✓ Tool calling (web search, code exec, image gen, file write, ...)
  ✓ Bilingual ID/EN

Yang masih dalam progress:
  ✗ File upload PDF/DOCX (Week 6)
  ✗ Generate PDF/Slide (sebentar lagi, Day 41-42)
  ✗ Dev mode (Bulan 2 Week 7-8)

URL register:
  https://app.migancore.com

Setelah daftar, ikutin onboarding 2-question, lalu silakan eksperimen.

Kalau ada bug atau feedback, kirim WA aja ke saya. Atau tag di
Twitter/X kalau viral-able.

Thanks!
Fahmi
```

---

## 📋 ONBOARDING SCRIPT (untuk 1-on-1 session)

### 5-minute walkthrough script:

1. **Buka `app.migancore.com`** di browser
2. **Register** dengan email + password (cepat)
3. **Onboarding modal muncul** — jawab 2 pertanyaan:
   - "Apa yang ingin kamu lakukan dengan MiganCore?" (free text)
   - "Bahasa: ID / Mix / EN?"
4. **Modal tutup** → 3 starter cards muncul → pick salah satu (atau ketik bebas)
5. **Test chat continuity:** kirim "Halo, saya [nama], kerja di [bidang], punya kucing nama [X]" → AI acknowledge → kirim "Apa nama kucing saya?" → AI jawab benar
6. **Test image attach:** drop screenshot atau paste image → ketik "apa isi gambar" → AI describe in Indonesian (~5-10s)
7. **Test mic:** klik 🎤 → record 5 detik "halo" → klik lagi → transcript muncul di input
8. **Test spawn child agent:** klik "+ SPAWN CHILD" di sidebar → pilih template (Customer Success/Research/Code Pair) → buat
9. **Test memory:** ke chat baru, ask "siapa saya?" → AI ingat dari sesi sebelumnya

### Common questions to anticipate:
- "Kenapa lambat?" → CPU 7B inference normal, GPU upgrade Day 50+
- "Aman ga data saya?" → Postgres self-hosted di VPS Fahmi, no third-party ingest, ID 30-day rolling memory
- "Bisa pakai di Claude Desktop / Cursor?" → YA via MCP. Generate API key di app.migancore.com (saat admin UI ready Day 43, atau via Fahmi manual sebelum itu)
- "Kapan public launch?" → Day 50-58 (post-Cycle-1 + GPU inference + dev mode beta)

---

## 📊 SUCCESS METRICS BETA Day 41-49

Track via:
- LangFuse (Day 44 deploy)
- Manual Fahmi diary
- Beta user feedback forms

| Metric | Target Day 49 | Stretch |
|--------|---------------|---------|
| Beta users registered | ≥3 | 5-7 |
| Active conversations / day total | ≥10 | 30+ |
| Average response time | <60s | <30s (post-Cycle-1) |
| Tools used / week | ≥30 calls | 100+ |
| Bugs reported | <5 critical | <2 |
| User retention (D7) | ≥60% | 80% |
| Multimodal usage | ≥50% sessions use image OR mic | 80% |

---

## 🔄 ITERATION CADENCE

- **Daily:** Fahmi check feedback DMs, log to TODO
- **Day 47:** Mid-week review (3 days into beta), prioritize fixes
- **Day 49:** End-of-week retro + plan Week 7 polish
- **Day 50+:** Public-beta prep based on feedback

---

## 🎓 CRITICAL ATTRIBUTES untuk SHARE

Saat share ke beta user, tekankan:

1. **"Visi: AI yang belajar dari kita, bukan AI yang kita pakai sekali pakai"** — narasi long-term relationship
2. **"Open-source soon"** (Day 50+ GitHub public, Apache 2.0) — trust + transparency
3. **"Self-hosted brain"** — data tidak ke pihak ketiga
4. **"Modular architecture"** — bisa adopt by other AI agents (developer angle)
5. **"Indonesia-first"** — Scribe v2 WER 2.4% Indonesian (3x lebih akurat dari Whisper-v3)

---

## 🛡️ ANTI-RISK BEFORE SHARE

Sebelum kirim invite ke FIRST 5:
1. ✅ Cek `app.migancore.com` healthy (curl /health)
2. ✅ Cek register flow incognito (5 menit smoke test)
3. ✅ Cek image attach end-to-end
4. ✅ Cek mic upload (key permission already enabled by Fahmi)
5. ✅ Buat 1 test user pribadi (Fahmi own use 1 hari penuh dulu sebelum invite friends)
6. ⚠️ **Hindari:** invite >5 sekaligus (bisa overload CPU)

---

## 📅 TIMELINE BETA → PUBLIC

| Phase | Day | Audience | What's New |
|-------|-----|----------|------------|
| **Soft beta** | 41-46 | 3-5 friends Tiranyx | Current state |
| **Iterate** | 47-49 | Same + bug fixes | + file upload + admin UI |
| **Mid beta** | 50-55 | 5-10 invitees + dev community | + Cycle 1 v0.1 + speculative decoding |
| **Open beta** | 56-65 | Public invite (Twitter/X) | + dev mode + skill marketplace |
| **GA** | Bulan 3 Week 9+ | mighan.com marketplace open | + agent clone + SimPO Cycle 2/3 |

---

**KESIMPULAN: SUDAH BISA mulai SOFT BETA Day 41. Public beta tunggu Day 50-58 polish. Invite template + onboarding script di atas siap dipakai.**
