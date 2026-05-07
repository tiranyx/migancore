# DAY 67 — MIGANCORE STRATEGIC PLAN & VISION ELABORATION
**Tanggal:** 2026-05-07  
**Implementor:** Claude Code (main), Kimi (review/strategy), Codex (QA)  
**VPS Hostname:** mix.migancore.com (72.62.125.6)  
**Status Training:** Cycle 6 ORPO — LIVE (14:02 UTC, ETA selesai ~14:35)

---

## MANDATORY LOG — STATUS HARI INI

### Yang Sudah Selesai (Day 67 pagi)
1. ✅ VPS Migration: 10/15 domain live di VPS baru (187.77.116.139)
2. ✅ SSL certbot: tiranyx.co.id, sidixlab.com, galantara.io, app.sidixlab.com, ctrl.sidixlab.com
3. ✅ Cycle 6 training LAUNCHED: 954 pairs, Q RTX 8000 @ $0.255/hr, Vast.ai instance 36295755
4. ✅ cycle6_orpo_vast.py committed: d2e0cb1
5. ✅ Duplicate instance (36295765) — killed + deleted dalam 2 menit (cost: $0)
6. ⏳ revolusitani.com + abrabriket.com — DNS belum propagasi

### Temuan Kritis Hari Ini
- **Cycle 5 ROLLBACK bukan karena model buruk** — 3 Ollama HTTP 500 (CPU steal 65%) = -0.099 weighted_avg. Estimated true score tanpa error: ~0.944 → PASS. Infrastruktur issue, bukan model issue.
- **Eval JSON says PROMOTE (threshold 0.8), promote_cycle5.sh says ROLLBACK (threshold 0.92)** — mismatch antara script gate. Lesson: single source of truth untuk gate definition.
- **Cycle 6 supplement 312 pairs ada tapi 75% dedup** dengan existing C2 pairs. Real unique supplement: 77 pairs. Root cause: similar prompts antara cycle6 supplement dan cycle2 curated.
- **Monitor task (b3g0zjrrh) captured PROMOTE dari re-run** tapi menggunakan threshold berbeda.

### Lesson Learns Hari Ini (#138-140)
- **#138**: Sebelum launch training, selalu `ps aux | grep [script]` — nohup bisa fork dua proses jika stdout buffer penuh. Selalu cek count proses setelah 5 detik.
- **#139**: Duplicate Vast.ai instances bisa terjadi dari duplicate script launch. Rule: launch → ps aux verify count=1 → proceed. Kill duplicate dalam <5 menit = $0 wasted.
- **#140**: Gate threshold harus ada di SATU tempat (config.py atau gates.json), dibaca oleh SEMUA scripts (eval, promote, monitoring). Mismatch threshold = false rollback atau false promote.

---

## VISION ELABORATION — ADO 2026-2027

### Visi Inti (dari Brief)
Migancore membangun **ADO (Autonomous Digital Organism)** — otak AI per organisasi yang:
- Self-hosted di infrastruktur client
- Zero data leak by architecture
- White-label + licensed Migancore × Tiranyx
- Modular clone: 1 base → banyak instance unik
- Retrain dengan data bisnis + flow bisnis client

### Apa yang Terjadi di Landscape 2025-2026

**5 Temuan Kritis dari Research:**

#### 1. Qwen3-8B Mengubah Kalkulasi
Qwen3-8B (April 2026, Apache 2.0) beats Qwen2.5-14B pada >50% benchmarks.  
**Implikasi untuk Migancore:**
- Upgrade Qwen2.5-7B → Qwen3-8B = near-14B performance di hardware yang sama
- **Hybrid thinking mode**: togglable reasoning (think) vs fast response (no-think) dalam 1 model
- Ini adalah **product differentiator**: client demo mode (fast) vs analytic mode (reasoning)
- Target: Cycle 7+ atau setelah Cycle 6 PROMOTE

#### 2. ORPO Tetap Optimal, Tapi GRPO Untuk Reasoning
- ORPO: terbaik untuk persona/voice/identity training (confirmed, sudah pakai)
- GRPO: terbaik untuk reasoning/code tasks dengan verifiable rewards
- SimPO: terbaik untuk broad alignment (+6.4 pts AlpacaEval vs DPO)
- **Action:** Cycle 8+ eksperimen GRPO untuk reasoning category (skor 0.500 di Cycle 5)

#### 3. MCP + A2A = Protocol Stack 2026
- MCP: 10,000+ servers, 97M SDK downloads/bulan, OpenAI + Microsoft adopted
- A2A v1.0: production-ready, Linux Foundation, 50+ enterprise partners
- **Migancore sudah correct**: MCP gateway live sejak Day 26
- **Gap**: A2A endpoint = multi-ADO orchestration ("SARI" refer ke "LEX" untuk legal advice)

