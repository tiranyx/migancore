# WEEK 4 PLAN — "Win Creative Domain Completely + Ship What Differentiates"
**Date Drafted:** 2026-05-04 (Day 28 evening)
**Agent:** Claude Opus 4.7 (1m context)
**Type:** Strategic Plan — protocol audit, vision-aligned, await approval

---

## 🎯 NORTH STAR (Tetap)

> **MiganCore = Indonesian Autonomous Digital Organism with self-improvement DNA.**
> Tools modular, persona sacred (SOUL.md), 4 specialist diturunkan (MighanTech3D / SIDIX / Ixonomic / Tiranyx).
> DPO flywheel via CAI + Synthetic + Distillation = competitive moat.

**Strategic insight dari research:** "If I were Fahmi — STOP adding domains. WIN ONE (Creative) COMPLETELY. Visible self-improvement = flywheel narrative no US startup will copy because it needs patience, not capital."

**Translation untuk Week 4:** Fokus = **Creative domain completion** + **shipping the moat** (multimodal chat, browser-use, "Watch MiganCore Learn" dashboard).

---

## 📊 STATE ASSESSMENT (Day 28 → Week 4 entry)

| Dimension | Status | Gap to "good" |
|-----------|--------|---------------|
| Backend infra | ✅ Production-grade | — |
| Tool catalog | ✅ 8 tools (gen, file, search, memory) | Need: video, music, vision, browser |
| Distribution | ✅ MCP server + 3 client integrations | — |
| DPO flywheel | ✅ 3 sources active, 277 pairs | Target 1500 by end Week 4 |
| Chat UX | ⚠️ Text-only chat | Need: file attach, image attach, voice (table stakes 2026) |
| External data | ⚠️ web_search basic + http_get | Need: browser-use, GitHub, HF, Firecrawl |
| Specialist agents | ❌ None deployed | Need: 1 specialist (Creative Director) |
| Public narrative | ❌ Internal only | Need: "Watch Migan Learn" dashboard, public commits |
| Vision/multimodal | ❌ None | Need: image understanding (Qwen2.5-VL or API) |

---

## 🗓️ WEEK 4 OBJECTIVES (Day 29-35)

### PRIMARY (must-ship)
1. **Multimodal Chat Input** — image / file / drag-drop attach (table stakes)
2. **Browser-Use Agent** — `browser_navigate` tool via Playwright/browser-use
3. **Vision Tool** — `analyze_image` via Qwen2.5-VL or Gemini Vision (start API, self-host later)
4. **Creative Director Agent v1** — first SPECIALIST agent: brief → konsep → image gen → caption (uses generate_image + write_file + memory)
5. **Public "Watch MiganCore Learn" dashboard** — read-only `/learn` page showing pair count growth, last training delta, win-rate (the MOAT NARRATIVE)

### SECONDARY (nice-to-have if time)
6. STT input (ElevenLabs Scribe v2 atau Whisper-large) — voice-to-chat
7. PDF/Doc parser tool (Docling) — file attach → text extraction → context
8. Conversation export (MD, JSON) — basic UX hygiene
9. GitHub connector tool — `github_fetch` (issues, code)
10. First 200-prompt golden eval set — required before any fine-tune trigger

### EXPLICITLY DEFERRED (Week 5+)
- ❌ Specialist agents lain (Programming, Productivity, Marketing, dll) — fokus Creative dulu
- ❌ Legal, Finance, Cybersecurity domain — high liability, premature
- ❌ Physical AI — no hardware
- ❌ SimPO training run di RunPod — tunggu data flywheel mencapai 1500 pairs + golden eval ready
- ❌ Marketplace / payment / billing — business layer Week 6+

---

## 📐 KPIs / SUCCESS METRICS (per item)

| Item | Metric | Target by Day 35 |
|------|--------|------------------|
| Multimodal chat | Image/PDF/MD attach works in chat.html | E2E tested |
| Browser-use | `browser_navigate` tool callable, returns page text | 1 tool added |
| Vision | `analyze_image` tool returns description | E2E with sample image |
| Creative Director Agent | Specialist agent template + persona file + 5 demo runs | 1 agent live |
| Public Learn dashboard | `/learn` page accessible without auth, charts live | Live + 1 tweet shared |
| DPO data flywheel | Total pairs in DB | **>= 1500 pairs** |
| Golden eval set | 200-prompt curated set with expected behaviors | Set committed to repo |
| Fine-tune readiness | Run plan + RunPod cost estimate locked | Plan documented |
| Cost discipline | Total external API spend Week 4 | < $25 |

**Exit criteria for Week 4:** Items 1-5 (PRIMARY) shipped + DPO at 1500+ + golden eval ready.

---

## 🔬 HYPOTHESIS + ADAPTATION

### H1: Multimodal chat input takes ≤ 1 day per type (image, PDF, MD)
- Test: end of Day 29, image attach E2E working
- Adapt fail: drop drag-drop, ship paste-only first (Trello/Slack pattern)

