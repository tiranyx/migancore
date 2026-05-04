# MiganCore Strategic Roadmap — Bulan 2 Week 6 → Bulan 3
**Date:** 2026-05-04 (Day 40 close)
**Drafted by:** Claude Sonnet 4.6 — full mandatory protocol
**Triggered by:** User: "gas semua sprint" + 6 fitur tambahan + cognitive trends 2026-2027
**Research:** parallel agent `a295fe04` (6 features + cognitive trends synthesis)

---

## 🧭 1. RE-ANCHOR ADO VISION (alignment check setiap fitur)

> **MiganCore = Otak Inti AI yang modular**, bisa diadopsi/diturunkan oleh AI lain seperti **prosesor + otak manusia + sistem syaraf MCP**.

**3-prong filter setiap fitur baru:**
1. **MCP-first** — tool/skill harus jadi MCP server module (mount/unmount runtime)
2. **Skill-portable** — adopt Anthropic SKILL.md format (Oct 2025) = bisa di-load AI lain
3. **Memory-aware** — interact dengan episodic Qdrant; tidak buat tabel ad-hoc

Jika fitur tidak penuhi 3 syarat → **DEFER atau redesign**.

---

## 📅 2. DAY-BY-DAY ROADMAP (Day 41 → Day 65)

### Bulan 2 Week 6 — "Beta-Polish + Quick-Win Tools"

| Day | Track A (Training) | Track B (Tools/UI) | Track C (Polish) |
|-----|--------------------|--------------------|------------------|
| **41** | DPO ≥500 → trigger SimPO Cycle 1 ($2.80) | **Output PDF (WeasyPrint) + Slides (Marp) + Web Read (Jina)** ⭐ ship today | nginx HTML no-cache (done Day 40) |
| **42** | SimPO complete + GGUF Q4 convert | A4 status hierarchy (seeing/hearing) | Smithery quality polish (homepage, README, badge) |
| **43** | Identity eval v0.1 ≥0.85 → PROMOTE/ROLLBACK | **Input artifacts (Docling/MarkItDown)** parse_artifact tool | Admin Dashboard fix (proper /admin + API Keys UI) |
| **44** | Hot-swap v0.1 ke Ollama, A/B 10% traffic | Audio edit (FFmpeg MCP wrapper: cut/mix/effect) | LangFuse self-hosted (Postgres-only) |
| **45** | 24h A/B win-rate metrics | Image→Video tool (`generate_video` via fal.ai Kling) | Beta invite flow + invite codes |
| **46** | PROMOTE or ROLLBACK decision | Episodic image memory (image hash + caption to Qdrant) | Conversation export MD/JSON |
| **47-49** | (autonomous monitoring) | **5 BETA USER ONBOARDING** + 1-on-1 sessions | Bug iteration berdasarkan feedback |

### Bulan 2 Week 7 — "Cognitive Upgrade + SKILL.md Foundation"

| Day | Track A | Track B | Track C |
|-----|---------|---------|---------|
| **50-52** | Budget-controlled CoT (R1-style reasoning) | **SKILL.md format adoption** (loader + UI) | Speculative decoding llama.cpp benchmark |
| **53-55** | Magpie 300K full + DPO 1000+ pairs | Skill marketplace UI (`/skills` panel di chat) | Dev mode pre-architecture (E2B research) |
| **56-58** | Letta sleep-time memory consolidator | **Dev Mode E2B prototype** (`dev.migancore.com`) | Firecrawl self-host (full crawl + JS render) |

### Bulan 2 Week 8 — "Open Source + Dev Beta"

| Day | Track A | Track B | Track C |
|-----|---------|---------|---------|
| **59-61** | SimPO Cycle 2 + APO with anchor 100 | **Dev mode beta** (3 dev users invited) | GitHub repo public (Apache 2.0) |
| **62-65** | Qwen3-MoE-A3B benchmark + migration test | Web builder lite (Bolt-pattern) | Bulan 3 plan + tweet thread launch |

