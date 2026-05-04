# Day 36 Checkpoint — Bulan 2 Week 5 Re-Anchor
**Date:** 2026-05-04 (Day 36 evening, Bulan 2 Week 5 Day 1)
**Purpose:** Re-iterate visi, audit posisi nyata, identifikasi leak, putuskan next step. Anti scope-creep checkpoint sebelum Day 37.
**Trigger:** User minta "Catat, simpulkan, iterasi ulang visi produk, onboarding, roadmap. Optimasi yang masih bisa?"

---

## 🎯 1. VISI PRODUK — RE-ANCHOR (Tidak Berubah)

> **Migancore = Autonomous Digital Organism (ADO).** Core Brain AI yang bisa diajak ngobrol, mengingat semua konteks, menggunakan tools, **memperbaiki diri setiap minggu**, dan **melahirkan child agents** dengan kepribadian unik.

**Boundaries (LOCKED — dari kickoff doc + WEEK4_DECISIONS_LOG):**
- ✅ Semua dev di `*.migancore.com` saja sampai Core matang
- ❌ Consumer domains (mighan, sidixlab, mighantect3d, tiranyx) → **Bulan 3+**
- ❌ 10-domain specialist ADO → **Bulan 4+**
- ❌ Marketplace, billing, mobile → defer

**5-Level Evolution — Status Honest (Day 36):**

| Level | Target | Status Hari Ini | Gap |
|-------|--------|-----------------|-----|
| L1 Seed | VPS + LLM + first token | ✅ DONE | — |
| L2 Director | Tools + memory + RAG | ✅ DONE | — |
| L3 Factory | Spawn + mode templates | ✅ **UI live, 4 agents bred (3 G0, 1 G1)** | Belum dipakai user lain |
| L4 Innovator | Self-Reward → SimPO → A/B | ⚠️ **Pipeline 100% siap, NEVER triggered** | Tunggu DPO ≥500 (now 277) |
| L5 Breeder | Spawn live + tree + clone | ⚠️ **Backend + UI live, marketplace defer** | Bulan 3+ |

**Kesimpulan posisi:** Kita di **akhir L3, ujung L4**. Cycle 1 belum jalan = belum bisa klaim "self-improving". Itu blocker terbesar untuk narasi produk.

---

## 📊 2. STATE HARI INI (Day 36 Evening — Honest Audit)

### Production health
| Component | Status | Verified |
|-----------|--------|----------|
| API v0.5.2 | ✅ healthy | `curl /health` HTTP 200 |
| Landing migancore.com | ✅ HTTP 200 (2.6 KB) | live |
| Chat app.migancore.com | ✅ HTTP 200 (59 KB) | live, hardened Day 36 |
| MCP api.migancore.com/mcp/ | ✅ HTTP 401 (auth required, expected) | live |
| nginx SSE | ✅ 600s timeout, buffering off | Day 36 fix |
| DPO pool | 277 pairs (262 synth + 15 CAI) | growing |

### Yang sudah di-ship (cumulative)
- 10 tools (web, code, image, file, http, memory, spawn, TTS)
- MCP Streamable HTTP server (4 resources + 7 tools)
- API keys system (mgn_live_*) + migan CLI
- Distillation pipeline (4 teachers verified)
- Spawn UI + Genealogy Tree (D3.js)
- 3 mode templates (customer_success, research_companion, code_pair)
- Identity eval set (20 prompts, ≥0.85 cosine gate)
- SimPO training scripts (export, train, convert GGUF)
- Hot-swap framework + guide
- migancore.com landing (full design system)
- Chat UX hardening (Day 36: thinking indicator + retry + friendly errors + cancel propagation)

### Yang BELUM ada (gap honest)
- ❌ **Onboarding flow** — user baru hit chat kosong, no template suggestion, no example prompts, no guided tour
- ❌ **Cycle 1 SimPO** — never triggered (waiting 500 pairs)
- ❌ **Identity eval baseline run** — script ada, never executed end-to-end
- ❌ **Auto-retry chat** — masih manual button (Day 36 retry)
- ❌ **Conversation export** — promised Bulan 2 Week 6
- ❌ **Beta invite system** — registrasi masih open, no invite codes
- ❌ **Multimodal input** — image/file attach (deferred Bulan 2)
- ❌ **GPU inference** — CPU 30-90s response time = beta dealbreaker (Week 7)
- ❌ **Server-side partial persistence** — Vercel AI SDK pattern (deferred)
- ❌ **HTTP/2 → HTTP/1.1 SSE downgrade** (deferred, monitor first)

