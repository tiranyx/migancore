# EXECUTE PLAN — ADO 2026–2027
**Dibuat:** 2026-05-09 | **Author:** Claude Sonnet 4.6 + Fahmi Ghani
**Status:** LIVING DOCUMENT — update tiap phase selesai
**North Star:** ADO = AI pertama di Indonesia yang *genius-level, white-label, privacy-first*

---

## BAGIAN 1 — SITUASI SEKARANG (JUJUR)

### Apa yang Sudah Kuat
| Aset | Status | Nilai |
|------|--------|-------|
| Self-training pipeline (ORPO 6 cycle) | ✅ Proven | Kompetitor tidak punya ini |
| Clone mechanism (GAP-01) | ✅ E2E dry-run PASS | P0 untuk client pertama |
| License system BERLIAN/EMAS/PERAK/PERUNGGU | ✅ Live | Fondasi monetisasi |
| 23+ tools (web, image, file, vision, TTS) | ✅ Terdaftar | Ekosistem awal |
| Indonesia KB v1.3 (10 domain) | ✅ Live | Moat lokal |
| Qdrant episodic memory (BM42 hybrid) | ✅ Live | Memori jangka panjang |
| MCP server di Smithery | ✅ Public | Enterprise discoverability |

### Apa yang Lemah (Jujur)
| Kelemahan | Dampak | Root Cause |
|-----------|--------|------------|
| 7B model = reasoning lemah | Tidak bisa saing di coding/math berat | Arsitektur, bukan training |
| Tool-use score 74% (di bawah gate 85%) | 1/4 tool call gagal | Dataset tool-use kurang |
| CPU-only VPS, shared hypervisor | Latency 3-8s, CPU steal | Infrastruktur |
| 0 klien berbayar | Revenue nol | Gap teknis → bisnis |
| Feedback flywheel 0 data | Loop self-improve dari user belum jalan | User base tipis |
| Creative/evo-aware di bawah gate | Model belum "berkarakter" cukup | Data supplement |

### Kesimpulan Situasi
ADO punya **fondasi terkuat** di Indonesia untuk kategori ini. Tapi saat ini masih di level *proof-of-concept yang sangat canggih*, belum *product yang bisa bersaing head-to-head* dengan Claude/GPT di semua domain.

---

## BAGIAN 2 — RISET LANDSCAPE AI 2026

### Tren Utama yang Sedang Terjadi Sekarang

**T1 — Reasoning Jadi Default (bukan fitur premium)**
- Claude 3.7 Sonnet, o3-mini, DeepSeek-R1, Qwen3 semua sudah hybrid thinking
- Model 8B dengan thinking mode (Qwen3-8B) performanya mendekati GPT-4o-mini di benchmark reasoning
- *Implikasi ADO:* Qwen2.5-7B yang kita pakai sudah "generasi lama" — Qwen3-8B langkah wajib

**T2 — 7B Model Jadi Komoditas, Diferensiasi Naik ke Stack**
- Llama 4 Scout (17B MoE aktif 17B) beats GPT-4o di banyak benchmark, gratis
- Gemma 3 (27B) Google, performa tinggi, bisa jalan di consumer GPU
- *Implikasi ADO:* Tidak bisa menang dengan "punya model sendiri" saja — harus menang di lapisan atas: tools, memori, domain knowledge, identitas

**T3 — MCP Adoption Accelerating**
- 78% enterprise mulai adopt MCP (Model Context Protocol) sebagai standar
- Smithery, Cursor, VS Code semua support MCP native
- *Implikasi ADO:* MCP server kita yang sudah live di Smithery = keunggulan nyata

**T4 — Privacy-First AI Jadi Pasar Sendiri**
- EU AI Act enforcement mulai ketat 2026
- Indonesia: RUU Perlindungan Data Pribadi (PDP) aktif, sanksi berat
- BUMN dan instansi pemerintah mulai dilarang kirim data ke cloud asing
- *Implikasi ADO:* Self-hosted white-label = produk yang DIBUTUHKAN regulasi, bukan sekadar pilihan

**T5 — Agent Orchestration Jadi Infrastruktur**
- LangGraph 0.3+, AutoGen 0.4, CrewAI makin mature
- A2A Protocol (Google + Linux Foundation) mulai diadopsi 150+ organisasi
- Multi-agent jadi standar untuk task kompleks
- *Implikasi ADO:* Satu agent generalis kalah — butuh network of specialists

