# DAY 68 SPRINT PLAN — Product Stabilization
**Tanggal:** 2026-05-08 (Day 68)
**Penyusun:** Claude (main implementator hari ini, per protokol Day 67)
**Parent:** `ROADMAP_DAY67_MASTER.md` (Phase A — Stabilization)
**Co-watchers:** Codex (read-only QA), Kimi (strategi/docs)

> **Tujuan dokumen ini:** mengisi 3 gap di master roadmap — (1) Codex audit Day 67 yang konkret per P1/P2/P3, (2) Active Inference + Causal AI moats dari riset 2026-2027, (3) Day 68 sprint plan tactical dengan hour-by-hour + OKR per task.

---

## A. INTEGRASI CODEX AUDIT DAY 67

Master roadmap berfokus ke flywheel/Cycle/Hafidz tapi kelewatan 7 issue konkret yang Codex temukan. Berikut mapping ke Phase A:

| ID | Codex Finding | Severity | Phase A Slot | Owner |
|----|---------------|----------|--------------|-------|
| **C1** | Conversation history belum E2E (UI pakai localStorage padahal API `/v1/conversations` ready) | **P1** | Day 68 P0 | Claude |
| **C2** | Server working tree `/opt/ado` kotor — cycle*_output, docs_pending, .bak, api_backup nested, eval outputs untracked | **P1** | Day 68 P0 (sebelum deploy lain) | Claude |
| **C3** | Mobile UI: sidebar `display:none` di breakpoint mobile = user kehilangan akses NEW CHAT, agents, history, logout | **P1** | Day 68 P0 | Claude |
| **C4** | Version labels stale: API 0.5.16, chat boot v0.4.1, dashboard v0.4.7 padahal Day 67/commit 30f254d | **P2** | Day 68 P1 | Claude |
| **C5** | OpenAPI schema: admin/license routes ditandai open padahal live guard 401/403 — misleading buat integrator | **P2** | Day 70 | Claude |
| **C6** | Admin dashboard simpan `X-Admin-Key` di localStorage — XSS surface | **P2** | Day 70 | Claude |
| **C7** | `/v1/speech/to-text` open + cost-bearing (ElevenLabs) — rate limit 10/min, 25MB cap, tapi tanpa auth | **P2** | Day 70 (atau session-token) | Claude |
| **C8** | Favicon 404 noise di nginx error log | **P3** | Day 68 P2 (10 menit) | Claude |

**Kenapa gap ini berbahaya kalau diabaikan:** 53 user beta yang udah ada akan churn pelan-pelan kalau mobile broken (Indonesia mobile-first ~85%) dan history hilang setiap reload. Itu menjelaskan **0 feedback signals** sebagian — bukan UI feedback button broken doang, tapi seluruh re-engagement loop broken (gak bisa balik ke conv lama).

---

## B. ACTIVE INFERENCE + CAUSAL AI MOATS (from "migancore new riset.md")

Master roadmap fokus ke incremental loop. Riset 2026-2027 yang user kasih tegas: **diferensiasi terkuat solo founder bukan model — itu komoditas — tapi arsitektur kognitif: Active Inference + Causal AI + memori multi-tier + self-evolving skill**. Ini "moat arsitektural" yang Gartner sebut pembeda 60% projek yang berhasil vs 40% yang dibatalkan 2027.

### B.1 Active Inference / Free Energy Principle

**Apa:** Agent yang minimize variational free energy → curiosity-driven exploration tanpa hand-crafted reward. Alternative ke RL.

**Bukti komersial:** VERSES Genius — Mastermind solved 100% of time, 140× faster, 5,260× cheaper than o1-preview ($0.05 vs $263). Caveat: vendor benchmark, satu game spesifik, revenue $400K/6mo.

**MIGANCORE relevance:** ADO yang diturunkan ke per-org butuh adaptive ke domain berubah (BPJS rule update, OJK regulasi baru, SOP klien revisi). Active Inference loop = ADO yang explore proactively saat detect distribution shift, bukan nunggu SimPO cycle berikutnya.

**Implementasi:**
- Library: `pymdp` (Python) atau `RxInfer.jl` (Julia, Eindhoven Bert de Vries blueprint)
- Domain-pertama: document approval workflow (cocok untuk firma hukum target market)
- Effort: ~3-4 minggu solo founder, **defer ke Phase D Day 161+** karena butuh Phase A-C (real signal + paid client) dulu
- Risk: VERSES revenue lambat (bukti commercial scaling slow) — bisa jadi this is academic, not market
- Mitigasi: implement Day 170-180 sebagai **prototype showcase** (1 vertical demo) bukan production primary. Whitepaper-first sebelum production.

### B.2 Causal AI

