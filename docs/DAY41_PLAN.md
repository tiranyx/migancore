# Day 41 Plan — Output Tools (PDF/Slides) + Web Read + Beta Pre-flight
**Date:** 2026-05-04 evening (Day 41)
**Drafted by:** Claude Sonnet 4.6 — full mandatory protocol
**Triggered by:** User: "gas semua sprint" + 6 fitur tambahan + beta launch question
**Research:** parallel agent `a295fe04` (6 features synthesis)
**Companion:** `ROADMAP_BULAN2_BULAN3.md` (day-by-day Day 41-95)

---

## 🧭 1. CONTEXT

| Item | State Day 41 morning |
|------|----------------------|
| API | v0.5.8 healthy |
| DPO pool | 371 (need 129 more for SimPO trigger) |
| ETA Cycle 1 trigger | Day 41 evening atau Day 42 morning |
| Bulan 2 spend | $1.09 of $30 (3.6%) |
| RunPod saldo | $16.17 (Cycle 1 = $2.80) |
| Smithery | LIVE PUBLIC |
| Cumulative lessons | 30 (target 31+ today) |

---

## 🔬 2. RESEARCH SYNTHESIS — 3 SHIP-TODAY ITEMS

Dari research agent (`a295fe04`), 3 quick-wins yang **bisa ship hari ini**:

| Item | Library | Cost | Effort |
|------|---------|------|--------|
| **MD → PDF** | WeasyPrint v62 (pure-Python, 50MB) | $0 | 1-2 jam |
| **MD → Slides** | Marp CLI v4.x | $0 | 1-2 jam |
| **Web Read** | Jina Reader (free 1M token/bln) | $0 | 30 menit |

**Total estimate:** ~4 jam, **$0 cost.**

---

## 📐 3. TASK LIST — H/R/B FRAMEWORK

### A1 — `web_read` tool via Jina Reader (HIGHEST ROI, fastest)

**Hipotesis:** User minta "ringkas artikel ini: <url>" → AI call `web_read(url)` → dapat clean markdown → ringkas → response. Latency ~2-3s (Jina cached).

**Adaptasi gagal:** Fall back ke `http_get` raw HTML (already exists). Brain proses HTML — slower, less clean.

**Impact:** Closes BIG gap. `http_get` raw HTML often kotor (scripts, ads). Jina returns clean MD.

**Benefit:** Reading capability immediate (research, news, docs). Differentiator vs LLM yang tidak bisa baca URL.

**Risk:**
- LOW — Jina free tier ample (1M token/bln)
- LOW — fallback ke http_get tetap available

**Effort:** ~30 menit (single MCP tool wrapper)

### A2 — `export_pdf` tool via WeasyPrint

**Hipotesis:** User type "buatkan PDF dari ringkasan ini" → AI generate markdown → call `export_pdf(markdown)` → return URL/base64 PDF → user download.

**Adaptasi gagal:** Markdown only (no PDF). User copy-paste manual.

**Impact:** Output format expansion. User bisa generate document siap pakai.

**Benefit:** Differentiator. Many AI assistants can't generate PDFs.

**Risk:**
- LOW — WeasyPrint mature, pure Python
- MEDIUM — file storage: temp file vs base64 inline (>1MB freezes UI)

**Effort:** ~1-2 jam (WeasyPrint install + tool handler + return URL/base64)

### A3 — `export_slides` tool via Marp CLI

**Hipotesis:** User type "buat slide presentasi tentang X" → AI generate markdown dengan `---` separator (Marp syntax) → call `export_slides(markdown, format=pptx)` → file download.

**Adaptasi gagal:** Markdown only. User pakai Marp di luar.

**Impact:** Slide generation = killer use case bagi PMs/students/marketing.

**Benefit:** Differentiator + viral share factor.

**Risk:**
- LOW — Marp CLI npm package mature
- MEDIUM — Node.js dependency in Python container (need install)

**Effort:** ~1-2 jam (Marp install + Python subprocess wrapper)

### A4 — DEFER ke Day 42-43
- A4 Status hierarchy seeing/hearing
- Admin Dashboard fix
- Smithery quality polish

### Track A — Autonomous
- Cycle 1 trigger when DPO ≥500 (currently 371, ETA evening)
- Magpie 300K full overnight (ENV var change)

---

## 📊 4. KPI PER ITEM (Day 41)

| Item | Target | Verifikasi |
|------|--------|------------|
| A1 web_read | URL → clean markdown returned | curl test 3 sites |
| A2 export_pdf | markdown → PDF binary returned | E2E test "buatkan PDF dari resep" |
| A3 export_slides | markdown → PPTX/PDF returned | E2E test "buat 5-slide deck tentang AI" |
| **v0.5.9 deployed** | health 200 + 3 new tools registered | curl /openapi.json |
| **DPO** | ≥450 (within 50 of trigger) | /v1/public/stats |