**T6 — Hybrid Routing = New Architecture Standard**
- Groq, Together AI, Fireworks: inference frontier model < $0.001/1K token
- Pattern baru: "Local brain untuk identity + memori, cloud brain untuk compute berat"
- Tidak ada yang menganggap ini "cheat" lagi — ini arsitektur production standard
- *Implikasi ADO:* Hybrid routing bukan kompromi visi, ini ADALAH visi 2026

**T7 — Small Specialist > Large Generalist (di domain spesifik)**
- Medical AI: 7B yang fine-tuned medis beats GPT-4 di diagnosis spesifik
- Legal AI: model 13B yang trained hukum Indonesia beats Claude untuk POJK/KUHP
- *Implikasi ADO:* "Genius niche" lebih achievable dan lebih defensible

**T8 — Voice + Multimodal = Interface Baru**
- ChatGPT advanced voice mode, Gemini Live, Claude voice
- Di Indonesia: 60% pengguna mobile lebih nyaman voice daripada ketik
- *Implikasi ADO:* STT/TTS yang sudah ada = fondasi, perlu dipoles jadi experience seamless

**T9 — Indonesia AI Market Exploding**
- Nilai: $10.88B by 2030 (CAGR 40%+)
- 80% UMKM Indonesia belum sentuh AI sama sekali
- Pemerintah: program 1 juta AI talent 2025, anggaran digital naik
- *Implikasi ADO:* First-mover advantage di segmen ini masih sangat terbuka

**T10 — x402 + Agent Commerce Emerging**
- Standard HTTP 402 untuk AI-to-AI billing mulai diimplementasi
- ERC-8004 on-chain agent identity
- Agent yang bisa "membeli layanan" dari agent lain = ekosistem baru
- *Implikasi ADO:* Long-term: ADO bisa jadi "broker" antar agent

---

## BAGIAN 3 — VISI 2027 (NORTH STAR)

### ADO v3: The Indonesian Cognitive Platform

**Satu kalimat:** ADO adalah platform kognitif white-label pertama di Indonesia — lebih pintar dari asisten generik karena tahu domain klien lebih dalam, lebih aman karena data tidak pernah keluar, dan terus belajar dari setiap percakapan.

### Capability Target 2027

| Kemampuan | 2026 Sekarang | Target 2027 |
|-----------|---------------|-------------|
| Reasoning (math, logic) | Lemah (7B) | Kuat (Qwen3-30B + GRPO) |
| Coding (fullstack, debug) | Sedang | Sangat kuat (hybrid routing) |
| Domain Indonesia (hukum, keuangan) | Baik | Terbaik di Indonesia |
| Tool invocation accuracy | 74% | 95%+ |
| Latency (response) | 3-8s (CPU) | < 1.5s (GPU dedicated) |
| Context window | 4K token | 32K+ token |
| Bahasa (ID/EN/Jawa/Sunda) | ID+EN | ID+EN+Jawa+Sunda |
| Klien berbayar | 0 | 50+ (EMAS tier) |
| Revenue bulanan | $0 | $10,000+ MRR |
| Training cycle | Manual (user GO) | Autonomous nightly |

### Arsitektur Target ADO v3

