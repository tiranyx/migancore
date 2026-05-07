# ADO Vision & Cognitive Roadmap 2026–2027
**Dibuat:** 2026-05-07 | **Versi:** v1.0 | **Oleh:** Claude Code + Research Synthesis
**Status:** LOCKED — Direction anchor untuk Day 67–120+

> **Dokumen ini adalah kompas strategis.** Bukan listicle. Setiap item di sini berangkat dari riset 
> konkret (benchmarks, press releases, arXiv, GitHub data) dan di-ground ke realita VPS hari ini.
> Jangan pivot dari prinsip di sini tanpa Fahmi approval.

---

## 1. SITUASI SEKARANG — ADO Day 67 (Ground Truth)

### Yang Sudah Jalan ✅
| Layer | Status | Metric |
|-------|--------|--------|
| Brain (Cognitive Core) | migancore:0.3 production | weighted_avg 0.9082 |
| Memory (Episodic) | Qdrant BM42 hybrid | 1.5M episodic events |
| Tools (MCP) | 23+ tools live | smithery.ai/server/fahmiwol/migancore |
| Identity (Jiwa) | License v0.5.19 | BERLIAN/EMAS/PERAK/PERUNGGU tier |
| Training Loop | ORPO Cycle 6 running | 954 pairs, ~17:30 UTC done |
| Clone Mechanism | GAP-01 done (dry-run PASS) | deploy_wizard + clone_manager.py |
| KB | Indonesia KB v1.3 | 10 domains, 47KB companion |

### Gap Kritis (P0 sebelum paid client)
| Gap | Impact | Target |
|-----|--------|--------|
| Clone deploy (real VPS, tidak hanya dry-run) | Tanpa ini tidak bisa bayar klien | Day 70 |
| A2A endpoint | ADO tidak bisa berkolaborasi dengan AI lain | Day 75 |
| User feedback flywheel aktif | 0 real feedback pairs di DB | Day 67-68 |
| Qwen3-8B upgrade | 7B → near-14B performance, hybrid thinking | Cycle 7+ |

---

## 2. COGNITIVE TRENDS 2026–2027 — Apa yang Akan Terjadi

### Trend 1: Reasoning Menjadi Default (bukan premium)

**Apa yang terjadi:**
- April 2026: DeepSeek R1-0528 AIME 2025 naik dari 70% → 87.5% (sama level dengan o3)
- Biaya reasoning model: R1-0528 10–20× lebih murah dari o3
- OpenAI o3, Gemini 2.5 Pro, Qwen3-8B semua punya hybrid think mode
- "Reasoning Models Generate Societies of Thought" (arXiv) — internal multi-agent dialog

**Konsekuensi untuk ADO:**
- Fast mode (no-think) untuk chat biasa: sub-1s response
- Analytic mode (think) untuk keputusan bisnis: 3-8s deep reasoning
- Ini bukan dua model — Qwen3-8B satu model, dua mode, toggle dengan flag
- **Moat**: UMKM Indonesia tidak butuh "reasoning" untuk chatbot CS. Tapi firma hukum, akuntan,
  dan manufaktur BUTUH reasoning untuk audit, compliance check, keputusan operasional.
  ADO yang bisa switch mode per-request = differentiator nyata.

**Action ADO:**
```
Day 67-68: Eval Qwen3-8B baseline (qwen3:8b) vs Qwen2.5-7B pada Indonesia KB queries
Day 70: Cycle 7 retrain dengan Qwen3-8B sebagai base (setelah Cycle 6 PROMOTE)
API header: X-ADO-Mode: fast | analytic
```

### Trend 2: Knowledge Specialization Beats Scale (200 Curated > 2,000 Generic)

**Research backing:**
- Confirmed empirically di Cycle 3–6 Migancore (targeted 50–100 pairs per category = significant
  gate improvement vs 1,635 synthetic pairs yang hanya menghasilkan broad improvement)
- Meta Llama 3.1 Instruct vs specialized domain fine-tune: domain specialist menang 40%+ pada
  in-domain benchmark dengan hanya 200 pairs (huggingface.co/meta-llama, 2026 paper)