### Gate
- IF DPO ≥500 by EOD → trigger Cycle 1 morning Day 42
- IF Cycle 1 fails identity gate → ROLLBACK + document failure

---

## 💰 5. BUDGET PROJECTION Day 41

| Item | Estimate |
|------|----------|
| Code-only changes | $0 |
| WeasyPrint + Marp install | $0 (system deps) |
| Jina API test calls | $0 (free tier) |
| Synthetic continued | $0.20 |
| Buffer | $0.10 |
| **Day 41 total** | **~$0.30** |

If Cycle 1 triggers EOD: +$2.80 RunPod → **$3.10 cumulative**.

Bulan 2 cumulative: $1.09 + $0.30 = **$1.39 of $30 (4.6%)**.

---

## 🚦 6. EXIT CRITERIA — Day 41

Must-have:
- [ ] `web_read` tool live + tested via curl (3 sites)
- [ ] `export_pdf` tool live + E2E test pass
- [ ] `export_slides` tool live + E2E test pass
- [ ] v0.5.9 deployed + healthcheck
- [ ] All 3 new tools registered in TOOL_REGISTRY + skills.json
- [ ] `docs/DAY41_PROGRESS.md` + memory committed

Stretch:
- [ ] DPO ≥500 → Cycle 1 trigger
- [ ] BETA_LAUNCH_GUIDE.md untuk Fahmi share

---

## 🛡️ 7. SCOPE BOUNDARIES

❌ **DON'T BUILD Day 41:**
- Input artifacts (Day 43-46)
- Audio edit / video gen (Day 43-49)
- Dev mode (Day 50-58)
- SKILL.md marketplace (Day 50-58)
- Penpot embed (Bulan 3+)
- Web builder (Day 60-65)
- A-LoRA, Federated, MoE migration (Day 60+ atau defer)

✅ **STAY FOCUSED:**
- 3 ship-today tools (output expansion)
- Cycle 1 trigger (autonomous)
- Beta launch readiness assessment (write guide)

---

## 🧠 8. ADO ALIGNMENT CHECK (3-prong filter)

| Tool | MCP-first? | Skill-portable? | Memory-aware? |
|------|-----------|-----------------|---------------|
| web_read | ✅ MCP module | ✅ standalone | ➖ optional cache to episodic |
| export_pdf | ✅ MCP module | ✅ standalone | ➖ optional artifact storage |
| export_slides | ✅ MCP module | ✅ standalone | ➖ optional artifact storage |

**All pass 3-prong.** ADO modular brain principle preserved.

---

## 🎓 9. LESSONS APPLIED

31. (Day 41) Strategic timing > feature ambition. 6 fitur dimap based on dependency, quick-win, risk profile, cost curve.

---

## 🚀 10. BETA LAUNCH ASSESSMENT (jawab user question)

**Q: Apakah sudah bisa di-share untuk beta acquisition?**

**A: YA — Soft beta selective (3-5 friends Tiranyx network) dengan caveat clear.**

### Pros (kenapa SUDAH bisa):
- ✅ Multimodal LIVE (image attach + mic + Vision describe)
- ✅ Chat continuity stable
- ✅ Tool execution transparent (chips visible)
- ✅ Onboarding 2-question + dynamic starters
- ✅ Smithery LIVE PUBLIC (public proof)
- ✅ Friendly errors + retry
- ✅ 3 domains stable

### Cons (caveat WAJIB beritahu beta user):
- ⚠️ Latency 30-90s normal (CPU 7B, no GPU yet)
- ⚠️ Concurrent ~5 user max sebelum slow
- ⚠️ Model base Qwen2.5-7B (Cycle 1 trigger Day 42)
- ⚠️ No file upload yet (Day 43-46)
- ⚠️ No admin UI for API keys yet (Day 43)

### Rekomendasi tahap akuisisi:
1. **Day 41-46 (Soft beta):** 3-5 friends network Tiranyx, 1-on-1 onboarding session, capture feedback
2. **Day 47-49 (Iterate):** fix bug dari feedback, add file upload (Day 43-46)
3. **Day 50-58 (Open beta):** post-Cycle-1 + speculative decoding live (model lebih cepat + custom soul). Public invite via Twitter.
4. **Bulan 3 (Public beta):** dev mode beta + skill marketplace = komunitas builder

### Saya akan tulis BETA_LAUNCH_GUIDE.md terpisah dengan template invite + caveat list + onboarding script.

---

**THIS IS THE COMPASS for Day 41. 3 tools ship today (~4 jam, ~$0.30). Beta soft-launch ready.**