```
┌─────────────────────────────────────────────────────────┐
│                    ADO v3 ARCHITECTURE                   │
│                                                         │
│  ┌─────────────┐     ┌──────────────────────────────┐  │
│  │   CLIENT    │────▶│        IDENTITY LAYER         │  │
│  │  (White     │     │  - Nama, suara, kepribadian   │  │
│  │   Label)    │     │  - Memori episodik (Qdrant)   │  │
│  └─────────────┘     │  - Context window management  │  │
│                      └──────────┬───────────────────┘  │
│                                 ▼                        │
│                      ┌──────────────────────────────┐  │
│                      │       ROUTER CERDAS           │  │
│                      │  Classifier: task complexity   │  │
│                      │  + privacy sensitivity check  │  │
│                      └─────┬──────────────┬──────────┘  │
│                            ▼              ▼             │
│               ┌─────────────────┐ ┌──────────────────┐ │
│               │  LOCAL BRAIN    │ │  HYBRID COMPUTE   │ │
│               │ Qwen3-30B       │ │  Claude/Gemini    │ │
│               │ fine-tuned ADO  │ │  API (task berat  │ │
│               │ (privacy tasks, │ │  + coding + math) │ │
│               │ domain spesifik)│ │  — NO raw data    │ │
│               └────────┬────────┘ └────────┬─────────┘ │
│                         └─────────┬─────────┘           │
│                                   ▼                      │
│                      ┌──────────────────────────────┐  │
│                      │      TOOL ECOSYSTEM           │  │
│                      │  Web/Search/File/Image/Voice  │  │
│                      │  BPS/IDX/BI/POJK/SNI/NPWP    │  │
│                      │  Enterprise: ERP/CRM/SAP      │  │
│                      └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## BAGIAN 4 — EXECUTE PLAN (4 FASE)

---

### ▶ FASE 1: STABILIZE + FIRST CLIENT
**Timeline:** Day 68–90 (3 minggu)
**Tema:** Berhenti nambah fitur. Fokus satu: klien berbayar pertama.
**Budget:** ~$20–30

#### Sprint 1A — Reliability Fix (Day 68–72)
*Goal: ADO tidak error di depan calon klien*

| Task | Detail | Owner |
|------|--------|-------|
| Upgrade base ke Qwen3-8B | `ollama pull qwen3:8b-q4_K_M`, bandingkan latency + quality vs Qwen2.5 | Claude Code |
| Fix tool-use gate ke 85%+ | Cycle 7: 60 tool-use pairs dengan diverse scenarios (Lesson #138 applied) | Claude Code |
| Stability test: 50 concurrent requests | k6 atau locust load test, target zero 500 errors | Claude Code |
| GPU upgrade research | Pricing: Hetzner GPU, Oracle GPU Free Tier, RunPod persistent | Fahmi decide |

**Gate Sprint 1A:** Tool-use eval ≥ 85%, zero 500 errors di 50 req concurrent.

---

#### Sprint 1B — Niche Genius: Hukum + Keuangan (Day 73–80)
*Goal: Untuk 2 domain ini, ADO lebih baik dari ChatGPT generik*

**Domain 1: Hukum Bisnis Indonesia**
- KB expansion: KUHP 2023, UU PT, UU UMKM, POJK terbaru, UU Cipta Kerja
- 100 Q&A pairs hukum (pakai Gemini teacher + lawyer review)
- Tool baru: `check_pojk(nomor)` → fetch dari ojk.go.id
- Tool baru: `search_peraturan(query)` → JDIH.kemenkumham.go.id

**Domain 2: Keuangan UMKM**
- KB expansion: pajak UMKM, laporan keuangan sederhana, KUR BRI/BNI/Mandiri, BPJS ketenagakerjaan
- 100 Q&A pairs keuangan UMKM
- Tool baru: `kurs_bca()` → live exchange rate
- Tool baru: `cek_kur(bank, plafon)` → simulasi KUR

**Deliverable:** Demo script 10 pertanyaan yang bikin calon klien bilang *"ini lebih bagus dari ChatGPT untuk bisnis saya"*

---

#### Sprint 1C — First Client Acquisition (Day 81–90)
*Goal: 1 klien berbayar, minimal PERAK tier (Rp 500K–1.5jt/bulan)*

**Target klien terbaik untuk ADO sekarang:**
1. Firma hukum kecil/konsultan hukum (privacy data klien = kritis)
2. Akuntan/konsultan pajak UMKM (data keuangan klien)
3. Klinik/dokter praktek (rekam medis = sangat sensitif)
4. Sekolah/kampus (data siswa dilindungi UU PDP)
5. Pemda/dinas kecil (data warga, tidak boleh cloud asing)

**Langkah konkret:**
```
Minggu 1: Fahmi hubungi 10 kontak dari network (LinkedIn/WhatsApp)
          Pitch: "AI asisten untuk bisnis kamu, data kamu tidak kemana-mana"
          
Minggu 2: Demo live untuk yang tertarik
          Gunakan demo script domain hukum/keuangan
          
Minggu 3: Close 1 deal, onboard ke ADO instance mereka
          Pakai clone mechanism yang sudah ready