---

## 🚪 3. ONBOARDING — CURRENT vs IDEAL

### Current (broken story)
1. User Fahmi bagi link `app.migancore.com` ke 5 calon beta
2. Mereka klik → form register → email/pass
3. Login → sidebar kosong (no agents) atau default agent → input box kosong
4. **No system prompt context. No "what is this." No example prompt. No template picker.**
5. Mereka ketik "halo" → MiganCore (Qwen2.5-7B base) jawab generic
6. Karena CPU 30-90s, mereka mungkin tutup tab sebelum jawaban selesai
7. Kalau pun jawaban masuk, mereka tidak tahu: ini bisa apa? bisa pakai tool? bisa di-spawn? bisa dikasih kepribadian?

**Result kemungkinan: bounce rate >80% dari beta cohort.**

### Ideal Minimum (Bulan 2 Week 6 ready)
1. Login → **First-Run Modal**:
   - "Selamat datang. MiganCore adalah AI yang belajar dari obrolan kita."
   - **Pilih kepribadian awal:** [Customer Success] [Research] [Code Pair] [Custom blank]
   - "Apa yang ingin kamu lakukan dulu?" → 3 example prompts (clickable)
2. Masuk chat dengan agent default sudah ber-template
3. **Chat empty state:** 4 starter cards ("Tanya tentang X", "Buat plan Y", "Generate gambar Z", "Review file W")
4. **Tooltip sekali jalan:** "Sidebar = agent kamu. + button = lahirkan child agent dengan kepribadian baru."
5. **Footer chip:** "MiganCore mengingat 30 hari obrolan. Privasi: data hanya di server kamu."
6. Link kecil ke `migancore.com` untuk konteks penuh

### Effort estimate
- First-Run Modal + template picker: **3-4 jam** (chat.html + localStorage flag)
- Empty state starter cards: **1 jam**
- Tooltip walkthrough: **2 jam** (intro.js atau custom)
- **Total: ~1 hari kerja (Day 37 PM)**

---

## 🛠️ 4. OPTIMASI — TIERED (Apa yang Masih Leaky)

### TIER A — Blocks Bulan 2 milestones (do first)

| # | Leak | Impact | Fix Effort |
|---|------|--------|------------|
| A1 | DPO velocity unverified | SimPO trigger blocked | Restart synthetic + monitor (1jam) |
| A2 | Identity eval baseline never run | Tidak tahu apakah model dasar lulus gate | Dry-run script (2jam) |
| A3 | Onboarding kosong | Beta bounce risk >80% | First-run modal + starters (4jam) |
| A4 | No conversation export | Beta tidak bisa save percakapan penting | MD/JSON download (3jam) |
| A5 | No beta invite codes | Open registration = spam risk | Invite code table + flow (3jam) |

### TIER B — Quality of life (Bulan 2 Week 6-7)

| # | Leak | Impact | Fix Effort |
|---|------|--------|------------|
| B1 | Auto-retry exp backoff | Manual retry button = friction | 2jam |
| B2 | Server-side partial persist | Network drop = lost message | 5jam (Vercel pattern) |
| B3 | Last-Event-ID resume | Mid-stream truly resumable | 4jam |
| B4 | MCP usage telemetry | No analytics on tool usage | 3jam |
| B5 | Rate limit `/v1/public/stats` | DDoS surface | 30 min |
| B6 | Distillation auto-cron | Manual trigger now | 2jam |
| B7 | Memory recall quality eval | LoCoMo-style benchmark | 1 hari |

### TIER C — After Cycle 1 done (Week 7+)

| # | Leak | Impact | Fix Effort |
|---|------|--------|------------|
| C1 | CPU inference latency 30-90s | Beta dealbreaker | RunPod GPU pod ($7/10jam) |
| C2 | Multimodal input (image/file) | 2026 table stakes | 1 hari per modality |
| C3 | STT voice input | Nice-to-have | 1 hari (ElevenLabs Scribe) |
| C4 | Browser-use tool | Nice-to-have | 1 hari (Anchor browser) |
| C5 | Vision tool (analyze_image) | Nice-to-have | 1 hari (Gemini Vision) |
| C6 | Distillation GPU pod | Eliminates Ollama bottleneck | $7 +1 hari setup |

---

## 🗓️ 5. ROADMAP REVISI — BULAN 2 WEEK 5 (Day 37-42)

### Original BULAN2_PLAN Week 5 (linear)
- Day 37: monitor DPO
- Day 38-40: SimPO Cycle 1
- Day 41-42: hot-swap + A/B