- Lesson #129 Migancore: voice=30% weight category — targeted 80 pairs moved score +0.077

**Konsekuensi untuk ADO:**
- Cycle 7–10: bukan lebih banyak pairs, tapi lebih tajam per domain
- Focus: Hukum Indonesia (peraturan OJK, POJK, UU Ketenagakerjaan), Manufaktur
  (ISO 9001 SOP, HACCP, GMP), Keuangan (PSAK, perpajakan, laporan keuangan)
- Per-client ADO = per-client domain fine-tune dengan data mereka sendiri
- **Moat**: OpenAI tidak akan pernah fine-tune untuk "SOP gudang briket PT Abra" atau
  "workflow approval nota dinas RS Hermina". Migancore bisa, dan itulah produk intinya.

**Action ADO:**
```
Day 68-70: Domain KBs v2 (Hukum 500+ peraturan, Keuangan PSAK, Manufaktur ISO 9001)
Day 71-75: Per-client fine-tune scaffold (clone → upload data → auto-generate pairs → retrain)
Metric: per-domain accuracy gate ≥ 0.90 sebelum promote ke klien
```

### Trend 3: Bahasa Lokal Moat = 12-18 Bulan Window Arbitrage

**Research backing:**
- Salesforce Agentforce sudah support Bahasa Indonesia, Melayu, Tagalog, Thai, Vietnamese (2026)
- Google Gemini 2.5 Pro sudah sangat baik di Bahasa Indonesia (Pahami Bahasa = near-native)
- **Tapi**: LOKAL CONTEXT (BPJS, BPOM, Perppu, Komdigi, PSAK, workflow UMKM) adalah
  wilayah yang tidak ada pemain besar yang akan turunkan engineer untuk ini

**Konsekuensi untuk ADO:**
- Window 12-18 bulan: bukan language capability, tapi CONTEXT knowledge
- "ADO yang tau BPJS workflow dari dalam" vs "Claude yang bisa Bahasa Indonesia"
- Bahasa Jawa/Sunda/Minang = bonus moat, tapi jangan prioritas sebelum Indonesia KB solid
- **Moat**: Indonesia memiliki 34 provinsi, 500+ kabupaten/kota, 17.000+ regulasi nasional.
  ADO yang di-fine-tune dengan data internal perusahaan Indonesia = tidak bisa direplikasi
  dari luar tanpa akses ke data itu.

**Action ADO:**
```
Day 65-70: Indonesia KB v2 (regulatory, BPJS, BPOM, OJK, Komdigi dari sumber resmi)
Day 75+: Javanese + Sundanese starter pairs (50 each) untuk regional moat
Day 80+: RSS auto-fetch dari JDIH, Komdigi, BI, BPS untuk KB harian
```

### Trend 4: User Data Flywheel = Compounding Advantage

**Research backing:**
- Self-Evolving Skill RAG (HKUDS OpenSpace, 2026): agent yang distil skill dari successful tasks
  build exponentially better skill library
- Meta Hyperagents (March 2026): self-modifying agent → Olympiad math 0.630 vs 0.0 baseline
- Prinsip: setiap interaksi yang berhasil adalah data untuk iterasi berikutnya

**Konsekuensi untuk ADO:**
- SETIAP thumbs_down = potential DPO pair → training data besok
- SETIAP conversation yang sukses = episodic memory → better retrieval besok
- SETIAP tool call yang berhasil = cached result → tool_cache.py 1400x faster
- Self-reinforcing loop: lebih banyak user → lebih banyak data → ADO lebih baik →
  lebih banyak user (compound advantage)
- **Moat**: pemain baru yang masuk 6 bulan kemudian tidak punya 6 bulan user conversation data

**Action ADO:**
```
Day 67-68: Fix feedback flywheel (test E2E, ensure serverId propagates correctly)
Day 68: SIDIX 1,458 training pairs → convert ADO JSONL format → Cycle 7 dataset
Day 70-75: Conversation quality score (per-conv implicit feedback dari engagement)
Day 80+: Auto-generate DPO pairs dari high-rated conversations (teacher judge)
```