**Apa:** Living Causal Graph + do-calculus + Structural Causal Models. Jawab counterfactual: "what would have happened if X was different?"

**Bukti teori:** DeepMind 2024 theorem — "Any agent capable of adapting to a sufficiently large set of distributional shifts must have learned a causal model" (mathematical proof).

**Bukti komersial:** Causaly (9 pharma clients termasuk Gilead, UCB, Novartis), 500M scientific facts × 70M cause-effect rels, cut literature review 90%.

**Bukti pain:** Carnegie Mellon study — 74% "faithfulness gap" pada LLM/CoT/RAG (model explanation tidak mencerminkan reasoning sebenarnya). MIGANCORE sebagai brain klien tidak boleh punya gap ini di domain regulated (legal, healthcare, finance).

**MIGANCORE relevance:** ICP brief (firma hukum, klinik, BUMN, manufaktur) **wajib** decision-grade output. CoT fakebait tidak akan lulus audit di 3 dari 5 segmen ini. Causal AI = required arsitektur untuk segmen Tinggi/Sangat Tinggi willingness-to-pay.

**Implementasi:**
- Library: `DoWhy` (Microsoft) + `EconML` + custom SCM layer di Python
- Expose via MCP tool: `do_intervention(X=x)` (return effect on Y) + `counterfactual(if_X_was_x_then_Y)` (return alternative outcome)
- Effort: ~2-3 minggu solo founder, **trigger Phase C atau D early** (Day 121-130) sebagai differentiator first paid client
- Domain-pertama: kasus kontrak hukum (counterfactual: "kalau klausul X diubah, apa risiko nya?")
- Risk: butuh data structured (knowledge graph populated) — Phase A milestone M-KG (`kg_entities` populated dari fact_extractor) prerequisite

### B.3 Mengapa keduanya = MOAT 5+ tahun

| Faktor | Detail |
|--------|--------|
| Tidak bisa di-clone via prompting | Bukan "tambah kalimat di system prompt." Beda paradigma. |
| Tidak bisa di-clone via fine-tune | Tidak ada dataset publik. Setiap implementasi vendor unik. |
| Mathematical foundation | DeepMind theorem (Causal AI), Free Energy Principle (Active Inference) — peer-reviewed. |
| Require full-stack engineering | Knowledge graph + symbolic reasoner + sampling layer + MCP. Bukan one-trick. |
| Vendor lapuk | VERSES revenue kecil, Causaly seg pharma niche. **Window arbitrage 12-18 bulan untuk solo founder Indonesia.** |

### B.4 Keputusan untuk roadmap

**Tambahan ke milestones master:**