### Revised — TWO PARALLEL TRACKS (better risk distribution)

**Track A — Training (autonomous, hands-off):**
- Day 37 AM: verify synthetic generator alive, restart if dead, log velocity
- Day 37 PM: identity eval **baseline dry-run** (catch issue BEFORE expensive SimPO)
- Day 38: monitoring tick, expect 350-400 pairs by EOD
- Day 39: pool hits 500 → trigger SimPO Cycle 1 ($5.50)
- Day 40: convert GGUF + identity eval on v0.1
- Day 41: hot-swap if eval ≥0.85 (otherwise rollback + document)
- Day 42: A/B 24h begin

**Track B — User-facing (beta-readiness):**
- Day 37 PM: **First-run modal + template picker + starter cards** (Tier A3) ⭐
- Day 38: conversation export MD/JSON (Tier A4)
- Day 39: beta invite codes + registration gate (Tier A5)
- Day 40: auto-retry exp backoff (Tier B1)
- Day 41-42: dogfood polish based on Fahmi's own usage

### Day 43-49 (Week 6) — Beta Launch
- Day 43: invite 5 beta dari network Fahmi
- Day 44-46: 1-on-1 onboarding sessions, capture feedback
- Day 47-49: iterate based on real feedback

---

## ▶️ 6. RECOMMENDED NEXT STEP — Day 37

**Two half-days, both Tier A:**

### Day 37 AM (~2 jam) — Training health check
1. SSH ke VPS, check: synthetic generator running?
2. Last 24h pair count log
3. If stopped: restart with `target_pairs=1000`
4. Run identity eval **baseline** on current Qwen2.5-7B (script ada di `eval/run_identity_eval.py`)
5. Document baseline cosine sim score → expected 1.00 (self-comparison) tapi useful sebagai sanity test

### Day 37 PM (~4 jam) — Onboarding First-Run ⭐ HIGHEST ROI
1. `chat.html`: First-Run Modal (template picker + 3 example prompts)
2. localStorage flag `migancore.onboarding.completed`
3. Empty-state starter cards (4 prompts klik)
4. Tooltip ringan untuk Spawn button
5. Bump v0.5.2 → v0.5.3
6. Deploy + manual E2E test (incognito → see modal → pilih → masuk chat)
7. Commit `docs/DAY37_PLAN.md` + `DAY37_PROGRESS.md`

**Why these two specifically:**
- Training Track A = autonomous dari sini, jadi verify-and-leave hari ini
- Identity eval dry-run = mencegah waste $5.50 RunPod kalau pipeline broken
- Onboarding = **#1 blocker untuk klaim "5 beta users" exit kriteria Bulan 2**
- Both fit dalam 1 hari → punya buffer Day 38 untuk DPO velocity check

**What we explicitly DON'T do Day 37:**
- ❌ Multimodal input (defer Week 6)
- ❌ GPU inference (defer Week 7)
- ❌ Browser-use / Vision (defer Week 8 or Bulan 3)
- ❌ mighan.com / sidixlab.com (defer Bulan 3+)

---

## 🎓 7. PELAJARAN DARI 35 HARI YANG DIJAGA

1. **Compass doc setiap minggu mencegah scope creep** (Week 4 lesson)
2. **Verify before commit assumes** (Day 36 nginx fix verified syntax + reload + smoke test)
3. **Dokumentasi adalah "project RAM"** — kalau hilang, agent berikut salah arah
4. **User VISI lebih akurat dari trend research** (Week 4: "10-domain ADO" = wrong scope)
5. **Friendly error mapping = high-ROI UX** (Day 36)
6. **Default infra config umumnya hostile to streaming** (nginx 60s, HTTP/2 HOL blocking)
7. **Container `--build` mandatory untuk code changes** (Day 28 painful lesson)
8. **Cost discipline: stop+ask kalau >$1** (kept Week 4 spend <$0.05)

---

## ✅ EXIT CRITERIA — Day 37 (besok)

- [ ] Synthetic generator confirmed running OR restarted
- [ ] Identity eval baseline score documented
- [ ] First-Run Modal live di `app.migancore.com`
- [ ] Empty-state starter cards visible
- [ ] v0.5.3 deployed + healthcheck pass
- [ ] `docs/DAY37_PLAN.md` + `DAY37_PROGRESS.md` committed
- [ ] `memory/day37_progress.md` + MEMORY.md index updated

---

**THIS IS THE COMPASS for Day 37. Refer back if drift.**