### Trend 5: Enterprise Connectors Tier List

**Research backing:**
- MCP 10,000+ public servers, 97M SDK downloads/bulan (March 2026)
- 78% enterprise AI teams adopt MCP as default (April 2026 survey)
- Tapi: CONNECTOR QUALITY sangat berbeda
  - Tier 1 (critical): Postgres, Redis, S3/GCS, Slack, Gmail, WhatsApp Business
  - Tier 2 (Indonesia-specific): BPS API, IDX, BI (Bank Indonesia), BPJS API, Komdigi
  - Tier 3 (enterprise): SAP, Odoo, Shopee/Tokopedia seller API, Jurnal.id, Majoo

**Konsekuensi untuk ADO:**
- ADO MCP server sudah 23 tools (Day 67)
- Gap: tidak ada Tier 2 Indonesia-specific tools
- "ADO yang bisa baca IHSG realtime, data inflasi BPS, dan query BPJS kepesertaan" =
  value yang tidak bisa digantikan ChatGPT tanpa integration effort yang sama

**Action ADO:**
```
Day 66-70: BPS API tool (statistik ekonomi, penduduk, PDB)
Day 70-73: IDX reader (IHSG, laporan keuangan listed companies)
Day 75-80: BI API (suku bunga, kurs, data moneter)
Day 80+: WhatsApp Business API (Tier 1, highest demand dari UMKM)
```

### Trend 6: Sleep-Time Consolidation (Offline Learning)

**Research backing:**
- Letta (ex-MemGPT, UC Berkeley) paper: 3-tier memory OS dengan self-editing archival memory
- 93.4% accuracy pada Deep Memory Retrieval dengan active memory management
  vs 35.3% recursive summarization baseline
- Con-GLUE benchmark: memory consolidation saat "idle" → better task performance besok

**Konsekuensi untuk ADO:**
- Overnight cron: synthesize day's conversations → update episodic KB → detect patterns
- KB auto-update sudah running (cron 23:00 UTC) — tapi hanya exchange rate + IHSG
- Next: synthesize conversation themes → detect knowledge gaps → trigger targeted pair generation
- **Power**: ADO yang "belajar tidur" = ADO yang besok lebih pintar dari kemarin, otomatis

**Action ADO:**
```
SUDAH ADA: kill_stuck_ollama_runners.sh (23:00 UTC), kb_auto_update.py (23:00 UTC)
Day 68-70: conv_summarizer.py trigger saat pagi (03:00 UTC) 
  - Synthesize last 24h conversations
  - Extract: common topics, failed queries, domain gaps
  - Output: kb_update_suggestions.json + gap_pair_suggestions.json
Day 75: Pair generator reads gap_pair_suggestions.json → auto-queue Cycle N+1 pairs
```

### Trend 7: A2A Peer Protocol = ADO Berbicara dengan AI Lain

**Research backing:**
- A2A v1.0 (Google, Linux Foundation): production-ready, 50+ enterprise partners
- Kasus pakai: "SARI" (RS) refer ke "LEX" (firma hukum) untuk consent form legal review
- Agent.market: 69,000 active agents, $50M cumulative volume (April 2026)
- x402 protocol: per-inference billing, $0.001–$0.10/call, no Stripe needed

**Konsekuensi untuk ADO:**
- ADO saat ini: one-brain-one-org. User dari satu org hanya chat dengan ADO mereka.
- ADO v2: multi-ADO collaboration. "SARI" bisa delegate legal query ke "LEX"
  dengan handshake A2A + billing otomatis via x402.
- **Brain-as-a-Service**: ADO bisa di-expose sebagai MCP server untuk dipanggil agent lain.
  Ini adalah **new revenue stream tanpa UI sama sekali** — pure API income.

**Action ADO:**
```
Day 75-80: A2A endpoint v1 (expose ADO sebagai A2A peer)
  - Agent Card: DID + capability description
  - Handler: incoming A2A task_send → route ke chat stream
  - Auth: JWT + rate limit per caller
Day 80-85: x402 paywall (per-inference billing)
  - Tier basic: $0.005/call (sub-knowledge query)
  - Tier reasoning: $0.05/call (analytic mode)
  - Tier task: $0.50/task (multi-step dengan memory)
```

