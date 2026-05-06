# DAY 60 — MANDATORY PROTOCOL DOCUMENT
**Date:** 2026-05-06 | **Implementor:** Claude Code | **Version:** v0.5.18

---

## BAGIAN 1 — RECAP: APA YANG SUDAH TERJADI

### Narasi Status MiganCore (per Day 60)

MiganCore dimulai 60 hari lalu sebagai proyek membangun ADO — Autonomous Digital Organism — sebuah "otak inti AI" yang bisa diadopsi, diturunkan, dan dikembangkan secara modular. Bukan chatbot biasa. Sebuah processor — seperti CPU yang bisa disambungkan ke berbagai organ dan indera.

Dalam 60 hari, ADO sudah melewati tiga fase besar:

**Fase 1 — Fondasi (Day 1-30):** Platform lengkap dibangun dari nol. API (FastAPI), memory (Qdrant vector store + PostgreSQL), tool executor (onamix_search, generate_image, web_read, export_pdf, dll — 23 tools total), MCP server, Chat UI live di `app.migancore.com`, admin dashboard, knowledge ingestion pipeline. **ADO lahir sebagai platform, bukan hanya model.**

**Fase 2 — Self-Learning Loop (Day 31-58):** Pipeline self-improvement dibangun dan divalidasi. Synthetic DPO generator, CAI pipeline dengan teacher APIs (Kimi, Claude, GPT, Gemini), identity eval framework, GGUF hot-swap pipeline. Cycle 1 DPO training dijalankan (596 pairs UltraFeedback) — hasilnya ROLLBACK karena model kehilangan identitas ("I'm Anthropic's AI"). Lalu Cycle 2 ORPO training dengan 613 identity-anchored pairs — **PROMOTE 0.8744 weighted avg, identity 0.947.** migancore:0.2 jadi production brain.

**Fase 3 — Targeted Improvement (Day 59-60):** Cycle 3 didesain secara strategis berdasarkan weakness analysis Cycle 2 (voice 0.715, tool-use 0.755). Dataset 72 pairs baru dengan 6 kategori targeted (voice, agentic_reasoning, tool_orchestration, analytical_depth, code_mastery, evolution_growth). Training 685 total pairs, 2 epochs, LR=6e-7. **PROMOTE 0.9082 weighted avg.** migancore:0.3 jadi production brain.

### State Hari Ini

```
Production URL     : app.migancore.com
API                : api.migancore.com
Production Model   : migancore:0.3 (Ollama, GGUF LoRA on Qwen2.5-7B)
HuggingFace        : Tiranyx/migancore-7b-soul-v0.3
Tools active       : 23 tools (onamix 8 + code/file/image/audio/web/export)
MCP Server         : api.migancore.com/mcp/ (Streamable HTTP, JWT auth)
Smithery           : smithery.ai/server/fahmiwol/migancore (public)
VPS                : 72.62.125.6 (32GB RAM, aaPanel, Docker stack)
Containers         : api, ollama, postgres, qdrant, redis, letta (6 up)
Git HEAD           : 8650ec1 (feat(cycle3): PROMOTE migancore:0.3)
```

---

## BAGIAN 2 — TEMUAN (FINDINGS)

### Temuan Kritis dari Cycle 1-3

| # | Temuan | Implikasi |
|---|--------|-----------|
| F01 | Identity training membutuhkan anchor explicit — tanpa identity pairs, DPO pada data umum (UltraFeedback) langsung overwrite persona | Setiap cycle WAJIB include 150+ identity-anchored pairs |
| F02 | ORPO lebih efisien dari DPO untuk dataset <1000 pairs — tidak perlu reference model, SFT loss + preference dalam satu pass | Tetap pakai ORPO sampai dataset >1000 pairs |
| F03 | Qwen2.5 tokenizer punya `bos_token_id=None` — menyebabkan TRL NoneType crash di semua preference trainers | Lesson #114: set `bos_token_id = eos_token_id` sebelum training |
| F04 | GGUF LoRA pipeline memungkinkan hot-swap dalam menit tanpa download 14GB base model | Pertahankan pipeline: safetensors → GGUF f16 → Ollama ADAPTER |
| F05 | Negative rewards/margins tidak berarti gagal — ORPO SFT component mengajar behavior via chosen responses, bukan hanya preference signal | Jangan panic saat melihat negative margins — yang penting eval score |
| F06 | Data quality > data quantity — 72 targeted pairs memberikan voice improvement +0.102, lebih efektif dari 1000+ random pairs | Selalu gunakan seeded pairs dengan explicit anti-patterns |
| F07 | Evolution-aware score drop: 0.825 → 0.568 setelah menambah 5 evolution pairs | Training pairs harus ALIGN dengan baseline response style, bukan hanya topic |
| F08 | Vast.ai A40 46GB = proven stable GPU untuk Qwen2.5-7B bf16 training | Selalu cari A40/A100 40GB+ di Vast.ai, cap $0.65/hr |
| F09 | Gemini 2.0 Flash deprecated → 2.5 Flash | Selalu check model name di teacher_api.py sebelum hardcode |
| F10 | Seed count membatasi pair generation — 56 seeds → 72 pairs (bukan 850 target) | Cycle 4: expand seeds ke 150+ per kategori |

