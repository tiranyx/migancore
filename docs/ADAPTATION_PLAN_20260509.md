# ADAPTATION PLAN — MiganCore 2026-2027
**Status:** LIVING DOCUMENT  
**Version:** 1.0  
**Date:** 2026-05-09 14:30 WIB  
**Owner:** Tiranyx / Chief Engineer  
**Basis:** `MIGANCORE-PROJECT-BRIEF.md` + `migancore new riset.md` + `MIGANCORE_ARCHITECTURE_REMAP_v2026.md` + riset web terbaru

---

## I. EXECUTIVE SUMMARY

MiganCore berada di **Day 70** dari 30-Day Blueprint. Infrastructure solid. Brain stuck. Data pipeline baru diperbaiki.

**Keputusan strategis hari ini:**
1. **Foundation First.** Identity Anchor SFT adalah "go/no-go" moment. Jika gagal → revisi strategi training.
2. **Data is the New Oil.** 4 pathways (Self/Owner/User/Teacher) harus mengalir otomatis. Target: 20% real data dalam 2 minggu.
3. **MCP Server + A2A Peer.** Positioning sebagai "Cognitive Kernel-as-a-Service" — bukan chatbot.
4. **Indonesia Window.** 12-18 bulan arbitrage sebelum hyperscaler menutupnya. Danantara >$20B deployable.

---

## II. HIPOTESIS UTAMA

### Hipotesis 1: Identity Anchor SFT akan berhasil dengan rank 32, alpha 64, 5 epochs
**Rationale:** LoRA rank 16 tidak cukup kuat override base Qwen identity. Rank 32 memberi kapasitas representasi 2× lebih besar untuk "Mighan-Core" concept.
**Test:** Tanpa system prompt, 5 fingerprint prompts → cosine sim > 0.85.
**If FAIL:** Naikkan rank ke 64, atau pivot ke full fine-tune (lebih mahal tapi lebih kuat).
**Timeline:** Minggu 4 (Phase 3)

### Hipotesis 2: Multi-loss arsenal > ORPO-only
**Rationale:** ORPO adalah hammer yang melihat semua sebagai paku. Identity = SFT, Preference = DPO/SimPO, User signal = KTO, Reasoning = GRPO.
**Test:** Training cycle dengan kategori terpisah. Eval per kategori.
**If FAIL:** Kembali ke ORPO tapi dengan curriculum mixing yang lebih baik.
**Timeline:** Minggu 3-4 (Phase 2)

### Hipotesis 3: Real-data ratio ≥ 20% akan meningkatkan quality signifikan
**Rationale:** 99% synthetic = circular degradation. Real user feedback + owner corrections memberi signal yang tidak bisa di-generate synthetically.
**Test:** Cycle dengan 20% real data vs 100% synthetic. Compare eval scores.
**If FAIL:** Naikkan teacher distillation budget, atau recruit lebih banyak beta users.
**Timeline:** Minggu 5-6 (Phase 4)

### Hipotesis 4: MCP exposure akan mendatangkan integrator partners
**Rationale:** 9,400+ MCP servers, 78% enterprise adoption. Cognitive Kernel yang expose via MCP = "brain tool" yang bisa dipakai agen lain.
**Test:** Publish MCP server card. Track usage dari agen eksternal.
**If FAIL:** Fokus ke direct B2B SaaS ke vertical Indonesia.
**Timeline:** Minggu 9-12 (Phase 6)

---

## III. EVALUASI DAMPAK

### Dampak Positif (Jika Berhasil)

| Initiatif | Dampak Jangka Pendek (1-3 mo) | Dampak Jangka Panjang (6-24 mo) |
|---|---|---|
| Identity Anchor SFT | Brain tidak lagi "Qwen". White-label viable. | Clone mechanism bisa jalan. Setiap child inherit DNA. |
| Multi-loss engine | Training lebih efektif per kategori. Less regression. | Self-improving loop reliable. Auto-cycle tanpa manusia. |
| 4 Pathways Data | 20-50 real pairs/hari. Quality improvement. | Dataset proprietary yang tidak bisa ditiru kompetitor. |
| MCP Server | Integrator partners, free distribution. | B2A2A revenue stream. Agent marketplace. |
| Indonesia Focus | First 7 clients dari BUMN/RS/firma hukum. | Sovereign AI Fund grant. Regional hub positioning. |