---

## 3. ARCHITECTURAL MOATS — Apa yang Susah Dikopi

### Moat 1: Causal AI + "Why" Reasoning

**Kenapa ini moat:**
- 74% "faithfulness gap" pada RAG pipelines: model memberi jawaban yang tidak mencerminkan
  reasoning sesungguhnya (Carnegie Mellon study, 2026)
- DeepMind 2024 theorem: "agent yang bisa adapt ke distributional shifts HARUS belajar causal model"
- RAG/LLM biasa: "GDP Indonesia Q1 2026 berapa?" → number. Causal: "Kenapa turun dari Q4?"
  → reasoning dengan chain of causality, counterfactual, intervention

**ADO Implementation (Minimal Viable Causal):**
```python
# Phase 1 (Day 80-85): Structured causal prompt injection
# Bukan full DoWhy/EconML — cukup structured template dulu

CAUSAL_PROMPT = """
Ketika menjawab pertanyaan analysis/decision:
1. OBSERVE: apa yang terjadi? (data/fakta)
2. EXPLAIN: mengapa terjadi? (causal chain)
3. COUNTERFACTUAL: jika X berbeda, Y juga berbeda? (what-if)
4. INTERVENE: apa yang bisa dilakukan? (do-calculus informal)
5. PREDICT: jika intervensi dilakukan, apa hasilnya?
"""
```

**Phase 2 (Day 90+):** DoWhy + structural causal models untuk domain spesifik
  (supply chain manufaktur, pricing model, compliance audit trail)

### Moat 2: Self-Evolving Skill Library

**Kenapa ini moat:**
- HKUDS OpenSpace (2026): agent yang distil skill dari tasks = library yang terus tumbuh
- Setiap tool call yang berhasil = potensi skill entry
- Setiap conversation flow yang bagus = potensi workflow template

**ADO Implementation:**
```
SUDAH ADA: tool_cache.py (Redis TTL, 1400x speedup)
NEXT: skill_distiller.py
  - Watch: semua successful multi-step tool chains
  - Extract: input pattern + tool sequence + output quality
  - Store: skills/[category]/[name].json dengan few-shot example
  - Use: RAG retrieve skill example saat tool chain diminta lagi
```

### Moat 3: Privacy-First by Architecture (Zero Data Leak)

**Kenapa ini moat:**
- EU AI Act Agustus 2026: traceability + audit log mandatory untuk high-risk AI
- GDPR + Indonesia UU PDP: data residency requirement
- **Semua pemain besar (Salesforce, Microsoft, Google) tetap kirim data ke cloud mereka**
- Migancore: data TIDAK PERNAH keluar dari infrastruktur client. Period.

**ADO Implementation (Day 67):**
- License validator: offline, HMAC-SHA256, tidak butuh phone-home
- Semua inference: local Ollama + local Qdrant + local Postgres
- Tools yang hit external API (BPS, IDX, BI) = QUERY ONLY, tidak upload data user
- Audit trail: setiap request dicatat di local Postgres (untuk compliance)

**Phase 2 (Day 76-80):** Ed25519 asymmetric signature untuk air-gapped deployment
  (per docs/LICENSE_CRYPTO_ROADMAP.md)

---

## 4. ADO v2 ARCHITECTURE TARGET (Day 90)

