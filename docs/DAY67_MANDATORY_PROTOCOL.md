# DAY 67 — MANDATORY PROTOCOL DOCUMENT
**Waktu:** 22:30 WIB / 15:30 UTC, 7 Mei 2026
**Status:** Cycle 6 training RUNNING (~34%, ETA 00:42 WIB)
**VPS:** root@72.62.125.6 | /opt/ado/

---

## 1. YANG SUDAH SELESAI HARI INI

### A. Cycle 6 Training LAUNCHED
- Instance: 36295755, Q RTX 8000 48GB @ $0.255/hr, ssh7.vast.ai:15754
- Dataset: 954 pairs (ORPO apo_zero, 2 epochs, LR=6e-7)
- Status saat ini: Step ~40/118 (34%), ETA ~00:42 WIB
- Duplicate instance (36295765) dikill dalam <2 menit = $0 wasted
- 3-layer recovery system aktif:
  - Layer 1: vast_recovery.sh (PID 118146) - poll Vast.ai tiap 10 menit via SSH
  - Layer 2: wait_cycle6.sh (PID 158431) - poll /opt/ado/cycle6_output/ tiap 5 menit
  - Layer 3: training_watcher.sh di Vast.ai instance - monitor training PID

### B. Bug Fixes Kritis (Committed)
1. **wait_cycle6.sh BREAK BUG** (commit fd20341) - CRITICAL
   - Bug: Ketika monitor process exit (SSH timeout), script `break` -> post_cycle6.sh TIDAK pernah dijalankan
   - Fix: `continue` bukan `break` - polling terus bahkan setelah monitor exit
   - Lesson #143 terkait: SSH timeout lama (7200s) lebih kecil dari waktu training (3.5hr)
   - Lesson #144: break vs continue di monitoring loop = silent failure, harus audit setiap exit point

2. **post_cycle6.sh EVAL_JSON path** (commit 314f7ca)
   - Bug: EVAL_JSON primary path = `/opt/ado/eval_result_*.json` - SALAH (file tidak di sana)
   - Fix: `/opt/ado/data/workspace/` (volume mount /app/workspace di container)
   - Fix: Eval command pakai `cd /app/workspace &&` prefix supaya output file jatuh di mounted volume
   - Fix: LD_LIBRARY_PATH=/opt/llama.cpp/build/bin/ untuk llama-quantize