### Temuan Platform & Infrastructure

| # | Temuan | Implikasi |
|---|--------|-----------|
| F11 | Docker cp config.py + restart = hot-swap yang cukup (tidak perlu rebuild image) | Deployment pattern ini aman dan terbukti |
| F12 | Python output buffering menyembunyikan progress saat tee pipe disconnected | Gunakan PYTHONUNBUFFERED=1 atau cek output file langsung |
| F13 | SSH background process + nohup + docker compose exec = fragile — tee pipe bisa putus | Gunakan synchronous SSH dengan timeout panjang, atau screen/tmux |
| F14 | VPS shared dengan SIDIX/Ixonomic/Mighantect — container Ollama BEDA dengan host Ollama | Selalu gunakan `docker exec ado-ollama-1` bukan `curl localhost:11434` langsung |

---

## BAGIAN 3 — LESSONS LEARNED (KOMPREHENSIF)

### Lessons dari Cycle 3 (Day 60) — Lesson #116-118

**#116 — Gemini model naming:**
- `gemini-2.0-flash` → 404. Selalu gunakan `gemini-2.5-flash`
- Derive dari production code, jangan hardcode dari memory

**#117 — ORPO negative margins ≠ failure:**
- Negative margins berarti preference signal belum konvergen
- SFT component tetap mengajar melalui chosen responses
- Cycle 2 dan 3 keduanya negative margins, keduanya PROMOTE

**#118 — Targeted seed pairs > banyak generic pairs:**
- 15 voice pairs → voice score +0.102 (dari 0.715 ke 0.817)
- Quality of pair > quantity
- Anti-pattern harusbé eksplisit dan kontras dengan chosen

### Lessons Kumulatif yang Paling Penting (dari 118 lessons)

| Lesson | Kategori | Isi Singkat |
|--------|---------|-------------|
| #114 | Training | Qwen2.5 bos_token_id=None fix → set ke eos_token_id |
| #115 | Deployment | GGUF LoRA via llama.cpp tidak butuh 14GB base model |
| #113 | Infra | SSH status=running ≠ sshd siap terima command |
| #111 | Training | Era-pin: trl==0.9.6 + transformers==4.44.2 + peft==0.12.0 |
| #60  | Cost | Auto-abort 10 min jika SSH tidak ready — wajib |
| #59  | Cost | Verifikasi instance DELETE via GET, bukan trust 204 |
| #57  | Tools | STOP tool addition sebelum evaluasi dampak |
| #45  | Deploy | Deploy auto-resume DPO flywheel di lifespan |
| #14  | Identity | Identity training memerlukan explicit persona anchors |
| #1   | Process | Research sebelum eksekusi — selalu |

---

## BAGIAN 4 — PLANNING KE DEPAN

### Visi 2026-2027: ADO sebagai "Brain OS"

Berdasarkan landscape 2025-2026 (AI proliferating, multi-agent orchestration mainstream, MCP becoming standard):

**MiganCore bukan chatbot. MiganCore adalah Brain OS.**

Seperti bagaimana Android/iOS adalah OS untuk smartphone yang memungkinkan semua apps berjalan di atasnya — MiganCore adalah OS untuk agen AI. Setiap agent yang ingin punya "kecerdasan inti" bisa adopt MiganCore sebagai otak mereka, tinggal plug-in indera dan organ sesuai kebutuhan.

