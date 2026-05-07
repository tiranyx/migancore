# CLAUDE PLAN — Day 70: Vision Elaboration + Cycle 7 + Letta Audit
**Date:** 2026-05-08 (WIB)
**Author:** Claude (Implementor)
**Status:** EXECUTING

---

## PROTOKOL DAY 70

**Disclaimer selesai dibaca:**
- `/opt/ado` = MiganCore (BUKAN sidix). Path konfirmasi: `cd /opt/ado && git remote -v → tiranyx/migancore`
- Lokal: `C:\migancore\migancore\` HEAD=`89b57cf`
- VPS: `/opt/ado` HEAD=`89b57cf` ← SELARAS ✅
- Live: `api.migancore.com` + `app.migancore.com` ← SELARAS ✅

---

## 1. CURRENT STATE SNAPSHOT (per Day 70 session start)

| Metric | Value | Status |
|--------|-------|--------|
| Production Brain | `migancore:0.3` Cycle 3, weighted_avg 0.9082 | STABLE |
| Cycle 6 | ROLLBACK — voice 0.705, tool-use 0.733, creative 0.771 | KNOWN |
| Feedback signals | 0 (fix deployed Day 69, not yet user-tested) | WATCH |
| DB preference_pairs | 3,046 | — |
| DB conversations | 68 · messages 181 · users 56 | — |
| DB kg_entities | 0 | RED FLAG |
| DB archival_memory | 0 | RED FLAG (Letta running, unwired) |
| Disk /opt | 126GB used / 388GB (33%) | OK |
| Ollama models | migancore:0.3, :0.6, qwen2.5:7b-instruct-q4_K_M, qwen2.5:0.5b | 14.7GB |
| Untracked files | KIMI_REVIEW_69_CYCLE6_AND_FEEDBACK.md | Commit today |

---

## 2. VISION ELABORATION — ADO 2026-2027

### 2A. Apa yang Telah Dibangun (Day 1–69)

MiganCore hari ini = **prototipe Cognitive Core** yang bisa:
- Bicara, ingat konteks dalam sesi, pakai 23 tools
- Belajar dari synthetic DPO/ORPO pairs (6 siklus)
- Diakses via MCP server, Smithery public registry
- Berjalan self-hosted, zero external data leak
- Punya license system (HMAC-SHA256)

Tapi ini masih **MVP lapisan pertama** dari ADO yang sebenarnya.

---

### 2B. Gap: MVP vs ADO Sesungguhnya

| Dimensi | MVP Hari Ini | ADO Sesungguhnya (Visi) |
|---------|-------------|------------------------|
| Memory | Single-session + Qdrant episodic (partial) | 4-tier: Working → Episodic → Semantic → Procedural (LoRA weights) |
| Learning | Periodic synthetic training + user feedback (0 signal) | Continuous: tiap interaksi → pair → training notif |
| Reasoning | ReAct loop (reactive) | Active Inference: minimize free energy, curiosity-driven |
| Causality | Tidak ada | Causal graph + do-calculus (counterfactual reasoning) |
| Identity | Persona via system prompt + LoRA jiwa | Cryptographic DID + Verifiable Credential per instance |
| Interoperability | MCP server (tool provider) | MCP server + A2A peer = bisa dipanggil agent lain sebagai "Brain" |
| Clone | Dry-run script | 1-click: Docker + license + persona → VPS client dalam 10 menit |
| Economy | Rp-based SaaS billing | x402 micropayment per inference call |

---

### 2C. Cognitive Trends 2026-2027 yang Relevan untuk MiganCore

**Trend 1: Cognitive Kernel-as-a-Service (CKaaS)**
Agen spesialis akan beli "brain" dari marketplace, bukan build sendiri.
MCP sudah 78% adopsi enterprise per April 2026 + 9,400+ public servers.
*Implikasi MiganCore:* Positioning ulang dari "AI chatbot per organisasi" ke
"Brain yang bisa disewa oleh agent lain." Ini yang riset sebut BaaS.
Window: 12-18 bulan sebelum hyperscaler tutup gap.

**Trend 2: Memory sebagai Moat Kompetitif**
Raw context window sudah komoditas. Yang menang: agent yang ingat LINTAS SESI.
Letta (ex-MemGPT): 3-tier OS-inspired memory. Benchmark +58% vs recursive summarization.
*Implikasi MiganCore:* Letta SUDAH running di VPS (`ado-letta-1`) tapi `archival_memory=0`.
Artinya: kita bayar infrastruktur tapi tidak dapat value. Ini harus diwire hari ini.

**Trend 3: Self-Evolving Skill Library**
Frontier 2026-2027: setiap task berhasil → distilled menjadi reusable skill module.
HKUDS OpenSpace, Meta Hyperagents (Olympiad math: 0.63 vs 0.0 baseline).
*Implikasi MiganCore:* Procedural layer (LoRA weights) adalah implementasi kita.
Tapi perlu pipeline: interaksi berhasil → ekstrak skill → masuk training pair → cycle berikutnya.
Ini adalah "ADO yang tumbuh dari pengalaman sendiri" — visi P1 brief.

**Trend 4: Reasoning Models Ubah Orkestrasi**
DeepSeek R1-0528: AIME accuracy 70% → 87.5%. 10-20x lebih murah dari o3.
Single reasoning model kadang lebih baik dari 3-5 specialist agents.
*Implikasi MiganCore:* Jangan terlalu banyak agent. Beri Qwen2.5-7B trained identity yang kuat +
reasoning capability. Kalau butuh reasoning berat: OpenRouter DeepSeek R1 sebagai "thinking backbone."

**Trend 5: Agentic Commerce via x402**
69,000 active agents + 165M transactions + $50M cumulative di Agent.market (April 2026).
Stripe sudah support x402 (Feb 2026).
*Implikasi MiganCore:* Fase 3 monetisasi bisa tanpa Stripe, tanpa KYC manual.
$0.005/inference call. Solo founder bisa setup wallet hari ini.

**Trend 6: Zero-Trust Agent Identity**
DID + VC (W3C) + ERC-8004 + SPIFFE = trio yang mendefinisikan trusted agent fabric 2027.
EU AI Act deadline penuh: 2 Agustus 2026.
*Implikasi MiganCore:* License HMAC-SHA256 yang ada = Phase 1 yang valid.
Ed25519 + DID = Phase 2 (roadmap Day 76-80 per CRYPTO_ROADMAP).
Ini bukan nice-to-have — ini gate untuk enterprise sales di regulated sectors.

**Trend 7: Indonesia 12-18 Bulan Arbitrage**
Google Cloud $350K credit program, Danantara $14B/tahun, BCG "rising contender."
Salesforce Agentforce sudah live Bahasa Indonesia — kompetisi datang.
*Implikasi MiganCore:* First mover advantage di Indonesia enterprise (hukum, keuangan, kesehatan)
dengan kombinasi: Bahasa Indonesia native + zero data leak + self-hosted = tidak bisa disamai
platform cloud asing. Window menutup 2027 Q4.

---

### 2D. Repositioning Strategis (tidak perlu pivot, ini refinement)

**Sebelum (hari ini positioning):** "AI organisme yang bisa di-clone per organisasi"
**Sesudah (2026-2027 positioning):** 
> "**Cognitive Kernel** — otak AI yang bisa disewa oleh organisasi lain sebagai brain untuk
> agent mereka. Self-hosted. Belajar sendiri. Lupa tidak pernah."

**Tiga moat yang harus dibangun berurutan:**

```
MOAT 1 (Day 70-90):   Memory ≠ context window
                       → 4-tier persistent memory via Letta
                       → archival_memory > 0 adalah KPI pertama