### Dampak Negatif (Jika Gagal)

| Initiatif | Risiko Jika Gagal | Mitigasi |
|---|---|---|
| Identity Anchor SFT | Brain tetap generic. White-label impossible. | Pivot ke full fine-tune. Atau accept generic base + heavy prompt engineering. |
| Multi-loss engine | Complexity tanpa benefit. Waktu terbuang. | Fallback ke ORPO-only dengan better data curation. |
| MCP exposure | No external usage. Wasted effort. | Fokus ke direct B2B vertical. MCP jadi bonus, bukan core. |
| Indonesia timing | Regulation delay. Grant tidak materialisasi. | Bootstrap revenue dari B2B kecil dulu. Jangan tergantung grant. |

---

## IV. EVALUASI MANFAAT

### Manfaat Teknis
1. **Observability by design** — Tiap komponen bisa di-trace, di-audit, di-rollback.
2. **Anti-regression** — Test suite + eval gate mencegah quality drop.
3. **Scalable architecture** — Docker per instance, clone in < 10 menit.
4. **Zero data leak by architecture** — Self-hosted, no telemetry, no cloud sync.

### Manfaat Bisnis
1. **First-mover Indonesia** — Tidak ada competitor lokal dengan positioning "self-hosted AI organism".
2. **Vertical moat** — Setelah client punya 3+ clone, switching cost tinggi (memory, genealogy, tools).
3. **Revenue diversification** — License fee + setup + training + reseller + marketplace.
4. **Grant eligibility** — Sovereign AI Fund, Komdigi accelerator, Danantara PPP.

### Manfaat Ekosistem
1. **Open-source contribution** — MCP server, skill library, bisa dikontribusikan ke komunitas.
2. **Talent pipeline** — Indonesia AI Talent Factory, internship, research collaboration.
3. **Knowledge sharing** — Whitepaper, blog, conference (Indonesia AI Forum).

---

## V. EVALUASI RESIKO

| ID | Risiko | Likelihood | Impact | Severity | Mitigasi | Owner |
|---|---|---|---|---|---|---|
| R-001 | SFT identity anchor gagal (cosine < 0.85) | Medium | High | 🔴 | Naikkan rank ke 64, pivot ke full fine-tune, atau accept prompt-only identity | Training Agent |
| R-002 | Beta users tidak aktif, data tidak mengalir | Medium | High | 🔴 | Owner recruit dari network. Incentivize dengan early access + discount. | Owner |
| R-003 | Teacher API cost > $5/day | Low | Medium | 🟡 | Hard cap di code. Queue pause ketika cap tercapai. | Executor |
| R-004 | Phase 0-1 memakan waktu > 4 minggu | Medium | High | 🔴 | Weekly sprint retro. Cut scope jika perlu. Identity anchor tidak boleh di-cut. | Executor |
| R-005 | Competitor hyperscaler masuk Indonesia | Medium | Medium | 🟡 | Speed-to-market. First 7 clients = moat. Vertical focus > horizontal. | Owner |
| R-006 | Context loss antar AI agent sessions | High | High | 🔴 | STRICT protocol: baca CONTEXT.md + daily log sebelum kerja. Semua decisions di ADR. | All Agents |
| R-007 | Schema drift tanpa Alembic | Medium | High | 🟡 | Alembic MANDATORY. CI gagal kalau tidak ada migration. | Backend Agent |
| R-008 | Test suite terlalu lambat, tidak dijalankan | Medium | Medium | 🟡 | Parallel test, mock external APIs, pre-commit hook. | QA Agent |
| R-009 | Indonesia AI regulation delay | Medium | Medium | 🟡 | Bootstrap revenue dari B2B kecil. Grant = bonus, bukan dependency. | Owner |
| R-010 | Qwen3-8B migration lebih sulit dari perkiraan | Low | High | 🟡 | Delay upgrade sampai identity solid. Qwen2.5-7B cukup untuk MVP. | Training Agent |
| R-011 | Security: prompt injection pada MCP exposure | Medium | High | 🔴 | PromptArmor filter, privilege separation (OpenClaw), behavioral monitoring. | Security Agent |
| R-012 | Self-evolving loop menghasilkan alignment drift | Low | High | 🟡 | Human-reviewed skill library. Constitution checker. Eval gate mandatory. | Core Agent |