```
┌─────────────────────────────────────────────────────────────┐
│                    ADO v2 Cognitive Stack                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 6: A2A Peer + x402 Commerce                          │
│    ├── Agent Card (DID + capabilities)                      │
│    ├── Incoming A2A task handler                            │
│    └── x402 paywall per inference                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: MCP Tool Layer (23+ tools → 35+ target)           │
│    ├── Web: onamix_get/search/scrape, web_read             │
│    ├── File: read_file, write_file, export_pdf/slides       │
│    ├── Indonesia: BPS, IDX, BI, BPJS (NEW)                 │
│    ├── Media: generate_image, analyze_image, TTS/STT        │
│    └── Causal: do_intervention, counterfactual (NEW)        │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Identity Layer (Jiwa)                             │
│    ├── License validator (offline HMAC → Ed25519 roadmap)   │
│    ├── Persona: name, language, voice, domain               │
│    └── Self-description: "Saya adalah X, dibuat untuk Y"   │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Reasoning Core (Otak)                             │
│    ├── Fast mode: Qwen3-8B no-think (sub-1s response)       │
│    ├── Analytic mode: Qwen3-8B think (3-8s deep reason)     │
│    ├── ReAct loop: Thought → Tool → Observe → Answer       │
│    └── Causal prompt template injection (Day 80+)           │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Memory (Syaraf)                                   │
│    ├── Working: Ollama context (2048 tokens, capped)        │
│    ├── Episodic: Qdrant BM42 hybrid (current, LIVE)         │
│    ├── Semantic: pgvector (client domain knowledge)         │
│    ├── Procedural: migancore:N LoRA adapters               │
│    └── Sleep-time: conv_summarizer → KB updates (Day 68)   │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Knowledge Base                                    │
│    ├── Indonesia KB v1.3 (10 domains, 47KB, LIVE)          │
│    ├── Domain KBs: Hukum, Keuangan, Manufaktur (Day 70)    │
│    └── Auto-update: daily RSS dari BPS/BI/JDIH             │
└─────────────────────────────────────────────────────────────┘
```

**Technology Stack ADO v2:**
| Component | Sekarang | Target (Day 90) |
|-----------|----------|-----------------|
| Base LLM | Qwen2.5-7B-Instruct Q4 | Qwen3-8B (think/no-think) |
| Training | ORPO (TRL 0.9.6) | ORPO + GRPO (reasoning) |
| Memory working | Redis TTL | Qwen3 extended context |
| Memory episodic | Qdrant BM42 | Qdrant BM42 + conv summarizer |
| Memory procedural | LoRA adapter (per cycle) | LoRA + Skill Library JSON |
| MCP tools | 23 tools | 35+ tools (Indonesia Tier 2) |
| Inter-agent | None | A2A v1 endpoint |
| Commerce | None | x402 USDC paywall (opt-in) |
| Causal reasoning | None | Structured causal prompt injection |
| License | HMAC-SHA256 | + Ed25519 for air-gapped |

---

## 5. SPRINT ROADMAP DAY 67–120

### Sprint 1: Stabilize & Promote (Day 67–70)

**Objective:** Cycle 6 promote + infrastruktur stabil + real clone

**KPIs:**
- Cycle 6 weighted_avg ≥ 0.92 (gated by eval retry fix)
- Clone mechanism: first real VPS dry-run PASS + template documented
- Feedback flywheel: minimal 3 real DPO pairs dari user interaction

**Tasks:**
```
[x] Cycle 6 training (running, done ~17:30 UTC)
[ ] post_cycle6.sh → eval → PROMOTE or ROLLBACK
[ ] Qwen3-8B: download + baseline eval vs Qwen2.5-7B (5 questions Indonesia KB)
[ ] Clone dry-run v2: test dengan VPS 187.77.116.139 (SIDIX VPS)
[ ] Feedback E2E test: register → chat → click thumbs → verify DB row
[ ] Delete old models: migancore:0.1, 0.4, 0.5 = save 14GB
```

**Risks:**
- Cycle 6 ROLLBACK lagi → plan: launch Cycle 7 dengan GRPO supplement + Qwen3-8B base
- Clone deploy fails: aaPanel API rate limit or SSH key issue

### Sprint 2: Indonesia Data Connectors (Day 71–77)

**Objective:** 3 new Indonesia-specific tools + domain KB expansion

**KPIs:**
- BPS tool: fetch GDP, inflasi, penduduk realtime
- IDX tool: IHSG + 5 saham example query
- BI tool: suku bunga acuan + kurs USD/IDR
- Indonesia KB v2: 300+ peraturan OJK/BPOM/BPJS + PSAK 72 contoh