#### 4. 200 Curated > 2,000 Scraped
Research 2026 confirms: 200 high-quality domain-curated examples beats 2,000 scraped.  
**Ini validasi arsitektur training Migancore** (targeted pairs per category, bukan bulk generation).  
**Action:** Stop generating >60 pairs per category per cycle. Focus pada QUALITY:
- Verify pairs dengan Gemini "as judge" sebelum masuk DB
- Set max 60 pairs per source per cycle

#### 5. Indonesia Agentic AI Forum June 2026 — Market Timing
Event pertama dedicated agentic/autonomous AI enterprise di Indonesia, Jakarta, 10 Juni 2026.  
**Implikasi:** Window 5 minggu sebelum event untuk siapkan demo + deck + first client.  
**Target**: Clone mechanism (GAP-01) ready sebelum 1 Juni = bisa demo live.

---

## GAP ANALYSIS — Brief vs Realita Day 67

| Komponen Brief | Status | Gap | Priority |
|---|---|---|---|
| Self-hosted ADO deployment | ✅ Live | — | — |
| Cognitive Core (reasoning) | ⚠️ Partial | Reasoning score 0.500 | P1 |
| MCP Integration | ✅ Live | — | — |
| Memory pipeline (episodic+semantic) | ✅ Live | — | — |
| License system | ✅ Live (Day 62) | Ed25519 upgrade roadmap | P3 |
| Clone mechanism | ❌ GAP-01 | Tidak ada | P0 |
| White-label identity | ⚠️ Partial | ADO_DISPLAY_NAME ada, UI belum | P1 |
| Business data training (RAG) | ✅ Qdrant live | No client-facing UI | P2 |
| Business flow training | ❌ | Tidak ada | P2 |
| Trilingual (ID/EN/ZH) | ⚠️ Partial | ZH tidak ada | P2 |
| ADO Builder UI | ❌ | Tidak ada | P2 |
| Deploy wizard | ❌ | Tidak ada | P1 |
| Billing system | ❌ | Tidak ada | P3 |
| Marketplace | ❌ | Tidak ada | P4 |
| Qwen3-8B upgrade | ❌ | Masih Qwen2.5-7B | P1 |
| A2A endpoint | ❌ | MCP ada, A2A belum | P2 |

**P0 = Blocker untuk first client**
**P1 = Harus ada sebelum proper demo**
**P2 = Nice to have, dapat bersamaan**
**P3 = Post-revenue**

---

## ARCHITECTURE TARGET — ADO v2 (2026-2027)

```
[Migancore Platform — mix.migancore.com]
│
├── ADO Builder (P2)          → konfigurasi persona, domain, tools
├── Clone Manager (P0/GAP-01) → 1-click: VPS detect → Docker deploy → license inject
├── Training Interface (P2)   → upload SOP/FAQ → chunk → embed → Qdrant RAG
├── License System (✅)        → HMAC-SHA256, BERLIAN/EMAS/PERAK/PERUNGGU tier
│
[Per-Org ADO Instance — di VPS client]
├── Identity Layer (Jiwa)     → ADO_DISPLAY_NAME, persona, language, soul.md
├── Memory Layer (Syaraf)     → Qdrant (episodic + semantic), Redis (session)
├── Cognitive Core (Otak)     → Qwen3-8B + ORPO adapter + GRPO reasoning
├── Tool Layer                → MCP tools (23 tools), A2A delegation
└── Privacy Vault             → zero external call, AES-256, license validator

[Protocol Stack 2026]
├── MCP (tools) → api.migancore.com/mcp/ ✅
├── A2A (agents) → api.migancore.com/a2a/ ← target Day 76-80
└── License API → api.migancore.com/v1/license/ ✅
```

---

## DAY 67 SPRINT PLAN — Prioritas Hari Ini

### Ongoing (background, jangan disentuh)
- [x] Cycle 6 training — Vast.ai, ETA 14:35 UTC
- [x] DNS propagasi revolusitani.com + abrabriket.com

### P0 — Clone Mechanism Foundation
Ini adalah blocker untuk first client. Tanpa ini, Migancore tidak bisa di-"jual".

**Target hari ini:** Buat `clone_manager.py` — struktur dasar yang:
1. Detect VPS spec client (RAM, CPU, disk)
2. Generate docker-compose.yml per-client dari template
3. Inject license file ke dalam compose env
4. SSH ke VPS client dan deploy