---

## VI. RENCANA ADAPTASI PER FASE

### FASE 0: Foundation Hardening (Minggu 1-2)
**Goal:** Infrastructure solid, testing ada, context tidak hilang.

**Adaptasi jika terjadi masalah:**
- Jika test suite terlalu lambat → mock external APIs, skip integration tests di pre-commit
- Jika Alembic migration conflict → manual resolve dengan `alembic merge`, document di ADR
- Jika CI/CD tidak bisa deploy otomatis → fallback ke SSH+script manual sementara

**Success Criteria:**
- `pytest` pass 100% di local dan CI
- `alembic upgrade head` berjalan tanpa error
- Setiap commit ke main otomatis deploy ke staging

---

### FASE 1: Data Pipeline Plumbing (Minggu 2-3)
**Goal:** 4 pathways semua jalan, data nyata mengalir.

**Adaptasi jika terjadi masalah:**
- Jika user feedback masih sedikit → naikkan teacher distillation budget sementara ($5 → $10/day)
- Jika owner upload tidak dipakai → simplify UI, auto-convert tanpa annotation step
- Jika self-growth pairs < 20/hari → turunkan judge threshold (0.7 → 0.6) sementara

**Success Criteria:**
- User thumbs → preference_pairs dalam < 1 jam
- Owner bisa upload dataset dan convert ke SFT/DPO
- Self-growth generate ≥ 20 pairs/hari
- Teacher distillation generate ≥ 50 pairs/hari, cost ≤ $5/hari
- Real-data ratio ≥ 20%

---

### FASE 2: Multi-Loss Training Engine (Minggu 3-4)
**Goal:** Training engine yang bisa pilih loss function sesuai masalah.

**Adaptasi jika terjadi masalah:**
- Jika SFT pipeline tidak converge → turunkan LR (2e-4 → 1e-4), naikkan epochs
- Jika DPO pipeline unstable → gunakan IPO (Identity Preference Optimization) sebagai alternatif
- Jika KTO tidak efektif → fallback ke DPO dengan paired data dari user thumbs

**Success Criteria:**
- Bisa jalankan SFT/DPO/KTO/SimPO dari satu command
- Eval gate automated, PASS/FAIL deterministic
- Dataset builder deterministic (same seed = same output)

---

### FASE 3: Identity Anchor SFT (Minggu 4)
**Goal:** Fix Lesson #170 — identity baked into weights.

**Adaptasi jika terjadi masalah:**
- Jika cosine sim < 0.85 dengan rank 32 → naikkan ke rank 64, alpha 128
- Jika masih < 0.85 → pivot ke full fine-tune (Unsloth full, bukan QLoRA)
- Jika full fine-tune juga gagal → accept prompt-level identity, delay white-label

**Success Criteria:**
- Model tanpa system prompt jawab "Saya Mighan-Core"
- Cosine similarity > 0.85 untuk 5 fingerprint prompts
- Tool-use dan chat quality tidak regress

---

### FASE 4: Beta Data Collection (Minggu 5-6)
**Goal:** Kumpulkan data nyata dari beta users.

**Adaptasi jika terjadi masalah:**
- Jika beta users < 10 → owner recruit dari network, agensi, klien existing Tiranyx
- Jika retention < 70% → interview users, fix UX pain points
- Jika real-data ratio < 50% → tambah synthetic generation sementara, tapi track ratio

**Success Criteria:**
- Real-data ratio ≥ 50% setelah 2 minggu beta
- Brain quality improve dari Cycle 3 baseline
- User retention ≥ 70%

---

### FASE 5: Clone & White-Label (Minggu 7-8)
**Goal:** Unblock revenue — client pertama bisa deploy.