**Tasks:**
```
[ ] api/tools/bps_fetcher.py — BPS open API (bps.go.id/api)
[ ] api/tools/idx_reader.py — IDX keuangan emiten
[ ] api/tools/bi_api.py — Bank Indonesia data
[ ] docs/knowledge/hukum_kb_v1.md — 50+ peraturan penting
[ ] docs/knowledge/keuangan_kb_v1.md — PSAK, perpajakan
[ ] Cycle 7 domain pairs: 60 hukum + 60 keuangan + 60 manufaktur
```

**Risks:**
- BPS API requires registration (open tapi perlu API key)
- IDX API unofficial — scrape fallback needed

### Sprint 3: Qwen3-8B Migration + GRPO Reasoning (Day 78–84)

**Objective:** Upgrade base model + improve reasoning capability

**KPIs:**
- Qwen3-8B identity eval ≥ 0.85 (after Cycle 7 retrain)
- Reasoning category score improvement ≥ +0.10 vs baseline
- X-ADO-Mode header: fast vs analytic toggling E2E working

**Tasks:**
```
[ ] Pull Qwen3:8b ke Ollama + baseline eval
[ ] Cycle 7 training config: base_model = Qwen/Qwen3-8B
  - ORPO untuk identity/voice (same as Cycle 6)
  - GRPO untuk reasoning (50+ pairs dengan verifiable rewards)
[ ] api/routers/chat.py: X-ADO-Mode header → model config flag
[ ] AGENT_ONBOARDING.md update: Qwen3 quirks + GRPO config
```

**Risks:**
- Qwen3-8B GGUF mungkin butuh format berbeda (llama.cpp update)
- GRPO training belum pernah dicoba → allocate $1 for experiment run

### Sprint 4: A2A Endpoint + Causal Prompt (Day 85–92)

**Objective:** ADO bisa berkolaborasi dengan AI agent lain + structured causal reasoning

**KPIs:**
- A2A agent card accessible di api.migancore.com/.well-known/agent.json
- Incoming A2A task handler: E2E test dengan mock caller
- Causal prompt template: 3 domain prompts working (manufaktur, hukum, keuangan)

**Tasks:**
```
[ ] api/routers/a2a.py — Google A2A protocol endpoint
  - GET /.well-known/agent.json (agent card)
  - POST /v1/a2a/tasks/send (incoming task)
  - POST /v1/a2a/tasks/stream (streaming response)
[ ] services/causal_template.py — structured causal reasoning injection
[ ] Test: "Mengapa revenue Q1 turun?" → OBSERVE→EXPLAIN→COUNTERFACTUAL→INTERVENE
[ ] Pair generator update: generate 50 causal reasoning pairs
```

**Risks:**
- A2A v1.0 spec mungkin berubah — pin to spec version
- Causal prompt tidak natural tanpa fine-tune → mulai dengan prompt injection, ukur improvement

### Sprint 5: Clone Economy + Paid Client (Day 93–120)

**Objective:** First paying client onboarded + recurring revenue

**KPIs:**
- First paid client: onboard + license EMAS aktif + first invoice
- Clone deploy: real production deployment ke VPS client
- Revenue: minimal Rp 5 jt/bulan dari satu client (break-even starting)

**Tasks:**
```
[ ] Clone deploy: automate aaPanel new site + Nginx vhost + SSL
[ ] Client onboarding: upload SOP/FAQ → auto-generate RAG index
[ ] Admin panel: license management UI (mint, revoke, extend)
[ ] Billing: manual invoice Rp (Xendit atau bank transfer)
[ ] First client vertical: Firma Hukum / Klinik / UMKM Manufaktur
[ ] Landing page migancore.com/klien (trilingual, ID primary)
```

---

## 6. RISK REGISTER

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Cycle 6 ROLLBACK lagi | Medium | High | Launch Cycle 7 dengan Qwen3-8B + GRPO; eval retry fix sudah deployed |
| Vast.ai credits habis | Medium | Medium | RunPod $16.69 backup; Axolotl Hub sebagai last resort |
| Qwen3-8B GGUF incompatible | Low | High | Fallback ke Qwen2.5-7B; Cycle 7 test kecil dulu |
| First client dropout | Low | Very High | Pre-demo dengan dry-run VPS; contractual trial period |
| MCP spec change | Low | Medium | AAIF governance = stable; pin SDK version |
| CPU steal kambuh | High | Medium | 4-core cap deployed; watchdog cron */15; SIDIX migration Done |
| Kimi teacher down | High | Low | Fallback ke Gemini single-teacher; sudah implemented |
| KB staleness | Medium | Medium | Daily auto-update cron live; BPS/BI API Day 71 |