**File yang akan dibuat:**
- `api/services/clone_manager.py`
- `api/routers/admin.py` → tambah `/v1/admin/clone` endpoint
- `docker/ado-instance/docker-compose.template.yml`
- `scripts/clone_ado.sh`

### P1 — Qwen3-8B Upgrade Plan
Buat migration plan + Modelfile untuk Qwen3-8B deployment di Ollama.  
**Bukan hari ini** — tunggu Cycle 6 PROMOTE dulu. Tapi buat plan dan test command.

### P1 — Deploy Wizard Draft
Minimal: bash script yang bisa di-copy-paste oleh client IT staff untuk:
1. Install Docker + Docker Compose di Ubuntu 22.04
2. Clone ADO template
3. Isi .env dari template
4. Jalankan docker compose up

**File:** `scripts/setup_new_ado.sh`

### AFTER TRAINING (14:35 UTC)
1. Cek training log → GGUF convert → Ollama register migancore:0.6
2. Run eval WITH retry logic
3. PROMOTE atau ROLLBACK based on gates
4. Push git + update memory

---

## BENCHMARKS & KPIs — Day 67-70

| KPI | Baseline (Day 66) | Target (Day 70) | Method |
|---|---|---|---|
| Brain eval weighted_avg | 0.8453 (C5, faulty) | ≥ 0.92 (C6) | run_identity_eval.py |
| Tool-use score | 0.7439 | ≥ 0.85 | eval Q9+Q10 |
| Creative score | 0.7278 | ≥ 0.80 | eval Q13+Q14 |
| Evo-aware score | 0.7502 | ≥ 0.80 | eval Q20 |
| Clone mechanism | Not exist | v0.1 working | manual test |
| Deploy wizard | Not exist | Script tested | SSH to fresh VPS |
| First client demo | Not ready | Demo-ready | Fahmi confirm |

---

## RISK REGISTER

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Cycle 6 ROLLBACK again | Medium | Medium | eval retry (Lesson #137), migration cleanup sebelum eval |
| Training cost overrun | Low | Low | $5 cap, Q RTX 8000 @ $0.255/hr = ~$0.25 total |
| Clone mechanism complexity | High | High | Start minimal: bash script only, Docker template |
| Qwen3-8B OOM di VPS lama | Medium | Medium | Qwen3 quant Q4_K_M = 4.8GB, sama dengan Qwen2.5 |
| DNS revolusitani/abra delay | Low | Low | Certbot setelah propagasi, tidak blocker |

---

## ADAPTATION PLAN — Berdasarkan Research

### Stop Doing
- Bulk synthetic generation (>60 pairs/source/cycle) → quality beats quantity
- Running eval tanpa retry → Lesson #137 mandatory
- Multiple training script launch tanpa PID check → Lesson #138

### Start Doing
- **GRPO untuk reasoning** — Cycle 8+ (fix reasoning score 0.500)
- **Clone mechanism** — P0 untuk first client
- **Qwen3-8B migration** — Cycle 7+ (after Cycle 6 promote)
- **A2A endpoint** — Day 76-80
- **Pair quality gate** — Gemini-as-judge sebelum DB insert

### Continue Doing
- ORPO untuk persona/identity/voice training ✅
- Targeted supplement per failed category ✅
- Vast.ai untuk GPU training ✅
- MCP gateway ✅
- Dual SSH key auth ✅

---

## COMMIT PLAN DAY 67

| Commit | Content |
|---|---|
| `feat(clone): clone_manager.py foundation` | Clone service + admin endpoint |
| `feat(clone): docker ado-instance template` | Docker template per-client |
| `feat(clone): setup_new_ado.sh deploy wizard` | Bash deploy script |
| `docs(day67): strategic plan + vision elaboration` | Dokumen ini |
| `feat(cycle6): promote/rollback script post-eval` | Setelah training selesai |

---

## CATATAN UNTUK AGENT SELANJUTNYA (Day 68 handoff)

1. **Cycle 6 eval** — jalankan dengan `--retry 3` flag
2. **PROMOTE gate**: tool-use≥0.85, creative≥0.80, evo-aware≥0.80, weighted≥0.92, identity≥0.90, voice≥0.85
3. **Jika PROMOTE**: update DEFAULT_MODEL ke migancore:0.6, commit, push, restart API
4. **Jika ROLLBACK**: analyze failed cats, plan Cycle 7 dengan GRPO untuk reasoning
5. **Clone mechanism** — lanjutkan dari file yang dibuat hari ini
6. **revolusitani.com + abrabriket.com** — certbot setelah DNS propagasi (user confirm)
7. **Qwen3-8B** — research Modelfile format untuk Qwen3 GGUF di Ollama

*Dibuat: Claude Code Day 67, 2026-05-07*