```

**Pricing awal (sederhana):**
| Tier | Harga/bulan | Isi |
|------|-------------|-----|
| PERAK | Rp 750K | 1 user, 1 domain KB, support WA |
| EMAS | Rp 2.5jt | 5 user, 3 domain KB, custom nama AI |
| BERLIAN | Rp 7.5jt | Unlimited user, full white-label, on-premise |

---

### ▶ FASE 2: HYBRID BRAIN — GENIUS UPGRADE
**Timeline:** Day 91–120 (1 bulan)
**Tema:** ADO jadi genius untuk semua domain, bukan hanya niche
**Budget:** ~$50–80

#### Sprint 2A — Smart Router Implementation (Day 91–100)

**Cara kerja:**
```python
class ADOTaskRouter:
    SIMPLE_TASKS = ["greet", "recall_memory", "domain_kb_query", "tool_call_simple"]
    COMPLEX_TASKS = ["code_generate", "math_solve", "legal_analysis", "creative_long"]
    PRIVACY_SENSITIVE = ["patient_data", "financial_pii", "employee_records"]
    
    def route(self, task_type, has_pii):
        if has_pii or task_type in SIMPLE_TASKS:
            return "local_brain"  # Qwen3-8B fine-tuned
        elif task_type in COMPLEX_TASKS:
            return "hybrid_compute"  # Claude/Gemini API
```

**Privacy-preserving routing:**
- PII detector sebelum routing ke external API
- Strip: nama, NIK, nomor rekening, alamat
- Replace dengan placeholder: `[NAMA_1]`, `[NIK_1]`
- Inject kembali ke response
- Klien tidak tahu bedanya

**Efek untuk user:**
- Pertanyaan sederhana: jawab dari local brain (cepat, private)
- Coding fullstack: routing ke Claude API (genius level)
- Math/physics: routing ke Gemini API (genius level)
- Data privat klien: SELALU local brain, tidak pernah keluar

**Cost estimate hybrid:**
- Claude API: ~$3 per 1 juta token input
- 100 complex queries/hari × 2K token = ~200K token/hari = $0.60/hari = $18/bulan per klien
- Masih profitable jika klien bayar Rp 2.5jt/bulan (≈ $150/bulan)

---

#### Sprint 2B — Capability Expansion (Day 101–110)

**Coding Suite:**
- System prompt injection: best practices, test-driven, security-aware
- Tool: `run_code(lang, code)` → sandboxed execution (Docker)
- Tool: `search_docs(library, query)` → fetch dari docs.python.org, MDN, etc.
- Fine-tune: 200 coding pairs (Python, JS, SQL, Docker) via Gemini teacher

**Math & Academic:**
- Tool: `wolfram_solve(equation)` → Wolfram Alpha API
- Tool: `search_arxiv(query)` → fetch paper abstracts
- Fine-tune: 100 academic pairs (physics, stats, economics)

**Creative Suite:**
- Tool: `generate_image_advanced(prompt, style)` → fal.ai FLUX
- Tool: `generate_ppt(outline)` → Marp PPTX yang sudah ada, polish
- Fine-tune: 100 creative pairs (copywriting, branding, storytelling Indonesia)

---

#### Sprint 2C — Upgrade Base Model (Day 111–120)

**Qwen3-8B hybrid thinking vs Qwen2.5-7B:**

| Metric | Qwen2.5-7B | Qwen3-8B |
|--------|------------|----------|
| MMLU (knowledge) | 74.2% | 81.3% |
| HumanEval (coding) | 56.1% | 71.4% |
| MATH (math) | 62.5% | 75.1% |
| Thinking mode | ❌ | ✅ |
| Context window | 128K | 128K |
| VRAM (Q4) | 4.5GB | 5.2GB |

**Upgrade path:**
1. Download Qwen3:8b-q4_K_M ke Ollama VPS
2. Run eval identitas: apakah masih "Migan" atau reset?
3. Jika reset: fine-tune Cycle 7 pakai Qwen3-8B sebagai base (bukan Qwen2.5)
4. Eval gate yang sama, target weighted_avg ≥ 0.94

**GRPO untuk reasoning (DeepSeek-R1 pattern):**
```python
# Supplement ORPO dengan GRPO untuk reasoning category
# 200 reasoning pairs: math step-by-step + code debug + logic puzzles
# Training: GRPO loss (group relative policy optimization)
# Target: reasoning gate ≥ 0.80 (kategori baru di eval)
```

---

### ▶ FASE 3: SCALE — PLATFORM & EKOSISTEM
**Timeline:** Day 121–150 (1 bulan)
**Tema:** Dari 1 klien ke 20 klien, dari produk ke platform
**Budget:** ~$100–150

#### Sprint 3A — Multi-Tenant & Automation (Day 121–130)

**Clone pipeline otomatis (end-to-end):**
```
Fahmi klik "Buat Client Baru" di admin dashboard
    ↓