### Bulan 3 (Day 66-95) — "Modular Mount + Marketplace"

| Phase | Focus |
|-------|-------|
| **Week 9** | mighan.com cloning marketplace foundation (agent clone, sell-skill) |
| **Week 10** | Penpot embed (design canvas inline) |
| **Week 11** | A-LoRA per-user personalization (research → prototype) |
| **Week 12** | sidixlab.com research dashboard (separate consumer platform) |

---

## 🎯 3. 6 USER-REQUESTED FEATURES — STRATEGIC MAP

### Feature 1 — Input Artifacts (PDF/DOCX/MD/HTML/script)
- **When:** Day 43-46 (Week 6)
- **How:** **Docling** (best accuracy) + **MarkItDown** (best DX) — local CPU, $0 cost
- **MCP tool:** `parse_artifact(file_url|file_base64) → markdown`
- **Risk:** layout extraction can fail on complex PDFs → fallback to PyMuPDF + LLM cleanup
- **Effort:** 2 hari

### Feature 2 — Output Formats (MD/PDF/Slide/Script/Image)
- **When:** Day 41-42 ⭐ SHIP TODAY (PDF + Slide), Day 43+ for executable
- **How:**
  - PDF: **WeasyPrint** (50MB pure-Python, no Chromium) → `export_pdf` MCP tool
  - Slides: **Marp CLI** (md→PDF/PPTX/HTML, LLM-friendly syntax) → `export_slides` MCP tool
  - Executable: write_file (already exists) + UI Download button
  - Image: generate_image (already exists)
- **Effort:** 1 hari per format
- **Cost:** $0

### Feature 3 — Dev Mode (`dev.migancore.com` — Claude Code replacement)
- **When:** Day 50-58 (Week 7-8)
- **How:** **E2B Firecracker microVM** ($0.05/hr idle) — managed sandbox, no DiD pain
- **Pattern:** OpenHands ReAct loop + nginx canary gateway (5%→25%→100%)
- **Risk:** prompt injection ke kode, runaway compute → mitigasi: network egress whitelist, AST scan, max-runtime cap
- **Cost:** ~$30-80/bln untuk beta (10 user × 30 min/hari)
- **Effort:** 6-8 hari
- **Architecture:**
  ```
  user@dev.migancore.com → MiganCore Brain (Qwen) → E2B sandbox
                                                  → write code → AST scan
                                                  → execute in microVM
                                                  → stream stdout/stderr
                                                  → user accepts → git commit + canary deploy
  ```

### Feature 4 — Built-in Tools on Chat (design/sound/video/web builder)
- **When:**
  - **Day 43-49:** `generate_video` (fal.ai Kling), `audio_edit` (FFmpeg MCP)
  - **Day 50-65:** Penpot embed (design canvas), web builder lite
  - **Bulan 3+:** full design integration
- **How:** Setiap tool = MCP server module (modular brain principle)
- **Cost:** Variable. Video gen $0.28/clip. Penpot self-host $0.

### Feature 5 — Plugin/Skill/Connector Marketplace
- **When:** Day 50-58 (Week 7)
- **How:** **Adopt Anthropic SKILL.md format** (Oct 2025 spec). Folder dengan `SKILL.md` (frontmatter: name, description, allowed_tools) + scripts.
- **Internal vs external:** in-process Python untuk hot-path; external MCP via Smithery (sudah ada) untuk pihak ketiga
- **Marketplace UI:** `/skills` panel di chat + Smithery directory link
- **Effort:** 4 hari (SKILL.md loader + UI)

### Feature 6 — Web Fetch/Scrape (audit + improvement)
- **AUDIT result (existing):**
  - ✅ `web_search` (DDG Instant Answers — basic)
  - ✅ `http_get` (raw GET, no JS render)
  - ❌ NO scraper with JS rendering
  - ❌ NO structured extraction (CSS selectors)
  - ❌ NO PDF/document fetch