| # | Milestone Baru | Target Day | Measurement |
|---|---------------|-----------|-------------|
| **M13** | Causal AI module v0 — DoWhy MCP tool live | Day 125 | `MCP do_intervention()` return correct effect on toy DAG (Simpson's paradox example) |
| **M14** | Causal AI demo 1 domain | Day 135 | 1 contract clause counterfactual demo recorded, ≤3 min video |
| **M15** | Active Inference prototype | Day 175 | pymdp loop di document approval — 10 trial state convergence |
| **M16** | Whitepaper "Cognitive Kernel for Indonesian Enterprise" | Day 180 | 12-15 hal dengan benchmark replicable, draft published Substack/arxiv |

**Decision lock baru:** Phase C+D = brain harus expose `do_intervention()` + `counterfactual()` MCP tool sebelum first BERLIAN-tier (Rp 30jt/bln) license dijual. Argumen marketing zero-data-leak doang gak cukup di segmen Sangat Tinggi.

---

## C. DAY 68 SPRINT PLAN — Hour-by-Hour

> **Mode:** Claude Code main implementator. Codex audit setelah setiap commit. Kimi review file changed kalau ada strategic decision.

### Pre-flight (07:00-08:00 WIB)
- [x] Baca `MIGANCORE-PROJECT-BRIEF.md` ✓ (done sesi ini)
- [x] Baca `migancore new riset.md` ✓ (done sesi ini)
- [x] Baca `ROADMAP_DAY67_MASTER.md` (agent output) ✓
- [x] VPS cleanup (4.4GB archived, 1.4GB RAM freed, perf 1-4s warm) ✓ (done malam Day 67)
- [x] Cycle 6 status: training step 92/118 (78%), recovery scripts polling ✓
- [ ] **Cycle 6 outcome (M01)** — auto-handled oleh `wait_cycle6.sh` → `post_cycle6.sh`. Cek pagi.
- [ ] **Pre-deploy report:** git status, diff stat, test plan, rollback (di akhir dokumen ini)

### Block 1 — Server hygiene (08:00-10:00 WIB) — addresses C2
**Goal:** `/opt/ado` working tree clean, ready buat trust agent commit selanjutnya.

| Task | Acceptance |
|------|-----------|
| 1.1 Pindah `cycle*_output/` ke `/opt/ado-artifacts/` (sister dir, di-bind-mount kalau perlu) | `git status` di /opt/ado return clean |
| 1.2 Tambah ke `.gitignore`: `cycle*_output/`, `docs_pending/`, `*.bak`, `eval_results/`, `cycle*_failed_attempts/` | `git check-ignore -v` confirms |
| 1.3 Hapus `migancore/api_backup/` (bukan dipakai, sumber confusion) | `du -sh /opt/ado/migancore/` <500MB |
| 1.4 Verifikasi local + server git align ke 30f254d, push hotfix kalau perlu | `git rev-parse HEAD` sama di local + server + GitHub |

**Indicator:** `cd /opt/ado && git status -sb` returns 1 line (`## main...origin/main`).

### Block 2 — Frontend UX P1 (10:00-13:00 WIB) — addresses C1, C3
**Goal:** Conversation history E2E + mobile nav working.

| Task | Acceptance |
|------|-----------|
| 2.1 Audit `frontend/chat.html` riwayat sidebar — saat ini fetch dari mana? | trace di code, dokumentasi di komen |
| 2.2 Wire sidebar ke `GET /v1/conversations` (existing endpoint) — replace localStorage | refresh page → conv list muncul dari server |
| 2.3 Click history item → `GET /v1/conversations/{id}` → render messages array | klik conv lama → message muncul, dapat lanjut chat |
| 2.4 Mobile breakpoint (<768px): sidebar jadi slide-in drawer dengan ☰ button di header | test di Chrome DevTools mobile + screenshot |
| 2.5 DELETE button per conv: prompt confirm → `DELETE /v1/conversations/{id}` | klik delete → conv hilang dari list, tidak bisa diakses lagi |

**Indicator:** Dari fresh login mobile + desktop, user bisa: lihat history, klik history, lanjut chat, delete conv, akses NEW CHAT/agents/logout. **OKR Day 68:** ≥3 user beta lapor history works (DM/WA polling Day 69 pagi).

### Block 3 — Version labels (13:00-13:30 WIB) — addresses C4
**Goal:** UI labels reflect reality (commit/Day).

| Task | Acceptance |
|------|-----------|
| 3.1 `/health` endpoint expose `commit_sha`, `build_time`, `day` | `curl /health` return all 3 fields |
| 3.2 `chat.html` boot text: dynamic dari `/health` (replace hardcoded v0.4.1) | refresh page → text reflect commit |
| 3.3 `dashboard.html` version: dynamic via meta tag injected at build, atau fetch `/health` | dashboard footer reflect commit |

**Indicator:** Tidak ada string `0.4.1`, `0.4.7`, `0.5.16` hardcoded di frontend (`grep -r 'v0\\.[0-9]' frontend/`).

### Block 4 — Favicon + log noise (13:30-13:45 WIB) — addresses C8
**Goal:** Clean error log.

| Task | Acceptance |
|------|-----------|
| 4.1 Tambah `frontend/favicon.ico` (logo Migan/orange dot 32x32) | `curl /favicon.ico` return 200 |
| 4.2 Cek nginx error log 5 menit setelah deploy | grep `favicon.ico` count = 0 |

### Block 5 — Pre-deploy verification (13:45-14:30 WIB) — protokol mandatory
| Task | Acceptance |
|------|-----------|
| 5.1 `git status -sb` (local) — clean, 1 untracked (DAY68_SPRINT_PLAN.md kalau belum committed) | log di chat sebelum deploy |
| 5.2 `git diff --stat origin/main` — show files changed | log |
| 5.3 Test plan: manual desktop + mobile (320px, 768px) di Chrome DevTools | screenshot evidence |
| 5.4 Deploy command: `cd /opt/ado && git pull && docker compose build api && docker compose up -d api` (frontend nginx serves directly) | komen di Day 68 retro |
| 5.5 Rollback plan: `cd /opt/ado && git reset --hard 30f254d && docker compose up -d api` | tested mentally, dokumentasi |

### Block 6 — Deploy (14:30-15:00 WIB)
- SSH ke 72.62.125.6
- Execute deploy command
- Smoke test 3 endpoint: `/health`, `/v1/conversations` (need auth), `/favicon.ico`
- Manual UI test desktop + mobile

### Block 7 — Post-deploy verification (15:00-15:30 WIB)
| Indicator | Target |
|-----------|--------|
| `/health` returns commit_sha=30f254d (atau next commit) + build_time | Pass |
| Mobile UI test (DevTools 375x812 iPhone): sidebar drawer accessible | Pass |
| Conversation history click load past conv | Pass |
| `/favicon.ico` 200 | Pass |
| Ollama response 1-4s warm (regression check dari Day 67 perf fix) | Pass |
| nginx error log 10-min window — 0 favicon 404 | Pass |

### Block 8 — Beta user re-engagement (15:30-16:30 WIB)
**Goal:** Trigger first feedback signal (M02).

- DM 5-10 beta user paling aktif: "UI udah fixed — coba thumbs-up/down 1 jawaban yang bagus, dapat fitur preview"
- Update USER_GUIDE.md sebut feedback button + history
- Post update di WA broadcast (kalau channel ada)

**Indicator:** ≥1 row di `interactions_feedback` Day 69 EOD = M02 hit.

### Block 9 — Day 68 Retrospective (16:30-17:00 WIB)
- Update `MEMORY.md` Day 68 entry + lessons baru
- `git commit -m "docs(memory): Day 68 retro + lessons #148-150"`
- Plan Day 69 (Block 1: Hafidz Ledger Phase A start, Block 2: Letta wiring audit)

---

## D. PROTOKOL MANDATORY (kompresi Codex)

### D.1 Sebelum Eksekusi
- [x] Baca brief + riset + master roadmap
- [x] Map current state (Day 67 EOD)
- [x] Identifikasi gap (Codex audit + research moats)
- [x] Plan ditulis (dokumen ini)
- [ ] User approve rencana sebelum eksekusi (waiting)

### D.2 Per-Task
- Hipotesis: apa yang akan terjadi
- Implementasi: kode/config change
- Testing: manual + automated
- Validasi: acceptance criteria
- Verifikasi: di production setelah deploy
- Catat: di MEMORY.md atau lesson kalau ada finding

### D.3 Sebelum Deploy
- `git status -sb` (lokal clean)
- `git diff --stat`
- Test plan dijalankan
- Deploy command jelas
- Rollback plan jelas
- LAPOR di chat dulu, tunggu konfirmasi user kalau scope besar

### D.4 Setelah Deploy
- Smoke test
- Indicator dicek (lihat tabel per block)
- Catat hasil
- Update memory + lessons
- Commit retro

---

## E. RISK/IMPACT/BENEFIT EVAL — Day 68 Sprint

### Risk
| Risk | Likelihood | Impact | Mitigasi |
|------|-----------|--------|----------|
| Conv history fetch break existing chat (regression) | Med | High | Feature flag `useServerHistory`, default off Day 68, on Day 69 setelah verify |
| Mobile drawer animasi conflict dengan iOS Safari | Low | Med | Test di iPhone real (Fahmi) sebelum buka public |
| Deploy bikin Cycle 6 recovery script terganggu | Low | High | API restart tidak touching `/tmp/wait_cycle6.sh` (PID 158431) atau Vast SSH session |
| Version label fetch /health gagal → empty UI string | Low | Low | Fallback ke "MiganCore" generic kalau fetch fail |

### Impact (Benefit kalau berhasil)
- **User:** History lifetime preserved → re-engagement → repeat conv → feedback signal generation
- **Codex P1 closed:** 3 dari 7 issue resolved (C1, C2, C3)
- **Strategis:** Membuka path Phase A milestone M02 (first signal) → M04 (50 signals) → M05 (Cycle 7 PROMOTE dari real data)
- **Commercial:** Tanpa history E2E, mustahil sell ke klien — 1.5 jam fix unlock seluruh Phase C

### Benefit (Long-term)
- Setiap fix sekarang = compounding karena setiap user re-engaged = potential signal source
- Codex audit ditangani serius = trust di tim development naik
- Master doc + sprint plan jadi template untuk Day 69-80

---

## F. OPEN QUESTIONS (sebelum eksekusi)

1. **Q-A:** Approve sprint plan ini? Atau ada Block yang prioritas berubah?
2. **Q-B:** Cycle 6 outcome (PROMOTE/ROLLBACK) — kapan kira-kira siap dicek? Recovery script auto-poll, tapi kalau user mau live monitor, bisa.
3. **Q-C:** Feedback signal trigger Block 8 — boleh DM 5-10 beta user, atau prefer post broadcast publik?
4. **Q-D:** Active Inference + Causal AI yang ditambahkan ke master roadmap (M13-M16) — confirm bahwa Phase D Day 161-180 = window untuk implement, atau geser?
5. **Q-E:** Untracked file di /opt/ado yang akan di-archive: ada yang perlu di-keep di repo (mis: cycle eval baseline JSON)?

---

*Dokumen ini diupdate setelah Day 68 retro. Subscribe perubahan via git history `docs/DAY68_SPRINT_PLAN.md`.*
