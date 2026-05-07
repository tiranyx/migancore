# ROADMAP DAY 67 — MASTER STRATEGIC PLAN
**Tanggal:** 2026-05-08 (Day 67+1, post Cycle 6 trigger malam ke-67)
**Disusun oleh:** Claude (Opus 4.7) berdasarkan synthesis 8 dokumen strategis + 67 hari progress
**Status:** Single source of truth untuk Day 68 → Day 180. Update kalau ada decision lock baru.
**Supersedes (partial):** ROADMAP_BULAN2_BULAN3.md (Day 40 — outdated post-trends), DAY67_PLAN.md (taktis)
**Tidak supersede:** VISION_PRINCIPLES_LOCKED.md (filosofi), PRODUCT_BRIEF_ALIGNMENT.md (brief mapping), VISION_2026_2027_COGNITIVE_TRENDS.md (kompas tren) — dokumen-dokumen itu tetap parent.

---

## ⚠️ CATATAN VERIFIKASI

Sebelum lanjut: ada beberapa angka yang perlu di-reconcile lintas dokumen.

- User prompt menyebut **147 lessons**. ACHIEVEMENT_WRAP.md (Day 67 22:30) menyebut **144**. DAY67_MANDATORY_PROTOCOL.md tertulis 144 (#138-144). MEMORY.md index menyebut "132 lessons cumulative (target)" Day 64 dan tidak menulis count Day 67. **Anggap 144 sebagai canonical Day 67 EOD; 147 mungkin termasuk lesson Cycle 6 promote + post-cycle yang belum ditulis di doc.** [verify]
- User prompt menyebut "Cycle 6 ~step 92/118". DAY67_PROGRESS.md tertulis 14:23 UTC step 9/118, ETA 17:23 UTC. ACHIEVEMENT_WRAP menyatakan PENDING. **Asumsi: Cycle 6 sedang/selesai training; outcome belum ter-dokumentasi pas roadmap ini ditulis.** Roadmap ini tetap valid baik PROMOTE maupun ROLLBACK — keduanya punya branch.
- File `MIGANCORE-PROJECT-BRIEF.md` **tidak ditemukan** di repo sebagai file standalone — hanya direferensikan PRODUCT_BRIEF_ALIGNMENT.md. Brief disaring lewat alignment doc tersebut. **Implikasi:** kalau ada brief versi mentah yang hilang, sebaiknya re-archive untuk audit trail.
- File `DAY67_STRATEGIC_PLAN.md` ada (referenced) tapi tidak dibaca penuh dalam draft ini — diasumsikan superseded oleh dokumen ini.

---

## 1. EXECUTIVE SUMMARY

- **Engine works, market hasn't.** 5 dari 9 prinsip brief ✅ tercapai (otak self-improve, MCP, KB, license, hardware floor). Tapi 53 user beta menghasilkan **0 sinyal feedback** = self-improving flywheel mati di sumbernya. Ini adalah **bug strategis #1**, bukan bug teknis.
- **Production stagnan di Cycle 3 (migancore:0.3, weighted 0.9082).** Cycle 4-5 ROLLBACK. Cycle 6 sedang/baru selesai training. Berarti dalam 11 hari sejak Day 56 GGUF pipeline ready, **brain produksi tidak naik versi**. Bukan masalah algoritma — masalah dataset signal-to-noise (synthetic vs real-user).
- **90 hari berikutnya = 1 taruhan tunggal: validasi flywheel real-user → Cycle 7 dari signal nyata, bukan synthetic.** Kalau berhasil, ini permanently differentiates dari Letta/mem0/Anthropic Skills. Kalau gagal, ADO turun jadi "wrapper Qwen + KB Indonesia bagus" — masih sellable tapi bukan moat.
- **Cost discipline strong.** ~$11-12/bulan dari $30 budget (37%). Vast.ai ~$0.80 lifetime untuk 5 cycles. Bottleneck bukan uang, bottleneck adalah **first paid client** (revenue) dan **first 50 user-feedback signals** (training data).
- **Decision lock untuk Day 68-95:** STOP nambah tools, STOP optimasi infrastructure. FOCUS hanya 3 hal: (1) feedback UI hidup, (2) Hafidz Ledger Phase A, (3) clone mechanism real deploy ke 1 paying client.

---

## 2. STATE OF PLAY — DAY 67

### 2.1 Yang sudah shipped (concrete, runtime-verified)

**Otak (Cognitive Core):**
- migancore:0.3 = Qwen2.5-7B + 685-pair LoRA, identity 0.953, voice 0.817, weighted 0.9082
- 6 training cycles (5 selesai, 1 running): C2 promote, C3 promote, C1/C4/C5 rollback
- ORPO `apo_zero` loss + APO identity λ proven di TRL Mar 2026
- Vast.ai pipeline $0.09-0.25/cycle (vs RunPod $2.50 wasted Cycle 1)
- 3,004 preference pairs di DB (hanya 954 dipakai Cycle 6 export)

**Syaraf (Integration Layer):**
- 23 tools registered (29 dengan 10 cognitive Day 67 — verifikasi: ACHIEVEMENT_WRAP menulis 29, MEMORY.md menulis 23, gap = 10 tools Day 67 belum stable). [verify]
- MCP Streamable HTTP server live (api.migancore.com/mcp/, JWT auth, Smithery public)
- Memory: Qdrant hybrid BM42+dense + Postgres+pgvector + Redis cache + Letta 0.6 (running, **belum ter-wired ke chat router**)
- Multimodal: vision (Gemini), STT (Scribe), TTS, image gen (fal.ai), PDF/PPTX export

**Jiwa (Identity Layer):**
- SOUL.md persona file
- Identity eval baseline (478KB, 20 prompts × 8 categories)
- Hot-swap proven (Cycle 2 → Cycle 3 zero downtime)
- ADO_DISPLAY_NAME white-label config
- License system live (BERLIAN/EMAS/PERAK/PERUNGGU, HMAC-SHA256)

**Distribusi:**
- Clone mechanism Day 67: clone_manager.py (618 lines) + dry-run E2E PASS (license b84227f2... minted, templates rendered, simulated deploy)
- **Real deploy ke client VPS = belum pernah dijalankan**

**Beta (Day 51 → Day 67 = 16 hari):**
- 53 users, 65 conversations, 174 messages
- 0 feedback signals (interactions_feedback table kosong)

### 2.2 Yang masih broken atau missing (jujur, tanpa spin)

| Issue | Impact | Severity |
|-------|--------|----------|
| Feedback UI tidak hidup di app.migancore.com (atau tidak ter-wire ke API) | Self-improving flywheel mati | P0 |
| Hafidz Ledger belum diimplementasi (design doc only) | Closed-loop belajar dari ADO anak gak jalan | P0 |
| Letta running tapi tidak ter-wire ke chat router | Cross-session memory fitur yang udah dibayar (RAM) tidak dipakai | P1 |
| Knowledge Graph kosong (kg_entities=0) | RAG tidak punya structured retrieval | P1 |
| 1,458 SIDIX training pairs untapped | Cycle 7 dataset bisa +40% kalau di-bridge | P1 |
| Cycle 4-5 ROLLBACK pattern (voice drift) | Dataset synthesis methodology punya bug sistemik | P1 |
| Per-org Docker template belum live deploy | Belum bisa onboard paying client | P0 |
| Reasoning traces (Trend #1) belum di-extract | Miss premium training data tipe baru | P2 |
| A2A AgentCard belum ada | Risk: jadi MCP-tool tier 2026, bukan peer agent | P2 |
| ZH (Mandarin) 0 pairs | Trilingual prinsip P9 partial | P3 |
| 14GB rollback models di Ollama | RAM/disk waste | Cosmetic |

### 2.3 Beta data → implikasi strategis

**53 users / 65 conversations / 0 feedback dalam 16 hari.**

Tiga interpretasi mungkin (dipilih satu setelah investigasi):

1. **Feedback UI broken/missing** — paling mungkin karena ACHIEVEMENT_WRAP menulis "Thumbs up/down (Day 65) -- TAPI 0 signals dari 53 users!" yang implies button ada tapi gak fungsi. **→ Day 68 P0 fix.**
2. **UI ada, user gak peduli** — kemungkinan jika feature hidup tapi tidak prominent. **→ design re-iteration setelah verifikasi #1.**
3. **User base bukan target market** — Indonesia friend-network, mostly tech-curious, bukan repeat-use case. **→ butuh shift launch strategy ke vertical (UMKM trial).**

**Implikasi besar:** kalau dalam 7 hari pasca-fix (Day 68→75) feedback signal tetap <10, **launch strategy salah**, bukan produk salah. Perlu pivot ke channel yang punya use-case retention (SIDIX WA bridge punya conversational user base — leverage itu).

### 2.4 Cost vs runway

- Bulan 1+2 cumulative: ~$11-12 dari $30 budget (37%)
- RunPod $7 cap habis Day 49 (untuk 0 success Cycle 1)
- Vast.ai lifetime: ~$0.80 untuk 5 cycles (5-9x lebih murah)
- Compute bottleneck SAAT INI: **bukan compute**, tapi **dataset signal source** (real user vs synthetic)
- Revenue: $0 / 7 client target (per brief break-even)
- VPS shared dengan SIDIX/Tiranyx/Ixonomic (40% RAM utilized, headroom besar)

**Runway statement:** dengan biaya operasi ~$11-12/bulan + Vast cycles ~$0.25/each, secara compute kita bisa terbang 6+ bulan tanpa revenue. **Tapi tanpa first paid client by Day 130, project status berubah dari "indie product" jadi "personal R&D tanpa market validation"** — itu strategis paling fragile, bukan teknis.

---

## 3. 5 BIGGEST RISKS (rank-ordered)

### Risk 1 — Self-improving moat tidak terbukti dengan real user (likelihood HIGH, impact CRITICAL)
**Detail:** Kita claim "ADO yang belajar dari user" tapi 16 hari beta = 0 sinyal. Kalau Cycle 7 (target Day 75-85) tetap pakai synthetic data, kita tidak pernah membuktikan flywheel nyata.
**Mitigation:** Day 68 P0 fix feedback UI + Day 81-95 instrument SIDIX channel (WA conversation logs → DPO pair extraction lewat teacher API offline). SIDIX punya base user aktual = real signal source. Lesson #68 (teacher = mentor) tetap berlaku.

### Risk 2 — Cycle ROLLBACK pattern berlanjut (likelihood MEDIUM, impact HIGH)
**Detail:** 3 dari 5 cycles ROLLBACK. Cycle 4: voice drift dari domain pairs. Cycle 5: Ollama 500 errors. Kalau Cycle 6 juga ROLLBACK (60% probability based on track record) = 3 minggu effort hangus + brain stuck di v0.3.
**Mitigation:** Cycle 7 hyperparams sudah locked dari Lesson #129 (voice gate dominates) + #137 (eval retry=3) + #140 (single source threshold). Tambah: jangan campur kategori dalam 1 cycle besar — lebih baik 200-pair targeted per kategori vs 950-pair scrambled. Identity-anchored seed minimum 30% setiap cycle (Lesson #56 root cause).

### Risk 3 — Distraction dari "lapisan baru" sebelum closed loop terbukti (likelihood HIGH, impact MEDIUM)
**Detail:** Roadmap original (Day 40) merencanakan Dev Mode, Penpot, Web Builder, A2A, Active Inference. Setiap item itu menarik. **Tapi tidak satupun melebarkan moat #1 (closed identity-evolution loop) selama feedback flywheel mati.**
**Mitigation:** Lock Day 68-95 ke 3 deliverable utama saja (Phase A & B). Refuse semua proposal "let's add X" sampai feedback signals ≥50 dan Cycle 7 PROMOTE. Reference: VISION_DISTINCTIVENESS_2026.md §4 STOP list.

### Risk 4 — Tidak ada paid client dalam 90 hari (likelihood MEDIUM, impact CRITICAL)
**Detail:** Clone mechanism dry-run PASS Day 67. Real deploy belum. Tanpa paying client by Day 130, project = R&D tanpa market validation, sponsor (founder) capital allocation jadi pertanyaan.
**Mitigation:** Day 101-130 Phase C dedikasi penuh ke 1 vertical UMKM client (asumsi: dari Tiranyx network — Fahmi punya warm intro). Target: Rp 5jt/bln × 1 = first revenue, terlepas dari size. Activation > optimization.

### Risk 5 — Vendor/model risk: Qwen2.5-7B obsolete sebelum Cycle 7 (likelihood LOW, impact MEDIUM)
**Detail:** Qwen3-8B sudah out (research Day 64-67), Qwen3-30B-A3B juga. Kalau kita stuck di Qwen2.5 sambil kompetitor pindah, identity 0.953 jadi "trained on stale base."
**Mitigation:** K01 di alignment doc lock Qwen2.5 sampai Cycle 5+. Cycle 6 PROMOTE = trigger Qwen3-8B benchmark. Jangan upgrade sampai Cycle 6 PROMOTE (preserves training pair investment). Migration plan ada di QWEN3_UPGRADE_PLAN.md (Day 67 commit 4c72c1e).

---

## 4. 2026 TRENDS APPLIED

Filtered melalui lens "is it a moat-widener atau commoditizing tool-bloat?" Reference: VISION_DISTINCTIVENESS_2026.md decision framework.

### Trend #1 — Reasoning-as-Default (DeepSeek-R1, Qwen3-Thinking)
- **What it means:** Model dengan `<think>` traces + verifier-driven RL bukan premium lagi, default. Reasoning traces = preference pair premium.
- **STOP:** Build "thinking UI" yang ngeluarin internal CoT ke user (commoditized — semua frontend punya).
- **DOUBLE DOWN:** Pipe `<think>` traces dari migancore Cycle 7+ ke Qdrant `reasoning_traces` collection. Setiap traces yang teacher API approve (CAI quorum) = chosen pair untuk SimPO Cycle 8. **Ini moat 6-12 bulan sebelum kompetitor catch up.**

### Trend #2 — Knowledge Specialization (vertical KB beats general)
- **What it means:** Harvey ($3B legal AI), Glean ($1.2B AR enterprise search). General "tahu segala" jadi commodity.
- **STOP:** Push "model umum yang serba bisa" sebagai positioning.
- **DOUBLE DOWN:** indonesia_kb_v1.md sudah v1.3 (1321 baris). Phase B-C butuh 2 vertical KB lagi: `kb_umkm_warung.md` + `kb_legalitas_startup.md` (sumber: BPS, Kemenkop, JDIH, OSS). Setiap vertical = 1 ADO template yang bisa dijual.

### Trend #3 — Bahasa Lokal sebagai Moat (Indonesia 212M users)
- **What it means:** OpenAI/Anthropic tidak akan pernah deep-context ke Bahasa Indonesia + warung kelontong margin 5-15%.
- **STOP:** Coba ngejar GPT/Claude di benchmark English umum.
- **DOUBLE DOWN:** Cycle 7-8 wajib ada >100 pair dalam **konteks** Indonesia (bukan cuma bahasa Indonesia). Day 131+ training pair Bahasa Jawa Ngoko/Krama (95M speaker) untuk pivot regional UMKM. ZH defer ke 2027 (Phase D, low priority).

### Trend #4 — User Data sebagai Flywheel Tersembunyi (KRITIS)
- **What it means:** Setiap interaksi user = signal training. Sistem yang menutup loop ini = compounding moat.
- **STOP:** Generate synthetic Magpie pair lebih besar kalau real user signal masih 0.
- **DOUBLE DOWN:** ⭐ **INI fokus utama Phase A & B.** Feedback UI hidup, Hafidz Ledger Phase A, SIDIX bridge. Kalau Day 95 feedback signals masih <50, BERHENTI synthesis dan reset launch strategy.

### Trend #5 — Enterprise Connector sebagai Moat (UMKM Indonesia tier 1)
- **What it means:** Tokopedia/Shopee/Jurnal/WA Business API = unfair advantage di market UMKM Indonesia.
- **STOP:** Build connector yang udah ada vendor SaaS-nya (mis: Salesforce, generic Slack — bukan target market).
- **DOUBLE DOWN:** Tier 1 Phase B-C: Tokopedia Seller API (read order/produk) + WA Business API (auto-reply customer). Setiap connector = MCP tool. ADO yang bisa "talk to" Tokopedia = hard sell ke UMKM.

### Trend #6 — Sleep-Time Memory Consolidation (Letta v0.5 pattern)
- **What it means:** Cron yang ekstrak durable facts dari episodic ke semantic = parity dengan SOTA.
- **STOP:** Treat memory_pruner sebagai "selesai" (Day 45). Belum upgrade ke consolidator.
- **DOUBLE DOWN:** Phase A: convert memory_pruner → sleep-time consolidator. Cron 03:00 WIB: episodic 24h → CAI quorum extract durable fact → upsert semantic_memory Qdrant collection. Substrate sudah ada, missing piece = consolidator logic. ~2-3 hari kerja.

### Trend #7 — A2A Protocol (Google A2A 14k+ stars, peer-layer above MCP)
- **What it means:** ADO yang tidak daftar A2A = stuck di tier "MCP tool" sementara kompetitor jadi "peer agent."
- **STOP:** Anggap MCP-only sebagai cukup.
- **DOUBLE DOWN:** Phase B: ship `/.well-known/agent.json` + AgentCard. Effort rendah (1 hari), insurance tinggi. ADO daftarkan skills `delegated-judgment` (CAI quorum exposed sebagai A2A skill). Ini adalah **revenue stream baru tahun 2027** (x402 per-inference dari agent lain).

### Trend #8 — Verifier-Driven RL (Tülu 3 pattern, 2027 horizon)
- **What it means:** Reward model lokal (Skywork/Nemotron-distilled) ranking 100x lebih cepat dari API judge.
- **STOP:** Bayar API judge selamanya untuk CAI quorum.
- **DOUBLE DOWN:** Phase D Day 131+: train Qwen3-0.6B reward head dari 450+ accumulated CAI labels. Defer karena butuh signal dataset matang dulu (Phase B output).

---

## 5. ROADMAP — 4 PHASES

### PHASE A — STABILIZATION (Day 68-80, ~13 hari)
**Theme:** "Fix the broken flywheel before adding new spokes."

**P0 (must ship):**
1. **Feedback UI hidup** (Day 68-70) — Audit thumbs up/down di app.migancore.com, wire ke `POST /v1/feedback`, store ke `interactions_feedback`. Gate: pertama signal masuk dalam <72h pasca-deploy.
2. **Hafidz Ledger Phase A** (Day 70-74) — Buat `hafidz_contributions` table + `POST /hafidz/contribute` endpoint + genealogy + knowledge_return field di license.json. Reference: ADO_KNOWLEDGE_RETURN_DESIGN.md.
3. **Cycle 6 outcome handling** (Day 68 pagi) — Jika PROMOTE: hot-swap migancore:0.6, hapus rollback models (~14GB), update config.py. Jika ROLLBACK: post-mortem kategori fail → lock Cycle 7 dataset shape.

**P1 (should ship):**
4. **Letta integration verification** (Day 72-75) — Cek `/api/services/letta.py` apakah dipanggil chat router. Jika tidak: wire untuk cross-session memory aktif.
5. **KG auto-extract** (Day 75-78) — Jalankan `fact_extractor.py` di background post-chat. Mulai populate `kg_entities` (currently 0 rows).
6. **KB cron** (Day 78-79) — `crontab -e` weekly `kb_auto_update.py`. Sudah ada script, belum ter-cron.
7. **Sleep-time consolidator** (Day 79-80) — Convert memory_pruner ke Letta-style consolidator. Cron 03:00 WIB.

**P2 (nice to have, defer kalau backlog):**
8. Hapus rollback models migancore:0.1, 0.4, 0.5 dari Ollama
9. SIDIX 1,458 pair audit (untuk Phase B)

**Phase A Exit Gate:** Feedback signals ≥10 dalam 7 hari pasca-fix + Hafidz endpoint live + Cycle 6 outcome resolved (PROMOTE atau ROLLBACK dengan plan Cycle 7).

---

### PHASE B — FEEDBACK FLYWHEEL (Day 81-100, ~20 hari)
**Theme:** "Real signal in, real model out. Cycle 7 must be from user data, not Magpie."

**P0:**
1. **Cycle 7 dari real signal** (Day 88-95) — Sumber: feedback signals (Phase A) + SIDIX channel data + Hafidz contributions. Target 200-300 *real* pairs minimum (boleh dicampur synthetic 60/40). Dataset shape: identity 30% + voice 25% + tool-use 20% + reasoning_trace 15% + creative 10%. Hyperparams locked di Lesson #129/#137/#140.
2. **SIDIX bridge** (Day 81-86) — Convert 1,458 SIDIX SFT/QA pairs ke ADO DPO format (chosen=teacher, rejected=baseline). Jangan langsung import — lewat CAI quorum filter dulu (lesson 4 teachers Day 28).
3. **A2A AgentCard** (Day 86-88) — `/.well-known/agent.json` endpoint + skill `delegated-judgment`. 1 hari ship, insurance murah.

**P1:**
4. **Reasoning traces pipeline** (Day 90-95) — Pipe `<think>` traces (kalau Cycle 6/7 generate) ke Qdrant `reasoning_traces` collection. Wajib untuk Trend #1 leverage.
5. **Vertical KB #1: kb_umkm_warung.md** (Day 95-100) — Sumber: BPS, Kemenkop, OSS, sample chat UMKM dari SIDIX. Format paralel dengan indonesia_kb_v1.md. ~500 baris target.
6. **Tokopedia Seller API MCP tool** (Day 96-100) — Read order/produk/analytics. Authentication via per-user OAuth (jangan hardcode).

**P2:**
7. WA Business API connector research (Phase C delivery)
8. ZH (Mandarin) 50-pair seed (kalau ada native speaker available)

**Phase B Exit Gate:** Cycle 7 PROMOTE (weighted ≥0.92, identity ≥0.90, voice ≥0.85) + ≥50 feedback signals + ≥1 vertical KB committed + A2A discoverable.

---

### PHASE C — FIRST PAID CLIENT (Day 101-130, ~30 hari)
**Theme:** "Convert engineering to revenue. One client. Real money."

**P0:**
1. **Clone mechanism real deploy** (Day 101-110) — Bukan dry-run. Target: 1 UMKM client dari Tiranyx network. Deliverable: VPS klien terdeploy, `migancore:0.6/7` running, `kb_umkm_warung.md` loaded, license PERAK (Rp 5jt/bln tier) di-mint, `Powered by Migancore × Tiranyx` admin text immutable.
2. **License enforcement live** (Day 105-110) — Startup validator + expired = read-only mode. Reference: license.py (sudah ada `mint_license()`). Test E2E: spoof expired license → ADO masuk read-only.
3. **Per-org Docker template hardening** (Day 110-115) — Docker Compose template parameterized: `ADO_DISPLAY_NAME`, `LICENSE_PATH`, `KB_PROFILE`, `TEACHER_API_KEYS` (encrypted env). Dokumentasi setup-new-ado.sh untuk admin client.

**P1:**
4. **Business data upload UI** (Day 115-122) — Endpoint sudah ada (Qdrant ingestion), UI client-facing belum. Target: client upload SOP PDF → ADO "ngerti" dokumen via RAG. Trigger Tren #2 specialization.
5. **Hafidz Ledger Phase B** (Day 122-128) — Anak ADO knowledge_return ke induk migancore.com (anonymized, opt-in). Setiap kontribusi ke `hafidz_contributions` → feed Cycle 8 training.
6. **WA Business API MCP** (Day 122-130) — Auto-reply customer untuk client UMKM. Tier 1 connector Trend #5.

**P2:**
7. Privacy Vault encryption-at-rest (AES-256 untuk Qdrant, Postgres). Wajib untuk enterprise tier (BERLIAN).
8. Reseller portal foundation (30-40% revenue share program).

**Phase C Exit Gate:** 1 paying client live (terlepas dari Rp/bulan) + license enforcement validated + Cycle 8 dataset includes Hafidz contributions + revenue stream #1 active (sekecil apapun).

---

### PHASE D — SCALE (Day 131-180, ~50 hari)
**Theme:** "Compounding. Multiple clients, multiple cycles, second moat."

**P0:**
1. **Qwen3-8B upgrade** (Day 131-145) — Trigger setelah Cycle 7+ PROMOTE. Identity baseline ulang, training pair re-port (685 pair format-compatible per K01). Hybrid thinking mode (no-think vs think header toggle). Eval gate sama (≥0.92 weighted).
2. **3-5 paying clients onboarded** (Day 131-180) — Reseller program live, Tiranyx network leverage. Target: Rp 25-50jt/bln MRR by Day 180.
3. **Vertical KB #2 + #3** (Day 145-160) — `kb_legalitas_startup.md` (sumber JDIH, Kemenkumham) + `kb_keuangan_syariah.md` (untuk fintech klien). Setiap KB = 1 ADO template sellable.

**P1:**
4. **Bahasa Jawa training pairs** (Day 160-175) — 200 pair Ngoko + Krama dari native speaker. LoRA layer mode bahasa (no base model swap). Pivot ke regional UMKM Jawa.
5. **Reward model lokal (Trend #8)** (Day 165-180) — Train Qwen3-0.6B reward head dari 450+ CAI labels. Cut judge cost ~60%.
6. **Dream Cycle prototype** (Day 170-180) — Innovation #4 dari VISION_DISTINCTIVENESS_2026.md §8. Counterfactual rollout + verifier-curated DPO. Most defensible because butuh full stack yang sudah ada.

**P2:**
7. mighan.com clone marketplace foundation (per Bulan 3 plan original).
8. Multi-instance license management (kelola multiple ADO dari satu admin panel).
9. ZH (Mandarin) 200-pair seed + LoRA mode bahasa.

**Phase D Exit Gate:** Qwen3-8B PROMOTE + 3+ paying clients + 3+ vertical KBs + reward model serving 60% CAI workload locally.

---

## 6. MILESTONES (12 concrete, dated, measurable)

| # | Milestone | Target Day | Measurement | Why |
|---|-----------|-----------|-------------|-----|
| M01 | Cycle 6 outcome resolved | Day 68 | PROMOTE migancore:0.6 atau dokumented ROLLBACK + Cycle 7 dataset plan | Closes Day 67 cliff-hanger |
| M02 | First feedback signal in DB | Day 70 | `interactions_feedback` count ≥1 | Proves UI fix works |
| M03 | Hafidz endpoint live | Day 74 | `POST /hafidz/contribute` returns 201 + row inserted | Phase A core deliverable |
| M04 | 50 feedback signals | Day 95 | `interactions_feedback` count ≥50 | Validates flywheel real |
| M05 | Cycle 7 PROMOTE | Day 95 | weighted ≥0.92 + 5 category gates + ≥30% real signal pairs | Proves real-data training works |
| M06 | A2A AgentCard live | Day 88 | `GET /.well-known/agent.json` returns valid AgentCard | Trend #7 insurance |
| M07 | Vertical KB #1 (UMKM) committed | Day 100 | `kb_umkm_warung.md` ≥500 lines, sourced BPS/Kemenkop | Trend #2 specialization |
| M08 | First paid client live | Day 130 | License PERAK minted + ADO running di VPS klien + invoice issued | Phase C exit, revenue validation |
| M09 | Qwen3-8B baseline benchmark | Day 145 | Identity eval di Qwen3-8B vs Qwen2.5-7B documented | Trend #1 model upgrade gate |
| M10 | 3 paying clients | Day 165 | 3 license active + MRR ≥Rp 15jt | Phase D scale signal |
| M11 | Reward model serving | Day 175 | Qwen3-0.6B reward classifier handle 60% CAI workload | Trend #8 cost moat |
| M12 | Dream Cycle prototype | Day 180 | 1 successful counterfactual rollout cycle dengan PROMOTE | Innovation #4 unique moat |

---

## 7. DECISIONS LOCKED (don't reopen)

Setiap decision di bawah sudah punya doc parent. Jangan re-debate kecuali ada signal eksplisit dari user.

| Decision | Locked Day | Reference | TL;DR |
|----------|-----------|-----------|-------|
| Migan = standing alone brain, teacher = mentor offline | Day 52 | VISION_PRINCIPLES_LOCKED.md | No wrapper pattern, ever. |
| Qwen2.5-7B sampai Cycle 5+, Qwen3-8B Day 131+ | Day 60 | PRODUCT_BRIEF_ALIGNMENT.md K01 | Preserve training pair investment. |
| HTML/CSS/JS frontend untuk beta, Next.js Phase 3 | Day 60 | PRODUCT_BRIEF_ALIGNMENT.md K02 | No rebuild yet. |
| aaPanel untuk migancore.com VPS, Coolify untuk client template | Day 60 | PRODUCT_BRIEF_ALIGNMENT.md K03 | Different roles. |
| Self-learning loop = core differentiator, never stop | Day 60 | PRODUCT_BRIEF_ALIGNMENT.md K04 | Cycle pipeline runs through Phase D. |
| 9 prinsip non-negotiable (Zero Data Leak ... Trilingual) | Day 1 | brief (via PRODUCT_BRIEF_ALIGNMENT.md) | Brief menang vs dokumen lama. |
| ORPO `apo_zero` loss + APO identity λ | Day 42 | TRL Mar 2026 PR #87 | Hyperparams locked. |
| Vast.ai bukan RunPod | Day 49.7 | Lesson #62 | 5-9x cheaper, no allocation-billing trap. |
| dry_run=True wajib di setiap deploy script ke client | Day 67 | Lesson #141 | Anti-prod-disaster. |
| Single source of truth gate threshold | Day 67 | Lesson #140 | post_cycle6.sh constants block. |
| Default brain = Ollama (safe), llama-server speculative = opt-in `X-Inference-Engine` | Day 53 | DAY53_REVIEW_SYNTHESIS | KPI miss empirical, opt-in. |
| Episodic poisoning filter di MCP | Day 26 | v0.4.4 | Anti-injection guardrail. |

---

## 8. OPEN QUESTIONS (need user input)

Lima hal hanya Fahmi yang bisa jawab. Roadmap atas dibikin asumsi. Kalau salah asumsi, perlu re-plan.

### Q1 — Phase C client #1 source
Kita asumsi first paid client dari Tiranyx warm intro (UMKM segment). **Apakah Fahmi sudah punya 1-3 candidate concrete (nama bisnis), atau perlu lead generation Phase B juga?** Kalau yang kedua, Phase C harus geser +14-21 hari untuk include lead-gen sprint.

### Q2 — SIDIX data bridge ethical scope
1,458 training pairs di SIDIX adalah real conversation user. **Boleh kita import ke ADO training (anonymized) tanpa eksplisit consent dari SIDIX user dulu, atau perlu opt-in retroactif?** Ini decision privasi yang menyentuh prinsip P1 (Zero Data Leak).

### Q3 — Beta launch strategy pivot trigger
Kalau Day 75 feedback signals masih <10 setelah UI fix, kita pivot launch ke channel yang punya retention (SIDIX WA bridge user base). **Approve pre-emptive plan ini, atau Fahmi mau decide saat angka muncul?**

### Q4 — Pricing tier untuk first client
Brief target: PERAK Rp 5jt/bln. Tapi first client biasanya ada friend-discount atau pilot pricing. **Default pilot pricing 50% off (Rp 2.5jt/bln) untuk 3 bulan pertama, atau full price?** Impact ke break-even calc.

### Q5 — Qwen3-8B upgrade aggressiveness
K01 lock Qwen2.5 sampai Cycle 5+, dan kita sekarang Cycle 6. Kalau Cycle 6 PROMOTE Day 68, **boleh trigger Qwen3-8B benchmark Day 70 (parallel ke Phase A) atau strict tunggu Phase D Day 131?** Trade-off: parallel = early model upgrade benefit; serial = focus stabilization Phase A.

---

## APPENDIX — Document Map (referensi cepat)

```
Tier 0 (BACA WAJIB):
- VISION_PRINCIPLES_LOCKED.md       (5 prinsip, 5-check sanity)
- PRODUCT_BRIEF_ALIGNMENT.md        (9 prinsip + GAP-01..08)
- ROADMAP_DAY67_MASTER.md           (← dokumen ini)

Tier 1 (kontekstual saat planning):
- VISION_2026_2027_COGNITIVE_TRENDS.md (Day 65, 7 tren applied)
- VISION_DISTINCTIVENESS_2026.md       (Day 45, 3 moat + STOP/DD lists)
- ACHIEVEMENT_WRAP.md                  (Day 67, milestone-based memory)
- DAY67_MANDATORY_PROTOCOL.md          (Day 67 EOD state)

Tier 2 (referensi pas eksekusi):
- AGENT_ONBOARDING.md                  (lessons #1-144)
- ENVIRONMENT_MAP.md                   (VPS topology)
- ADO_KNOWLEDGE_RETURN_DESIGN.md       (Hafidz Ledger SQL)
- QWEN3_UPGRADE_PLAN.md                (Day 67 upgrade path)
- LICENSE_CRYPTO_ROADMAP.md            (Ed25519 air-gapped roadmap)

Tier 3 (historikal, audit only):
- DAY{N}_PROGRESS.md, DAY{N}_PLAN.md, DAY{N}_RETRO.md
```

---

*Dokumen ini ditulis Day 67+1 (2026-05-08) sebagai re-mapping pasca Cycle 6 trigger. Update berikutnya: Day 95 (Phase B exit gate) atau Day 130 (Phase C exit gate), whichever lebih informatif. Decision lock changes hanya dengan eksplisit user approval dan log entry di table di §7.*