MOAT 2 (Day 90-130):  Learning dari interaksi nyata
                       → Feedback flywheel live (>10 signal/hari)
                       → training cycle dari real user pairs, bukan synthetic saja

MOAT 3 (Day 130-180): CKaaS exposure
                       → A2A Agent Card terdaftar
                       → x402 micropayment per inference
                       → ADO bisa dipanggil agent lain sebagai "brain"
```

---

## 3. DAY 70 SPRINT PLAN

### Objective
Unblock dua bottleneck yang paling mempengaruhi ADO sebagai learning organism:
1. **Voice recovery** via Cycle 7 dataset (training flywheel unblock)
2. **Cross-session memory** via Letta wire (memory moat Foundation)

### KPIs Day 70

| KPI | Target | Cara Ukur |
|-----|--------|-----------|
| Cycle 7 JSONL tersedia | ≥240 pairs, voice_anchor_v1:cycle7 source | `wc -l cycle7_dataset.jsonl` |
| Ollama stale cleanup | migancore:0.1, :0.4, :0.5 dihapus → -14GB | `ollama list` |
| Letta wiring audit | Tahu persis apa yang harus diwire | Read letta.py + routes |
| BUILD_DAY updated | "Day 70" di /health | curl api.migancore.com/health |
| Git align | lokal = VPS = GitHub HEAD | git log --oneline -1 |

### Blocks

| Block | Task | ETA | Owner |
|-------|------|-----|-------|
| B1 | Commit KIMI_REVIEW untracked + BUILD_DAY update | 30 min | Claude |
| B2 | Generate Cycle 7 dataset (260 pairs, Gemini) | 60-90 min | Claude |
| B3 | Cleanup stale Ollama models (-14GB) | 10 min | Claude |
| B4 | Letta audit: read letta.py + archival_memory wire design | 45 min | Claude |
| B5 | Deploy + smoke test | 20 min | Claude |
| B6 | Tracker update + lessons + CLAUDE_PLAN Kimi questions | 20 min | Claude |

### Pre-deploy Checklist (mandatory)
- [ ] `git status` clean
- [ ] `git diff --stat` reviewed
- [ ] No tests broken (API /ready = healthy)
- [ ] Deploy command written + verified
- [ ] Rollback plan documented
- [ ] VPS path confirmed: /opt/ado (not /opt/sidix or any other)

---

## 4. RESEARCH QUESTIONS FOR KIMI

1. **Letta 0.6.0 archival memory trigger:** Apa yang harus di-set di Letta SDK untuk agar `archival_memory` table (PostgreSQL) terisi? Apakah butuh explicit `save_to_archival=True` di setiap message, atau ada auto-trigger berdasarkan conversation length?

2. **Cycle 7 voice pair quality:** Berdasarkan Cycle 6 Q5 failure (score 0.438 untuk "Hai! Bagaimana kabarmu hari ini?"), apa pola CHOSEN yang paling efektif untuk voice identity dalam ORPO training? Apakah `informal + first-person pronoun + action offer` cukup, atau perlu tambahan elemen?

3. **Cognitive Kernel positioning:** Ada competitor Indonesia yang sudah positioning sebagai "Brain-as-a-Service" atau CKaaS? Atau market ini masih kosong sepenuhnya per Mei 2026?

4. **x402 + Indonesia:** Apakah ada regulatory blocker untuk menggunakan USDC on Base (blockchain payment) untuk B2B SaaS di Indonesia? Atau perlu fallback ke Stripe IDR?

---

## 5. QA QUESTIONS FOR CODEX

1. **Letta wiring security:** Ketika archival memory Letta diwire ke chat router, apakah ada risiko cross-tenant memory leak? (tenant isolation harus verified per user_id/agent_id)

2. **Cycle 7 generation script:** Apakah ada injection risk jika Gemini generated "chosen" response berisi adversarial instruction? (training pair poisoning)

3. **Ollama rm safety:** `ollama rm migancore:0.1 migancore:0.4 migancore:0.5` — apakah ada service yang masih reference ke model yang akan dihapus?

---

## 6. RISKS CLAUDE SEES

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Gemini API rate limit saat generate 260 pairs | Medium | Medium | Batch dengan sleep 2s, retry on 429 |
| Letta wire menyebabkan latency regression | Medium | High | Feature flag: env LETTA_ARCHIVAL_ENABLED=false default |
| Stale model ref setelah `ollama rm` | Low | Medium | Grep codebase untuk string "migancore:0.1" sebelum rm |

---

*Kimi: baca file ini, jawab Research Questions section 4.*
*Codex: baca file ini + KIMI_REVIEW ketika sudah ada, jawab QA Questions section 5.*