### H2: `browser-use` library integrates cleanly via subprocess (Playwright headless)
- Test: end of Day 30, demo tool returns Google search result text
- Adapt fail: fallback to Firecrawl API (paid but less infra)

### H3: Qwen2.5-VL on RunPod under $0.50/hr is feasible for vision
- Test: rent 1× RTX 4090 ($0.69/hr), benchmark Qwen2.5-VL-7B
- Adapt fail: use Gemini Vision API ($0.0001/image) for production

### H4: Creative Director agent works with existing tools (no new ones)
- Test: agent run 5 sample briefs end-to-end
- Adapt fail: identify missing tool, add 1 (max 1)

### H5: Public Learn dashboard converts to 100+ visits Week 1 via single tweet
- Test: post tweet from Fahmi's account, measure visits
- Adapt fail: iterate copy, retarget; metric is "shipped + tested", not viral

---

## ⚠️ RISKS

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Distillation pipeline still flaky (Ollama timeouts) | Medium | Medium | Day 29 Phase 0: investigate + fix root cause |
| Browser-use heavy dep (Playwright + Chromium = 500MB+) | High | Low | Run as separate Docker service, mount tool only |
| Vision via API expensive at scale | Medium | Low | Start API, self-host Qwen2.5-VL on RunPod when traffic demands |
| Multimodal UX complexity blows time budget | High | Medium | Cap each input type at 1 day, ship MVP not perfect |
| User has no time to test (Fahmi solo) | Medium | High | Build into chat.html first, dogfood himself |
| DPO 1500 target unrealistic if distillation slow | High | Low | Run synthetic + distillation in shifts (no overlap = no Ollama race) |
| RunPod cost overrun if we trigger training | Low | Medium | DEFER training to end Week 4 / Week 5; only after 1500 pairs + eval |

---

## 💰 COST ANALYSIS

| Item | Estimate (Week 4) |
|------|-------------------|
| Distillation 500 pairs (Kimi+Claude judge) | ~$5 |
| Synthetic 1000 pairs (free, just Ollama time) | $0 |
| Vision API testing (Gemini if used) | ~$2 |
| RunPod for vision experiment 2 hr | ~$1.50 |
| ElevenLabs TTS + STT testing | ~$1 |
| Fal.ai image gen (testing Creative Agent) | ~$3 |
| Misc API calls | ~$2 |
| **TOTAL Week 4 budget** | **< $15** |

Saldo aman: Anthropic $4.55, Kimi $2, OpenAI $5+, Gemini free tier, ElevenLabs $5, fal.ai $9.99 = **~$26 reserve**.

---

## 📅 DAY-BY-DAY EXECUTION PLAN

### Day 29 — "Stabilize + Multimodal Foundation"
- **AM**: Audit Day 28 distillation results (analyze Kimi pairs, fix any pipeline bug)
- **PM Phase 1**: Add image attach to chat.html (paste from clipboard + drag-drop)
  - Frontend: file input + preview chip
  - Backend: extend `/v1/agents/{id}/chat` to accept multipart with image
  - Pass image as base64 to Vision tool (or save to workspace if no vision yet)
- Commit + deploy + document

### Day 30 — "Vision + File Attach"
- **AM**: Add `analyze_image` tool (start with Gemini Vision API for quick win)
  - Tool wrapper: image bytes → Gemini → description
  - Add to TOOL_REGISTRY + skills.json + agents.json + DB policy migration
- **PM**: Add PDF/MD/code file attach
  - Docling integration for PDF → markdown
  - MD + code: pass directly as text context
  - 25MB soft limit, MIME sniff
- Commit + deploy + E2E test

### Day 31 — "Browser-Use Tool"
- **AM**: Set up browser-use as separate Docker service
  - Or as Python lib in main API container (test memory footprint)
- **PM**: Implement `browser_navigate(url, instructions)` tool
  - Returns: page text, screenshot URL, action log
- Add to MCP exposure + skills.json
- E2E: "search 'MiganCore' di Google" → tool returns top 3 results

### Day 32 — "Creative Director Agent v1"
- **AM**: Design specialist agent
  - SOUL fragment: `creative_director_soul.md` (extends core_brain SOUL)
  - Skills assignment: generate_image, write_file, memory_*, web_search, analyze_image
  - System prompt: "Convert brand brief → visual concept → 3 image variations → caption draft"
- **PM**: Implement agent template registration
  - Add to `agents.json` with `template_id: creative_director_v1`
  - Test E2E: 3 sample briefs → output assessment
- Document in `docs/AGENT_CREATIVE_DIRECTOR.md`

### Day 33 — "Public Learn Dashboard (the MOAT)"
- **AM**: Design `/learn` public page (no auth)
  - Read-only: total pairs, growth chart, source breakdown, latest pair samples (anonymized)
  - "Watch MiganCore Learn — every conversation makes me smarter"
  - Live counter, last 7-day pairs added, training readiness gauge
- **PM**: Deploy to `https://app.migancore.com/learn`
  - Same design system (dark sci-fi)
  - Social meta tags for Twitter/IG sharing