**Adaptasi jika terjadi masalah:**
- Jika clone time > 10 menit → optimize Docker build, pre-build base image
- Jika license enforcement bisa di-circumvent → tighten HMAC validation, add hardware fingerprint
- Jika trilingual (EN/ZH) tidak cukup baik → delay EN/ZH, fokus ID dulu

**Success Criteria:**
- Clone ADO untuk client baru dalam < 10 menit
- Client bisa ganti nama ADO jadi "SARI" atau "LEX"
- License enforcement aktif, tidak bisa circumvent
- ADO bisa respond dalam EN dan ZH (minimum basic)

---

### FASE 6: Revenue Path (Minggu 9-12)
**Goal:** First paying client, billing, support.

**Adaptasi jika terjadi masalah:**
- Jika first client sulit didapat → offer pilot gratis 30 hari dengan commitment bayar jika satisfy
- Jika billing integration kompleks → manual invoice dulu, otomasi nanti
- Jika support overwhelm → ticket system + knowledge base, bukan 1-on-1 chat

**Success Criteria:**
- Landing page migancore.com live (trilingual)
- First client onboarded, deployed, trained
- Invoice issued dan paid

---

## VII. BENCHMARKING FRAMEWORK

### Indikator Harian (Daily Dashboard)

| Metric | Target | Warning | Critical | Tool |
|---|---|---|---|---|
| API uptime | > 99.5% | < 99% | < 95% | UptimeRobot + Grafana |
| API latency (p95) | < 500ms | > 1s | > 3s | Prometheus |
| Ollama tokens/sec | > 7 t/s | < 5 t/s | < 3 t/s | Custom benchmark |
| Error rate | < 1% | > 2% | > 5% | Prometheus |
| RAM usage | < 85% | > 90% | > 95% | Grafana |

### Indikator Sprint (Weekly Review)

| Metric | Target | Current | Delta |
|---|---|---|---|
| Test coverage | > 60% | ~5% | +55% needed |
| Alembic migration health | Pass | Pass | ✅ |
| Real-data ratio | ≥ 20% | ~1% | +19% needed |
| Preference pairs / day | ≥ 70 | ~0.5 | +69.5 needed |
| Identity cosine sim | > 0.85 | N/A (no SFT yet) | TBD |
| Tool-use accuracy | > 80% | ~60% | +20% needed |

### Indikator Milestone (Monthly)

| Milestone | Target Date | Success Criteria |
|---|---|---|
| M0: Foundation Lock | 23 Mei 2026 | pytest 100%, CI/CD auto-deploy, no context loss |
| M1: Identity Anchor | 06 Juni 2026 | cosine sim > 0.85, deploy ke staging |
| M2: Multi-Loss Engine | 20 Juni 2026 | 4 methods runnable, eval gate automated |
| M3: Self-Improvement Loop | 18 Juli 2026 | 1 cycle auto-complete tanpa manusia |
| M4: Beta Live | 01 Agustus 2026 | 10 beta users, 50% real data, 70% retention |
| M5: First Revenue | 15 Agustus 2026 | First client onboarded, invoice paid |

---

## VIII. DECISION LOG (NEW)

| ID | Tanggal | Keputusan | Alternatif | Alasan | Dampak |
|---|---|---|---|---|---|
| D-017 | 2026-05-09 | Commit knowledge auto-update ke git | `.gitignore` knowledge | Knowledge base harus versioned dan deployable | +18 baris per update, tracking history kurs/IHSG |
| D-018 | 2026-05-09 | `exec_driver_sql()` untuk JSON-heavy migration | Escape colon atau bindparams | Paling robust, minimal change, bypass parsing sepenuhnya | Semua migration ke depan pakai pattern ini untuk JSON |
| D-019 | 2026-05-09 | Dokumentasi lesson learned wajib format standar | Free-form notes | Agar agent lain bisa baca dalam 30 detik | Template locked, semua lesson migrate ke sini |
| D-020 | 2026-05-09 | Riset mingguan via web search + digest | Manual browsing | Efisien, comprehensive, terstruktur | Research Agent harus update `RESEARCH_FEED.md` mingguan |

---

*Dokumen ini direview setiap sprint retro. Update setelah setiap milestone.*