- **When:** Day 41-42 ⭐ SHIP TODAY (Jina Reader), Day 56-60 full Firecrawl
- **How:**
  - **Jina Reader** (free 1M token/bln) → `web_read(url) → clean markdown` ⭐ Day 41
  - **Tavily** upgrade web_search (better than DDG) → Day 42
  - **Firecrawl self-host** ($9/bln) → full crawl + structured extract → Day 56-60
  - **Playwright MCP** (Microsoft Mar 2026) → interactive browsing → Day 60+
- **Effort:** 30 min Jina, 1 hari Tavily, 3 hari Firecrawl
- **Cost:** $0-19/bln

---

## 🧠 4. COGNITIVE TRENDS 2026-2027 — ADOPTION PLAN

### Must-adopt (30-60 days)
| Trend | When | Source |
|-------|------|--------|
| **Test-time compute / budget CoT** (R1, QwQ) | Day 50-55 | qwenlm.github.io/blog/qwq-32b/ |
| **Edge MoE Qwen3-MoE-A3B** (3B active/30B total, faster than 7B dense on CPU) | Day 60-65 benchmark | huggingface.co/Qwen/Qwen3-MoE-A3B |
| **Letta sleep-time memory consolidator** | Day 56-60 | github.com/letta-ai/letta |
| **Speculative decoding** llama.cpp stable | Day 50-52 | 1.8x CPU speedup |

### Defer (watch-only)
- A-LoRA per-user (not production-ready)
- Federated learning Flower (relevant kalau on-device)
- Constitutional AI v3 (kita sudah punya CAI v0.3.5)
- DeepSeek-V4 (Q3 2026 rumored)

### Differentiation (visi unik MiganCore vs competitor)
- **Letta** — paling dekat (persistent agent OS), TAPI single-agent
- **AIOS LLM Agent OS** (Rutgers) — OS layer, TAPI bukan modular brain
- **MiganCore** = **modular brain yang bisa di-mount AI lain** — posisi unik di market

---

## ⚠️ 5. RISK FORECAST (3 risk timing)

1. **Dev Mode terlalu cepat (sebelum Day 50):** prompt injection / runaway compute → reputation damage. **Mitigasi: tunggu E2B sandbox + SKILL.md foundation.**
2. **Skill marketplace tanpa standar:** lock-in ke format internal yang besok harus migrasi. **Mitigasi: adopt SKILL.md sejak hari pertama.**
3. **Multi-tool bloat tanpa MCP modularity:** chat UI jadi monolith — bertentangan dengan visi ADO. **Mitigasi: setiap tool baru WAJIB MCP server module sebelum merge.**

---

## 💰 6. BUDGET PROJECTION Bulan 2 Week 6 → Bulan 3

| Item | Estimate |
|------|----------|
| SimPO Cycle 1 (Day 41) | $2.80 |
| SimPO Cycle 2 (Day 59-61) | $3.00 |
| RunPod GPU inference test (Day 55+) | $5.00 |
| Anthropic Claude (judge + Vision fallback) | $3.00 |
| Kimi K2.6 (judge + bilingual) | $2.00 |
| OpenAI GPT-4o (occasional) | $1.00 |
| Gemini Flash (vision + onboarding starters) | $0.50 |
| Jina Reader / Tavily | $0-19/bln |
| Firecrawl self-host (Day 56+) | $9/bln |
| **E2B sandbox** (Day 50+, beta scale) | $30-80/bln |
| ElevenLabs TTS+STT | $5/bln |
| fal.ai (image + video gen) | $5-15/bln |
| **Total Bulan 2 Week 6-8** | **~$70-120** |

Per Bulan 2 budget cap $50 RunPod + $20/bln VPS + miscellaneous = **dalam batas $30 cap untuk API spend kita** kalau hindari E2B sebelum Bulan 3.

---