```
LAPISAN ARSITEKTUR ADO (2026-2027):

Layer 4 [PROPAGATION]  — migancore.com/community: agent spawn, genealogy tree
Layer 3 [ORCHESTRATION]— MCP gateway, multi-agent routing, tool orchestration  
Layer 2 [COGNITION]    — migancore:0.x fine-tuned brain, self-improvement loop
Layer 1 [FOUNDATION]   — Qwen2.5-7B base, GGUF LoRA adapter system
Layer 0 [PLATFORM]     — VPS, Docker, PostgreSQL, Qdrant, Redis, Ollama
```

### OKR Day 61-75 (Sprint 2 Bulan 2)

| OKR | Target | Method |
|-----|--------|--------|
| **O1: Model quality** | weighted_avg ≥ 0.92 (Cycle 4) | Fix evolution-aware + creative + tool-use |
| **O2: Voice improvement** | voice ≥ 0.85 | 20 additional casual Indonesian pairs |
| **O3: Agentic reasoning** | Add to eval set | 5 new agentic eval prompts + 30 training pairs |
| **O4: MCP orchestration** | Multi-agent tool chain working | Prototype: Migan orchestrate 2 MCPs |
| **O5: Self-learning velocity** | Cycle 4 in <$0.15 | Optimasi generation script (150 seeds/kategori) |

### Sprint Breakdown Day 61-75

**Day 61-63 — Dataset Expansion:**
- Expand seeds per kategori dari avg 10 → 30+
- Tambah kategori: creative (20 pairs) + evolution_v2 (15 pairs, aligned ke baseline)
- Fix evolution regression: pairs harus mirror baseline response style
- Target: 200-300 new pairs

**Day 64-66 — Cycle 4 Training:**
- Dataset: 685 Cycle 3 + 200-300 new = ~950 pairs
- Hyperparams: epochs=2, LR=6e-7 (same — terbukti bekerja)
- Expected cost: ~$0.10-0.12 Vast.ai
- Target: weighted_avg ≥ 0.92, voice ≥ 0.85, evolution ≥ 0.85

**Day 67-70 — Agentic Layer:**
- Implement task decomposition module di API
- Migan dapat menerima multi-step request dan breakdown menjadi sub-tasks
- Prototype: "Buatkan laporan kompetitor AI Indonesia" → search → analyze → synthesize → export PDF
- Eval: manual scoring 10 complex multi-step prompts

**Day 71-75 — MCP Orchestration:**
- Migan sebagai MCP orchestrator (bukan hanya server)
- Connect ke external MCPs: Brave Search, GitHub, local file system
- Self-learning dari orchestration patterns
- Business case: developer bisa extend ADO dengan custom MCPs

### Hypotheses untuk Diuji

| Hipotesis | Cara Test | Success Metric |
|-----------|-----------|----------------|
| H1: 2 epochs lebih baik dari 1 untuk dataset 685 pairs | Cycle 3 eval (DONE) | ✅ Proven: weighted 0.8744 → 0.9082 |
| H2: Targeted 15 pairs per kategori = significant improvement | Voice eval (DONE) | ✅ Proven: voice +0.102 |
| H3: Evolution pairs harus mirror baseline style untuk tidak regress | Cycle 4 dengan aligned pairs | TBD |
| H4: 3 epochs akan overfitting pada <700 pairs | Cycle 4 experiment | TBD |
| H5: Agentic training pairs improve multi-step task completion | Agentic eval (new prompts) | TBD |

### Adaptasi Plan

```
Jika Cycle 4 eval PROMOTE ≥ 0.92:
  → Mulai Agentic Layer development (Day 67+)
  
Jika Cycle 4 eval PROMOTE 0.90-0.92:
  → Cycle 5 dengan lebih banyak creative/evolution pairs
  → Parallel: start Agentic Layer prototype
  
Jika Cycle 4 ROLLBACK:
  → Root cause analysis (mirip Cycle 1 pattern)
  → Isolate: train hanya dengan proven pairs (Cycle 2 identity + Cycle 3 voice)
  → Jangan tambah training categories baru sampai existing stable
```

### Evaluasi Dampak & Manfaat