3. **cycle6_orpo_vast.py SSH timeout** (committed, Lesson #143)
   - Old: timeout=7200 (2hr) - akan crash sebelum training selesai
   - New: timeout=14400 (4hr) + try/except yang tidak delete instance saat timeout
   - Current PID 31373 masih pakai bytecode lama -> akan crash ~16:02 UTC
   - TAPI: training tetap survive (process di Vast.ai, bukan di SSH)

### C. GAP-01 Clone Mechanism Foundation (commit 2b623fc)
- clone_manager.py (618 lines) - async pipeline: detect -> mint -> render -> deploy -> verify
- POST /v1/admin/clone + GET /v1/admin/clone/dry-run
- E2E dry-run PASS: license minted (b84227f2...), templates rendered, SIMULATED deploy
- setup_new_ado.sh (192 lines) - bash deploy wizard standalone
- docker-compose.template.yml - Compose template untuk client deployment

### D. Post-Training Pipeline (commit c3a3462, via temp)
- post_cycle6.sh - 5 step automated: verify -> GGUF -> Ollama -> eval -> PROMOTE/ROLLBACK
- Single source of truth untuk gate thresholds (Lesson #140)
- retry=3 built-in di eval (Lesson #137)

### E. Documentation & Research
- RESOURCE_AUDIT_DAY67.md (commit d845d3f) - full VPS inventory, underutilized resources
- DAY67_STRATEGIC_PLAN.md - vision elaboration 2026-2027
- QWEN3_UPGRADE_PLAN.md (commit 4c72c1e) - upgrade path ke Qwen3-8B
- Baca MIGANCORE-PROJECT-BRIEF.md + migancore new riset.md (research 2026-2027)

### F. VPS Migration SSL (9 domains)
- tiranyx.co.id + www -> certbot OK
- sidixlab.com + app + ctrl -> certbot OK
- galantara.io + www -> certbot OK
- PENDING: revolusitani.com + abrabriket.com (DNS belum propagasi ke 187.77.116.139)

---

## 2. LESSON LEARNS HARI INI (#138-144)

### #138 - nohup fork verification
Sebelum launch training, selalu `ps aux | grep [script]`.
nohup bisa fork dua proses jika stdout buffer penuh.
Rule: launch -> ps aux verify count=1 setelah 5 detik -> kill duplicate.

### #139 - Vast.ai duplicate instance
Duplicate script launch = duplicate Vast.ai instance = ganda cost.
Rule: launch -> ps aux verify count=1 -> proceed.
Kill duplicate dalam <5 menit = $0 wasted (Vast billed dari SSH access, bukan allocation).

### #140 - Gate threshold single source of truth
Gate thresholds harus ada di SATU tempat: dibaca oleh SEMUA scripts.
Mismatch = false rollback atau false promote.
Implementasi: constants block di top of post_cycle6.sh.

### #141 - dry_run=True pattern untuk deployment
Setiap deploy script/endpoint yang touch client VPS harus ada dry_run=True mode.
dry_run: simulate semua langkah kecuali SSH/deploy + verify.
Ini test template rendering + license minting tanpa eksekusi nyata.

### #142 - mint_license() function signature
license.py expose mint_license() sebagai standalone function, BUKAN class method.
Jangan asumsi class interface. Selalu baca signature function sebelum integrate.

### #143 - SSH timeout harus melebihi training time
timeout=7200 untuk training yang butuh 3.5hr = akan crash sebelum selesai.
Rule: estimate training time realistically, set timeout=2x estimate.
Q RTX 8000 + 954 pairs + 2 epochs = ~3.5hr, jadi timeout minimal 14400.

### #144 - break vs continue di monitoring loop
`break` di monitoring loop = silent stop, tidak ada yang tau.
`continue` = terus polling.
Selalu audit exit points di loop yang bertugas trigger critical action.
Pattern: loop harus jalan sampai SUCCESS atau explicit user interrupt.

---

## 3. TEMUAN KRITIS (Resource Audit)

### A. Feedback Flywheel BROKEN (P0 - Langsung Fix)
- 0 sinyal dari 53 user terdaftar, 65 conversations, 174 messages
- interactions_feedback table = 0 rows
- Root cause: Chat UI tidak punya thumbs up/down aktif atau tidak connect ke API
- Impact: Self-improving loop TIDAK BISA JALAN
- Fix: 1 hari kerja - tambah feedback button di app.migancore.com

### B. Model Rollback Waste di Ollama (~14.4GB)
- migancore:0.1 (4.7GB), migancore:0.4 (4.8GB), migancore:0.5 (4.8GB) = semua ROLLBACK
- Tidak dipakai tapi makan disk/RAM
- Action: hapus setelah Cycle 6 PROMOTE

### C. 1,458 Training Pairs dari SIDIX (Untapped)
- /opt/sidix/brain/datasets/ punya: 713 SFT + 673 QA + 30 memory cards + 42 QA
- ALIGNED dengan visi ADO: kejujuran, sitasi, tabayyun, Indonesian context
- Zero overlap dengan current ADO training data
- Action: Adapt ke ADO format -> Cycle 7 dataset expansion

### D. Letta Integration Status UNKNOWN
- ado-letta-1: RUNNING di port 8083 (Up 2 hours)
- Letta = persistent memory + agent state yang lebih canggih dari current episodic
- TAPI: Belum diverifikasi apakah /api/services/letta.py di-call dari chat router
- Action: Cek integrasi, aktifkan cross-session memory yang proper

### E. Knowledge Graph = 0 Entities
- kg_entities: 0 rows, kg_relations: 0 rows
- fact_extractor.py EXISTS tapi tidak dijalankan
- Setiap conversation = source entities untuk KG -> RAG lebih cerdas
- Action: Jalankan fact_extractor di background setelah setiap chat

### F. ~2,050 Preference Pairs Belum Optimal Dipakai
- Total DB: 3,004 pairs
- Cycle 6 export: 954 pairs
- Sisa ~2,050 pairs belum masuk training optimal
- Action: Review source quality -> Cycle 7 expand dataset

---

## 4. TEMUAN STRATEGIS (dari Research 2026-2027)

### ADO sudah 80% aligned dengan optimal 2026 AI stack:
Stack optimal: LangGraph + Letta + Qdrant + MCP + A2A
ADO punya: Qdrant (live), MCP server (live), episodic memory (basic), tool execution (live)
Gap: Letta integration proper + A2A protocol exposure

### Positioning yang belum dieksploit:
- ADO = Cognitive Kernel-as-a-Service: expose sebagai MCP server + A2A peer
- Agents lain bisa hire ADO untuk reasoning, memory, Indonesian context
- x402 + ERC-8004: per-inference monetization dari agents lain (revenue stream baru)
- Indonesia arbitrage window: 12-18 bulan sebelum Big Tech saturate market

### 9 Non-Negotiable Principles (Status Day 67):
1. Zero Data Leak - OK (self-hosted, Docker isolated)
2. Self-Hosted Client - OK (Docker Compose per org)
3. Modular Clone - DONE dry-run (GAP-01)
4. Retrain by Owner - OK (Cycle pipeline working)
5. Base Skills Pre-loaded - OK (KB Indonesia, identity)
6. White-label ADO_DISPLAY_NAME - OK (config.py)
7. Licensed Migancore x Tiranyx - OK (license.py)
8. Anti Lock-in - OK (GGUF, Ollama, open source stack)
9. Trilingual ID/EN/ZH - PARTIAL (ID dominant, EN basic, ZH belum)

---

## 5. PLANNING

### Malam Ini (22:30 - 02:00 WIB)
1. Monitor training via: `tail -f /tmp/wait_cycle6.log /tmp/vast_recovery.log`
2. ETA 00:42 WIB: post_cycle6.sh auto-trigger
3. Jika PROMOTE: migancore:0.6 jadi default, update config.py, rebuild API, git push
4. Jika ROLLBACK: analisis gates yang fail -> plan Cycle 7 targeted supplement
5. Hapus rollback models: `docker exec ado-ollama-1 ollama rm migancore:0.1 migancore:0.4 migancore:0.5`

### Day 68 (Besok)
1. **Fix Feedback UI** - URGENT P0 (0 signals = flywheel mati)
   - Tambah thumbs up/down di setiap response Migan di app.migancore.com
   - Wire ke POST /v1/feedback endpoint
   - Target: pertama kali ada signal hari ini
2. **Review SIDIX SFT data** - 713 pairs potential untuk Cycle 7
3. **Benchmark Qwen3-8B** - hanya jika Cycle 6 PROMOTE
4. **DNS certbot** - konfirmasi propagasi revolusitani.com + abrabriket.com -> certbot

### Day 69-72
1. **Feedback -> DPO Flywheel**:
   thumb_down + correction -> teacher API -> preference_pair -> Cycle N
2. **SIDIX Data Bridge**:
   Convert 1,458 pairs ke ADO DPO format -> Cycle 7 dataset (+40% lebih besar)
3. **Letta Verification**:
   Cek /api/services/letta.py dipanggil atau tidak -> aktifkan cross-session memory
4. **KG Auto-Extract**:
   Jalankan fact_extractor.py di background post-chat -> mulai populate KG entities
5. **KB Auto-Update Cron**:
   `crontab -e` -> weekly kb_auto_update.py

### Day 73-80
1. **Clone Mechanism Real Deploy** - first paid client (bukan dry-run)
2. **A2A Protocol** - expose ADO sebagai peer agent (register ke A2A directory)
3. **Active Inference Prototype** - pymdp library test (moat 5+ tahun)
4. **Per-inference monetization** - x402 payment header research

### Day 81-90 (Bulan 3)
1. ADO sebagai Cognitive Kernel: embed di galantara.io, ixonomic embed widget
2. SIDIX channels (WA/TG/Threads) -> ADO conversation data -> DPO pairs (flywheel penuh)
3. Multilingual: ZH basic training pairs
4. First paid client deployment + license activation

---

## 6. METRICS SUMMARY (EOD Day 67)

| Metric | Value | Trend |
|--------|-------|-------|
| Cycle | 6 (training) | -> |
| Total lessons | 144 | +7 hari ini |
| Preference pairs DB | 3,004 | +954 Cycle 6 targeted |
| Beta users | 53 | stable |
| Feedback signals | 0 | CRITICAL |
| Beta conversations | 65 | stable |
| Ollama models | 7 | 3 junk (hapus) |
| VPS RAM used | 13GB/32GB | 40% |
| Bulan 2 cost est. | ~$11-12 | 37-40% of $30 |
| Current model (prod) | migancore:0.3 | weighted_avg 0.9082 |
| Gate target (Cycle 6) | weighted_avg >= 0.92 | 5 gates pending |

---

*Protocol dibuat: Day 67, 22:30 WIB | Claude Code*
*Next update: setelah Cycle 6 PROMOTE/ROLLBACK (~00:42 WIB)*