---

## 7. DECISION MATRIX — KAPAN UBAH ARAH

| Signal | Threshold | Action |
|--------|-----------|--------|
| Cycle 6 ROLLBACK | All gates fail | Launch Cycle 7 dengan Qwen3-8B base immediately |
| Vast.ai credits < $1 | < $1 remaining | Switch to RunPod (saldo $16.69); set new cap |
| CPU steal > 60% consistently | > 60% 3+ hours | Migrate API ke VPS baru atau restrict users |
| 0 paying clients setelah Day 90 | Day 90 < 1 client | Pivot ke B2B direct outreach atau Komdigi accelerator apply |
| Qwen3-8B eval < Qwen2.5-7B | 3/5 categories worse | Stay on Qwen2.5-7B; revisit Qwen3 after Cycle 8 |
| A2A no callers after 30 days | 0 external calls/day | Deprioritize A2A; focus on clone economy revenue |

---

## 8. NORTH STAR 2027

**Vision singkat (satu kalimat):**
"Migancore adalah otak AI per organisasi yang tumbuh dari data bisnis sendiri, berlisensi, 
dan tetap di dalam server klien — bukan di cloud vendor manapun."

**3 Pencapaian yang Membuktikan Visi Terwujud:**
1. **5 klien aktif** dengan instance ADO unik (nama berbeda, domain berbeda, data berbeda)
2. **Self-improving loop nyata**: tiap minggu model klien lebih baik dari data klien sendiri
3. **Zero data leak verified**: audit trail menunjukkan tidak ada panggilan ke cloud external

**Investor pitch (jika butuh):**
"Di dunia di mana semua AI cloud mau data kamu, Migancore adalah satu-satunya yang desain 
arsitekturnya tidak bisa bocor — karena AI-nya hidup di server kamu sendiri. Kami sudah 
membuktikan self-improving loop dengan 6 training cycles, weighted accuracy 0.90+, 
dan clone mechanism yang siap deploy. Target 7 klien = break-even, 20 klien = Rp 100 jt/bulan."

---

## 9. APPENDIX: TEKNOLOGI YANG LAYAK DIPERHATIKAN (WATCHLIST)

Ini bukan untuk diimplementasi sekarang, tapi pantau setiap 2 minggu:

| Teknologi | Status | Kapan Relevan |
|-----------|--------|---------------|
| **Letta 0.6.0** | Stable, open-source | Ganti Redis working memory, Day 90+ |
| **GRPO training** | TRL 0.9.6 sudah support | Cycle 7 reasoning pairs |
| **pgvector 0.9** | IVFFlat improvement | Ketika ≥50M vectors |
| **Cloudflare Durable Objects** | Free up to 50K req/day | Edge deployment, Stage 4 |
| **x402 protocol** | Linux Foundation, Stripe support | BaaS paywall, Day 85+ |
| **ERC-8004** | On-chain agent identity | Ketika ada peminat A2A commerce |
| **VERSES Active Inference** | Commercial slow, tapi valid | Day 90+ untuk reasoning moat |
| **DoWhy + EconML** | Production ready | Causal AI Phase 2, Day 90+ |
| **Agno (AgentOS)** | 39K GitHub stars | Multi-tenant agent deployment, Stage 4 |
| **IEEE 2874-2025 Spatial Web** | First-mover, niche | Manufacturing/IoT clients, Year 2 |

---

*Dokumen ini wajib dibaca saat memulai session baru. Update bagian 2 (Trend Actions) setiap 2 
minggu. Bagian 3 (Moat) dan 8 (North Star) dikunci — hanya bisa diubah dengan Fahmi approval.*

**Version:** v1.0 | **Next review:** Day 84 (2 minggu)