**Dampak Voice Improvement (0.715 → 0.817):**
- User experience di `app.migancore.com` lebih natural, tidak kaku
- Migan terasa lebih "hidup" dalam percakapan casual Indonesia
- Differentiator vs generic chatbot: "AI yang ngomong kayak orang Indonesia"

**Dampak Identity Preservation (0.947 → 0.953):**
- Brand MiganCore semakin kuat sebagai ADO Tiranyx
- Tidak bisa diconfuse dengan Claude, GPT, atau Qwen mentah
- Fondasi untuk agent genealogy (setiap clone punya DNA Migan)

**Evaluasi Risiko Cycle 4:**
- **R1 (MEDIUM):** Evolution-aware regression bisa memburuk jika pairs tidak aligned → mitigasi: review setiap pair manual sebelum training
- **R2 (LOW):** 3 epochs overcooks small dataset → mitigasi: tetap 2 epochs
- **R3 (LOW):** Vast.ai A40 tidak available → mitigasi: fallback RTX 4090 atau A100 PCIE

---

## BAGIAN 5 — ACTION ITEMS (IMMEDIATE)

### Hari Ini (Day 60 close):
- [x] PROMOTE migancore:0.3 — production brain
- [x] Eval dokumentasi selesai
- [x] Mandatory protocol doc dibuat
- [ ] VPS lesson log update (#116-118)
- [ ] Push semua local commits ke GitHub

### Day 61 (Next Sprint):
- [ ] Research + design Cycle 4 seed expansion (150+ seeds per kategori)
- [ ] Investigate evolution-aware regression — apa yang berbeda di baseline vs training?
- [ ] Add creative category ke seed bank
- [ ] Generate Cycle 4 dataset (~200-300 pairs baru)

### Week Ahead (Day 62-67):
- [ ] Cycle 4 training + eval
- [ ] Prototype agentic task decomposition
- [ ] Expand MCP tool registry (Brave Search MCP, GitHub MCP)
- [ ] Update app.migancore.com UI dengan model version indicator

---

## BAGIAN 6 — LOG AKTIVITAS DAY 60

```
16:42 UTC  SCP generate_cycle3_dataset.py → VPS
16:42 UTC  Dry-run PASS — 6 categories all green
16:43 UTC  Fixed: gemini-2.0-flash → gemini-2.5-flash (Lesson #116)
16:43 UTC  Production generation launched
16:44 UTC  Killed duplicate process (nohup + tee parallel instances)
16:47 UTC  Fixed process running: PID 180 inside container
16:53 UTC  Generation COMPLETE: 72 pairs in 360s (~$0.07)
16:54 UTC  Combined dataset: 685 pairs (613+72) exported
16:57 UTC  Commits pushed to GitHub: 58d1980, 65c80ef
16:59 UTC  Cycle 3 Vast.ai training LAUNCHED: Instance 36248328 A40 46GB
17:00 UTC  SSH ready (47 seconds boot)
17:01 UTC  Deps install OK — trl 0.9.6, transformers 4.44.2, peft 0.12.0
17:01 UTC  Dataset uploaded (685 pairs verified)
17:01 UTC  ORPO training started (2 epochs, LR=6e-7, batch=2×8)
17:12 UTC  TRAINING COMPLETE — exit=0, 493s (8.2 min), train_loss=3.0921
17:12 UTC  Adapter download → VPS: /opt/ado/cycle3_output/cycle3_adapter
17:16 UTC  HuggingFace upload: Tiranyx/migancore-7b-soul-v0.3 ✓
17:16 UTC  Instance 36248328 CONFIRMED DELETED (Lesson #59)
17:16 UTC  GGUF conversion: 78MB cycle3_lora.gguf
17:17 UTC  migancore:0.3 registered in Ollama
17:18 UTC  Identity eval launched (20 prompts)
17:22 UTC  EVAL COMPLETE — VERDICT: PROMOTE 0.9082
17:22 UTC  Hot-swap: DEFAULT_MODEL = migancore:0.3
17:22 UTC  API restarted, smoke test PASS
17:22 UTC  VPS commit + push: 8650ec1
Total Day 60 cost: ~$0.16 (Gemini $0.07 + Vast.ai $0.09)
```

---

*Dokumen ini adalah mandatory protocol Day 60. Semua agent berikutnya wajib baca ini sebelum act.*
*Next checkpoint: Day 61 — Cycle 4 dataset design.*