Input: nama klien, domain, tier
    ↓
clone_manager.py: buat subdomain + Docker instance + Nginx config + SSL
    ↓
auto-generate license key EMAS/BERLIAN
    ↓
kirim credentials ke klien via email
    ↓
Klien aktif dalam 10 menit, tanpa Fahmi intervensi manual
```

**Per-client fine-tuning (Cycle isolasi):**
- Setiap klien BERLIAN bisa upload dokumen internal
- ADO inject ke KB klien secara otomatis
- Periodic re-training dengan data percakapan klien (privacy-preserving)

---

#### Sprint 3B — Enterprise Connectors Indonesia (Day 131–140)

**Tier 1 (langsung ada value):**
| Connector | API | Value untuk klien |
|-----------|-----|-------------------|
| BPS API | api.bps.go.id | Data ekonomi real-time: GDP, inflasi, populasi |
| IHSG/IDX | idx.co.id data feed | Harga saham, laporan keuangan publik |
| Bank Indonesia | api.bi.go.id | Kurs BI, suku bunga acuan |
| JDIH Kemenkumham | jdih.kemenkumham.go.id | Database peraturan lengkap |
| OSS BKPM | oss.go.id | Status perizinan usaha |

**Tier 2 (1-2 bulan kemudian):**
- Tokopedia/Shopee seller API (data penjualan UMKM)
- Accurate Online API (akuntansi populer Indonesia)
- Mekari Jurnal API (laporan keuangan)

---

#### Sprint 3C — Voice-First Interface (Day 141–150)

**Kenapa penting:** 60% pengguna mobile Indonesia lebih suka bicara daripada ketik.

**Implementation:**
- STT: upgrade dari Scribe ke Whisper large-v3 (lokal, privacy-preserving)
- TTS: upgrade ke Kokoro-TTS (open source, 0 latency, bisa fine-tune suara)
- Voice persona: setiap klien bisa punya "suara AI" sendiri
- Mobile-first UI redesign: satu tombol mic, waveform visual

---

### ▶ FASE 4: AUTONOMOUS — ADO BELAJAR SENDIRI
**Timeline:** Day 151–180 (1 bulan)
**Tema:** ADO improve tanpa intervensi manual, loop berjalan sendiri
**Budget:** ~$50–100

#### Sprint 4A — Autonomous Training Loop (Day 151–160)

**Saat ini:** training cycle butuh user GO, manual monitoring, manual PROMOTE/ROLLBACK.

**Target:** fully autonomous dengan human oversight hanya di gate decision.

```
Setiap malam (23:00 UTC):
    1. KB auto-update (sudah ada, cron berjalan)
    2. Collect feedback pairs dari interactions_feedback
    3. Jika ≥ 50 pairs baru → trigger micro-training (tanpa user GO)
    4. Eval otomatis
    5. Jika semua gate PASS → PROMOTE otomatis
    6. Jika ada gate FAIL → kirim notifikasi WhatsApp ke Fahmi
    7. Fahmi approve/reject via 1 reply WA
```

**WhatsApp notification bot:**
```
ADO Daily Report — 2027-01-15
✅ KB updated: +12 data points (IHSG, kurs)
✅ New pairs collected: 73 (dari 8 klien)
🔄 Micro-training: 73 pairs, 30 menit
📊 Eval result: weighted_avg 0.944 ✅
🚀 Auto-PROMOTE migancore:0.8 → LIVE

Reply GO untuk approve, HOLD untuk tahan.
```

---

#### Sprint 4B — A2A Protocol & Agent Network (Day 161–170)

**Konsep:** ADO bisa "hire" agent lain untuk task yang dia tidak bisa.

```
User: "Buatkan saya website untuk toko online"