- Fahmi tweets it: "MiganCore is the AI agent that visibly improves weekly. Watch it learn live: app.migancore.com/learn"

### Day 34 — "Golden Eval Set + STT (optional)"
- **AM**: Create 200-prompt golden eval set
  - Categories: creative (50), Q&A (30), reasoning (30), tool-use (30), persona (30), edge cases (30)
  - Format: JSONL with prompt + expected behavior tags
  - Commit to `eval/golden_v1.jsonl`
- **PM (if time)**: STT input via ElevenLabs Scribe v2
  - Mic button in chat.html → record → upload → STT → use as message

### Day 35 — "Polish + Lock + Document"
- Conversation export (MD/JSON download)
- GitHub connector tool (if not done)
- Update CHANGELOG, SPRINT_LOG, CONTEXT, MEMORY index
- `WEEK4_RETRO.md` — what worked, what didn't, lessons
- Lock Week 5 plan

---

## 🎁 BENEFITS — Why This Plan Wins

1. **Closes table-stakes gap** (multimodal chat) — eliminates "looks like toy" first impression
2. **Adds 2 differentiators** (browser-use + public Learn dashboard) — content moat starts building
3. **First specialist agent shipped** (Creative Director) — proof that ADO architecture works
4. **DPO flywheel scaling** to 1500 pairs — training threshold reached, model improvement unlocked
5. **Cost stays under $15** — runway preserved for Week 5+
6. **Foundation for marketplace** — agent template pattern proven, repeatable for Week 5 specialists
7. **Public narrative starts** — "Indonesian AI that learns weekly" = sticky positioning vs OpenAI clones

---

## 🛡️ ANTI-PATTERN COMPLIANCE

| Industry mistake | MiganCore guardrail |
|------------------|---------------------|
| Manus opaque pricing | Public free tier with rate limits, transparent |
| Letta too abstract | Ship product (Creative Agent), expose framework second (already done w/ MCP) |
| Devin cherry-picked demos | Public Learn dashboard = real-time honesty |
| 50+ tools (failure surface) | Cap at 15 well-tested tools — current 8, add 4 max in Week 4 |
| Fine-tune without eval | Build golden eval set BEFORE first SimPO run |

---

## 🔄 ADAPTATION CHECKPOINTS

- **End Day 29**: Multimodal foundation working? If no → simplify scope, defer drag-drop
- **End Day 31**: Browser-use working? If too heavy → use Firecrawl API as fallback
- **End Day 32**: Creative Agent E2E? If issues → 1 more day, push other items
- **End Day 35**: 1500 pairs reached? If under → resume + extend Week 5 first 2 days

---

## ❓ DECISIONS NEEDED FROM USER (BEFORE EXEC)

1. **Approve plan?** Pilihan A (full plan as-is) / B (subset) / C (revisi)
2. **OK pakai Gemini Vision API untuk awal** ($0.0001/image, no GPU rent yet)?
3. **Setuju tunda training run** sampai 1500 pairs + eval ready?
4. **Public Learn dashboard URL**: `app.migancore.com/learn` — okay path?
5. **Fahmi commit untuk Tweet share Week 4 result**? (Critical for narrative moat)

---

## 📂 FILES TO CREATE/MODIFY (estimated)

**New (Week 4):**
- `api/services/vision.py` (Day 30)
- `api/services/browser.py` (Day 31)
- `api/services/file_parser.py` (Day 30)
- `api/services/stt.py` (Day 34, if time)
- `agents/creative_director/soul.md` (Day 32)
- `frontend/learn.html` (Day 33)
- `eval/golden_v1.jsonl` (Day 34)
- `docs/AGENT_CREATIVE_DIRECTOR.md` (Day 32)
- `docs/WEEK4_RETRO.md` (Day 35)
- `migrations/026_day29_multimodal_attachments.sql` (Day 29)

**Modify:**
- `frontend/chat.html` — multimodal input UI (Day 29-30)
- `api/services/tool_executor.py` — 4 new tool handlers
- `config/skills.json` — 4 new skills
- `config/agents.json` — Creative Director template
- `api/routers/chat.py` — multipart support
- `api/main.py` — version bumps per day

---

## 🚀 IF I WERE FAHMI (pure synthesis from research + ADO vision)

Week 4 isn't about adding 10 things — it's about **closing 1 gap (multimodal)** + **adding 1 moat (public learn)** + **proving 1 specialist (Creative)**. By Day 35:
- MiganCore looks like a 2026 AI agent (not a 2024 toy)
- Has visible self-improvement narrative (no competitor copies this in 30 days)
- First specialist agent live (proof for Week 5 specialists)
- Training data ready for first real fine-tune (Week 5 SimPO)
- Cost under $15

Week 5 is then: SimPO training trigger + 2 more specialists (Productivity, Programming) + early-access invite list. Week 6: marketplace foundation + first paying user. Week 8 (end of Month 2): seed conversations Q2 2026.

This plan respects your unfair advantage (designer who ships AI) and avoids the trap of generic-feature-adding that destroyed Devin/Manus narrative.