## 📊 7. PROGRESS LEDGER (Day-by-day, Day 36-40 yang SUDAH)

### What's DONE
- **Day 36:** Chat UX hardening (nginx SSE 600s, retry, friendly errors, cancel propagation) v0.5.2
- **Day 37:** Teacher API activation — CAI Kimi+Gemini quorum + Two-Question Onboarding pivot v0.5.3
- **Day 38:** Multimodal endpoints — `analyze_image` (Gemini Vision) + `/v1/speech/to-text` (Scribe v2) + Magpie 300K loader + APO loss pre-wire v0.5.4
- **Day 39:** Stream tool exec FIX (hybrid pattern) + chat continuity FIX + SimPO Q2-2026 hyperparams + identity baseline + Smithery config v0.5.6
- **Day 40 (BIG):** SSE tool chips + image attach (paste/drop/picker) + mic toggle + Vision describe endpoint + Smithery LIVE PUBLIC + user bubble fix + stream double-call fix v0.5.8

### Cumulative metrics end Day 40
- 11 commits across the day
- 30 lessons learned cumulative
- DPO pool: 277 → 371 (+94 across 5 days)
- Bulan 2 spend: $1.09 of $30 cap (3.6%)
- 3 domains live + Smithery directory
- 11 tools, 3 multimodal endpoints
- 88.5KB chat.html

### What's NEXT (Day 41 lock-in)
**TRACK A (autonomous):** Cycle 1 trigger when DPO ≥500
**TRACK B (today):** PDF export + Slides + Web Read (Jina) — 3 quick-ship MCP tools
**TRACK C (after Cycle 1):** A4 status hierarchy + admin fix + Smithery polish

---

## 🚀 8. BETA LAUNCH READINESS ASSESSMENT

### YES (sudah ready untuk SELECTIVE small beta):
- ✅ Chat continuity stable (Day 38 fix)
- ✅ Multimodal: image attach + mic + tool chips visible
- ✅ Onboarding 2-question + dynamic starter cards
- ✅ Tool execution transparent (chips render real-time)
- ✅ Friendly errors + retry button
- ✅ Smithery LIVE PUBLIC = public proof
- ✅ All 3 domains stable

### CAVEATS (kasih warning ke beta user):
- ⚠️ **Latency 30-90s normal** (CPU 7B inference, no GPU yet — Day 50+)
- ⚠️ **Single-user feel** (~5 concurrent max sebelum slow)
- ⚠️ **Model masih base Qwen2.5-7B** (Cycle 1 SimPO trigger Day 41) — soul belum custom
- ⚠️ **No file upload yet** (Day 43-46 ship)
- ⚠️ **Vision generic** (sub-species accuracy issue — Day 41-42 polish)
- ⚠️ **No admin UI for API keys** (Day 43 fix)

### REKOMENDASI:
**SOFT BETA Day 41-49 — undang 3-5 friends/network Tiranyx** dengan caveat clear: "ini early version, latency normal lambat di CPU, multimodal works, beberapa fitur masih in-progress."

**PUBLIC BETA tunggu Day 50-58** ketika:
- Cycle 1 v0.1 hot-swapped (model has custom soul)
- File input live (Day 43-46)
- Speculative decoding live (Day 50-52, +1.8x speed)
- LangFuse observability live (track win-rate)

---

## 🎓 9. LESSONS APPLIED (cumulative 30 → 31)

31. **Strategic timing > feature ambition.** User minta 6 fitur sekaligus = recipe for buggy half-shipped releases. Map ke timeline based on:
    - Foundation dependencies (SKILL.md sebelum marketplace, sandbox sebelum dev mode)
    - Quick wins (PDF/Slides/Jina = 1-day each)
    - Risk profile (dev mode = HIGH risk → defer until foundation ready)
    - Cost curve (E2B variable, defer until beta has paying users)

---

**THIS IS THE ROADMAP. Refer back when in doubt about timing.**