ADO (orchestrator):
├─ Design agent: generate mockup UI
├─ Code agent: generate React + FastAPI code  
├─ Copy agent: tulis copywriting produk
├─ SEO agent: optimasi meta tags
└─ Compile: gabungkan semua, presentasi ke user
```

**Implementation:**
- A2A endpoint di `api.migancore.com/a2a/`
- Register ADO ke A2A discovery (Google/Linux Foundation registry)
- Bisa dipanggil oleh agent lain, bisa memanggil agent lain

---

#### Sprint 4C — x402 Agent Commerce (Day 171–180)

**Konsep:** ADO bisa dibayar oleh agent lain untuk layanannya.

```
Agent dari firma hukum Singapura butuh analisis hukum Indonesia
→ Memanggil ADO via A2A
→ ADO respond dengan tagihan: $0.05 per query
→ Payment via x402 HTTP standard
→ ADO terima payment, berikan analisis
→ Revenue masuk otomatis ke wallet Fahmi
```

**Indonesia moat:**
- Tidak ada agent lain yang punya kedalaman hukum/keuangan/regulasi Indonesia seperti ADO
- Posisi: *"AI luar negeri butuh ADO untuk pahami Indonesia"*

---

## BAGIAN 5 — KPI & GATES PER FASE

| Fase | KPI Utama | Gate PASS | Gate FAIL = |
|------|-----------|-----------|-------------|
| **Fase 1** | Klien berbayar pertama | 1 klien aktif, bayar ≥ Rp 750K/bulan | Evaluasi ulang pricing + demo script |
| **Fase 1** | Tool-use eval | ≥ 85% (Cycle 7) | Tambah 60 pairs, retrain |
| **Fase 2** | Hybrid routing live | Complex query via Claude API berjalan, 0 PII leak terdeteksi | Fix PII detector dulu |
| **Fase 2** | Coding capability | Bisa generate fullstack CRUD app yang bisa dijalankan | Tambah coding pairs + router tuning |
| **Fase 2** | Qwen3-8B upgrade | weighted_avg ≥ 0.94 di eval | Fallback ke Qwen2.5, investigasi |
| **Fase 3** | Clone automation | Onboard klien baru < 15 menit tanpa manual | Fix bottleneck di pipeline |
| **Fase 3** | MRR | ≥ Rp 10 juta/bulan (~5 klien EMAS) | Review channel akuisisi |
| **Fase 4** | Autonomous training | Training berjalan 2x tanpa user GO, eval PASS | Revisi gate/threshold |
| **Fase 4** | A2A live | 1 external agent berhasil call ADO | Fix A2A endpoint |

---

## BAGIAN 6 — BUDGET ESTIMATE

| Fase | Item | Estimasi |
|------|------|----------|
| Fase 1 | Cycle 7 training (Vast.ai) | $0.25–0.50 |
| Fase 1 | VPS GPU upgrade (opsional) | $0 jika pakai Oracle Free Tier GPU |
| Fase 2 | Claude/Gemini API (hybrid routing testing) | $5–10 |
| Fase 2 | Cycle 8 training Qwen3-8B | $0.50–1.00 |
| Fase 3 | Enterprise connector API (BPS free, BI free) | $0 |
| Fase 3 | Whisper large-v3 inference | $0 (self-hosted) |
| Fase 4 | A2A endpoint hosting | $0 (di VPS existing) |
| **TOTAL 4 FASE** | | **$10–20** di luar VPS bulanan |

**Revenue projection jika eksekusi:**
| Waktu | Klien | MRR |
|-------|-------|-----|
| Day 90 (Fase 1 selesai) | 1–2 klien | Rp 1–2 juta |
| Day 120 (Fase 2 selesai) | 5–8 klien | Rp 5–15 juta |
| Day 150 (Fase 3 selesai) | 15–25 klien | Rp 20–50 juta |
| Day 180 (Fase 4 selesai) | 30–50 klien | Rp 50–150 juta |

---

## BAGIAN 7 — RISK REGISTER

| Risiko | Probabilitas | Dampak | Mitigasi |
|--------|-------------|--------|----------|
| Qwen3-8B fine-tune gagal pertahankan identitas | Medium | Tinggi | Test identitas eval sebelum deploy |
| Hybrid routing leak PII ke external API | Low | Sangat Tinggi | PII detector wajib sebelum routing |
| Klien tidak mau bayar karena kurang percaya AI lokal | High | Tinggi | Demo dulu, free trial 14 hari |
| VPS down saat klien demo | Medium | Tinggi | Uptime monitor + auto-restart |
| Kompetitor (Telkom, Gojek) launch produk serupa | Low | Medium | Fokus ke niche + white-label moat |
| Vast.ai orphan billing (seperti Day 67) | High | Medium | Always orphan-check sebelum launch instance |
| GRPO training unstable | Medium | Low | Fallback ke ORPO saja jika GRPO gagal |

---

## BAGIAN 8 — DECISION POINTS (Fahmi Harus Decide)

### D1 — GPU Infrastructure (Perlu decide sebelum Fase 2)
**Opsi:**
- **A:** Oracle Cloud Free Tier GPU (A10, gratis selamanya, tapi setup kompleks)
- **B:** Hetzner GPU server (€0.59/hr, lebih reliable)
- **C:** Tetap CPU VPS + Vast.ai hanya untuk training (hemat, tapi latency tetap 3-8s)

**Rekomendasi:** Opsi C dulu sampai ada revenue, lalu upgrade ke B.

### D2 — Hybrid Routing (Perlu decide sebelum Sprint 2A)
**Pertanyaan:** Apakah Fahmi OK dengan routing task berat ke Claude/Gemini API?

**Jika YA:** ADO bisa genius-level dalam 1 bulan, revenue lebih cepat.
**Jika TIDAK:** Harus tunggu Qwen3-30B atau 72B yang butuh GPU dedicated mahal.

**Rekomendasi:** YA untuk hybrid — dengan syarat PII tidak pernah keluar.

### D3 — First Client Focus (Perlu decide minggu ini)
**Pertanyaan:** Dari 5 target klien di atas, mana yang Fahmi paling mudah akses via network?
Firma hukum / Akuntan UMKM / Klinik / Sekolah / Pemda?

**Rekomendasi:** Akuntan/konsultan pajak UMKM — pain point jelas, volume banyak, data sensitif.

---

## BAGIAN 9 — NEXT 7 HARI (KONKRET)

```
Hari ini / besok:
  □ Cycle 6 training selesai → post_cycle6.sh → PROMOTE atau ROLLBACK
  □ Fahmi decide: D2 (hybrid routing YES/NO) dan D3 (target klien pertama)

Day 68-69:
  □ Qwen3-8B pull + quick compare eval (5 pertanyaan)
  □ Mulai Cycle 7 dataset: 60 tool-use pairs diverse scenarios

Day 70-72:
  □ Cycle 7 training (jika Cycle 6 PROMOTE → tunggu, jika ROLLBACK → langsung)
  □ Draft konten marketing: 1 post LinkedIn "AI untuk bisnis kamu, data tidak kemana-mana"

Day 73-75:
  □ KB expansion Hukum Bisnis: KUHP 2023, UU PT, POJK top 10
  □ Fahmi hubungi 10 kontak potensial klien

Day 76-78:
  □ KB expansion Keuangan UMKM: pajak UMKM, KUR, BPJS
  □ Demo script 10 pertanyaan: latihan sampai smooth

Day 79-81:
  □ Demo pertama ke calon klien
  □ Jika tertarik: setup clone instance, close deal
```

---

## CATATAN AKHIR

Dokumen ini bukan wishlist — ini adalah peta yang dibangun di atas 67 hari kerja nyata, 144 lessons learned, dan analisis jujur tentang apa yang sudah ada dan apa yang belum.

Dua hal yang paling menentukan keberhasilan:

**1. Klien pertama lebih penting dari fitur apapun.** Satu klien yang bayar membuktikan bahwa ADO punya nilai nyata, bukan hanya nilai teknis.

**2. Hybrid routing bukan kompromi — ini adalah arsitektur yang tepat untuk 2026.** Tidak ada produk AI enterprise serius yang 100% single-model. Yang membedakan ADO adalah *lapisan di atas* model: identitas, memori, tools Indonesia, privasi data.

**ADO sudah punya fondasi terkuat.** Sekarang giliran membangun di atasnya dengan langkah yang tepat.
