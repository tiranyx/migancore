# MIGANCORE — AGENT ONBOARDING PROTOCOL (PERMANENT)
**Owner:** Fahmi Ghani (tiranyx.id@gmail.com) | Founder & Owner, PT Tiranyx Digitalis Nusantara (brand: Tiranyx)
**Project:** MiganCore = Autonomous Digital Organism (ADO) — modular AI brain
**Vision:** "Otak inti AI yang bisa diadopsi, diturunkan, dikembangkan modular oleh AI lain — seperti prosesor / otak manusia siap terhubung indera & organ via sistem syaraf."

> **WAJIB BACA DI AWAL SETIAP SESI BARU. JANGAN LANGSUNG EKSEKUSI.**
> Pemilik proyek tidak harus mengulang protokol berulang-ulang — protokol HIDUP DI FILE INI.

---

## 🟢 30-DETIK FIRST CHECK (sebelum apa-apa)

```bash
# 1. Production health (3 commands max)
curl -s https://api.migancore.com/health
curl -s https://api.migancore.com/v1/public/stats | head -2
git -C /c/migancore/migancore log --oneline -10

# 2. Read 5 docs (priority order, total ~20 min):
#    a) docs/AGENT_ONBOARDING.md (THIS FILE)
#    b) docs/VISION_PRINCIPLES_LOCKED.md ⭐ NEW Day 52 — anti-strategi-drift
#    c) docs/ENVIRONMENT_MAP.md (VPS topology — CRITICAL, shared with 4 other projects)
#    d) docs/RESUME_DAY*_TO_DAY*.md (latest break-state checkpoint)
#    e) docs/VISION_DISTINCTIVENESS_2026.md (strategic compass)

# 3. Skim memory:
#    cat ~/.claude/projects/C--migancore/memory/MEMORY.md
#    cat ~/.claude/projects/C--migancore/memory/day{NN}_progress.md (latest)
```

**JANGAN SKIP LANGKAH 2.** Banyak bug hari kemarin disebabkan tidak baca environment dulu.

### Current North Star Ping - M1.6 Dev Organ

MiganCore sekarang punya arah eksplisit untuk self-improvement code/tool/workflow,
bukan hanya model training: observe -> diagnose -> propose -> sandbox patch ->
test -> iterate -> validate -> promote -> monitor -> learn.

Wajib baca sebelum menyentuh autonomy, tools, deployment, training, atau agent
behavior:

- `docs/SELF_IMPROVEMENT_NORTHSTAR.md`
- `docs/COGNITIVE_SYNTHESIS_DOCTRINE.md`
- `docs/INNOVATION_ENGINE_DOCTRINE.md`
- `docs/MIGANCORE_DIRECTION_LOCK.md` Section 8
- `docs/01_SOUL.md` Section X
- `api/services/dev_organ.py`

### Cognitive Synthesis Rule

If Fahmi gives a non-technical, intuitive, visual, or half-formed idea, do not
force him to become the engineer. Translate founder intent first, synthesize
the hidden concept, map it to components/roadmap/gates, and execute the first
safe slice when context is sufficient. Canonical reference:
`docs/COGNITIVE_SYNTHESIS_DOCTRINE.md`.

### Innovation Engine Rule

After intent is understood, convert cognition into innovation: generate
multiple options, rank them, prototype the smallest useful artifact, test,
polish, toolify repeated workflows, and save strong examples as training data.
Canonical reference: `docs/INNOVATION_ENGINE_DOCTRINE.md`.

---

## 🛡️ MANDATORY PROTOKOL (USER REQUIREMENT — JANGAN DILUPAKAN)

User's exact words yang HARUS diikuti tiap sprint:

### Pre-execution
1. **Baca seluruh dokumen penting** — anti kehilangan arah dan konteks
2. **Riset terlebih dahulu** — sumber 2025-2026 dari arxiv, github, blog reputable, reddit, jurnal
3. **Hipotesis** dengan framework H/R/B (Hipotesis / Rencana adaptasi / Evaluasi Dampak / Manfaat / Resiko)
4. **Buat KPIs + benchmarking + objective** per day-sprint
5. **Pilih cognitive trends 2026-2027** yang relevan (research dulu, jangan asumsi)

### Post-execution
6. **QA + Validate + Verify** secara empirical
7. **Catat semua temuan** — log progress, metodologi, hasil
8. **Per-day documentation:** `docs/DAY{N}_PLAN.md` + `docs/DAY{N}_RETRO.md` + `memory/day{N}_progress.md`
9. **Update `MEMORY.md` index** untuk anti-context-loss
10. **Setiap kegagalan = lesson** untuk tidak diulangi; setiap success = pattern untuk diulangi/dilipat-gandakan

### Communication
- **Bahasa Indonesia primary**, English untuk konteks teknis
- **Honest partner-engineering tone** — bukan "yes-man". Jika ada masalah, sampaikan jujur.
- **Jangan janji yang tidak bisa ditepati.** Jika perlu user GO untuk spending, MINTA dulu.

---

## 🏗️ PROJECT STATE QUICK REFERENCE

| Field | Value |
|-------|-------|
| Repo (LOCAL) | `C:\migancore\migancore` |
| Repo (VPS) | `/opt/ado` |
| Repo (GIT) | `git@github.com:tiranyx/migancore.git` |
| API | `https://api.migancore.com` |
| Chat UI | `https://app.migancore.com` |
| Landing | `https://migancore.com` |
| MCP server | `https://api.migancore.com/mcp/` |
| Smithery | `smithery.ai/server/fahmiwol/migancore` |
| Current version | check via `curl https://api.migancore.com/health` |
| VPS | 72.62.125.6 (32GB / 8 vCPU / Ubuntu 22.04) |
| SSH key | `~/.ssh/sidix_session_key` |
| Dataset/training | `/opt/ado/training/` + `/opt/ado/eval/` |

**SHARED VPS — read `docs/ENVIRONMENT_MAP.md`.**

---

## 🚨 CRITICAL FAILURE MODES (LESSONS PAST)

Top 6 yang HARUS diingat (144 lessons total — semua di MEMORY.md per-day notes):

| # | Lesson | Forever-rule |
|---|--------|--------------|
| 39 | `asyncio.create_task` swallowed exception | Wrap dengan `safe_task()` from `services/contracts.py` |
| 44 | Container kill = background tasks die silent | Persist state in Redis/DB + auto-resume in lifespan |
| 45 | Auto-resume condition wrong | State-machine guards, never silent skip |
| 46 | Tool description "use X instead" tapi X tidak ada → brain emit empty | Boot validator `services/contracts.py:validate_tool_registry()` |
| 51 | **Design by Contract for LLM Agents** — boot validators + safe_task + watchdog + output contracts | One module = catches 4 bug classes |
| 53 | Parallel sessions coordination | `git pull` + scan recent commits di session start |
| **54** | **VPS SHARED — selalu cek environment map dulu** | Dual ollama daemon (host vs container) buang berjam-jam karena tidak baca topology |
| **55** | **Cycle 1 trigger TANPA pre-flight availability check = waste** | Sebelum spawn pod $0.69/hr, query RunPod API dulu untuk GPU availability di data center. Hari ini langsung spawn → 2.5 jam stuck → $1.38 wasted. |
| **56** | **Heavy build di tenant lain (next/webpack) saturasi CPU → user chat slow** | Owner Fahmi commit untuk: jangan run `next build` di tiranyx-co-id selama jam chat MiganCore. Atau dedicated VPS untuk migancore. |
| **57** | **JANGAN sarankan tools/cloud baru saat sudah cukup — STOP per VISION compass** | 21 tools sudah cukup; STOP wrapper tool addition. Vendor cloud alternative bukan jawaban — yang penting pre-flight check. **DOUBLE DOWN ke identity eval + hot-swap demo + Dream Cycle, bukan feature collection.** |
| **58** | **Mencampur dua konteks dalam 1 kalimat → user bingung** | Pisahkan: "GPU cloud alternative" (infra ops) ≠ "brain tools" (skill registry). Selalu sebut domain konteks eksplisit. |
| **59** | **JANGAN trust HTTP 204 untuk DELETE pod — selalu VERIFY** | Hari ini saya laporkan "DELETE 204" → asumsikan pod gone. Reality: termination delayed/silent-fail → pod jalan 10+ jam = $6.76 wasted. Setelah DELETE, WAJIB GET /pods/{id} → expect 404, ATAU GET /pods → expect pod tidak di list. |
| **60** | **SECURE non-spot pod BILL DARI ALLOCATION, bukan dari boot** | Pod stuck "Rented by User" tanpa runtime jalan tetap kena charge $0.69/hr. SPOT pods only charge when running. ATURAN: kalau pod tidak boot dalam 5 menit, IMMEDIATE terminate + retry, jangan tunggu. |
| **61** | **Cost telemetry harus polling otomatis, bukan manual check** | User screenshot menunjukkan pod jalan, saya pikir sudah mati. Butuh: cron job 5-menit yang query /v1/pods + log to file. Kalau ada pod >$0/hr lebih dari 1 jam tanpa progress = alert. |
| **62** | **RunPod has bad days — diversify OR accept variability** | Hari ini 2x attempts (4090 RO + A40 CA, both SECURE) gagal boot. Bukan masalah image (10GB → 3GB tidak bantu). RunPod-side allocation issue. Rule: jangan spend >2 jam same vendor same fail mode → switch vendor (Vast.ai, Lambda) ATAU change strategy (defer + ship other tracks). |
| **63** | **Local laptop training infeasible untuk 7B di consumer hardware tipikal** | Fahmi laptop = ASUS TUF FA506QM (Ryzen 7 + RTX 3060 Mobile 6GB + 16GB RAM). Looks adequate but 3 blockers: (1) disk 98% full = no space untuk 15GB Qwen base, (2) RAM avail 2.42GB = OOM risk, (3) VRAM 6GB Mobile = edge of viability. Rule: hardware check WAJIB pre-spawn. Mobile RTX 3060 6GB ≠ desktop RTX 3060 12GB. Check `nvidia-smi` + `df -h` + `free -h` SEBELUM commit local strategy. |
| **65** | **Verify END-TO-END backend BEFORE assuming UX broken** | Day 49.5 panik chat slow → 5 jam diagnose Ollama/dual daemon. Real cause: tiranyx CPU contention (Lesson #56). Day 50 morning chat fast 22tps karena tiranyx idle. Rule: shared-resource contention check FIRST sebelum deep-dive code. |
| **66** | **Indie indie launch Indonesia: "gw bikin sendiri" + scarcity + time-bound + 15-sec video** | Day 51 research synthesis: synchronous 15-min demo = 80% week-2 retention (vs 15% cold link). Video > GIF (Indonesian WA = GIF=meme). DM ~70 words max. 3 chips beat 6 by 40% (Vercel A/B). Pi.ai expectation framing "lebih lambat tapi inget" disarms ChatGPT comparison. WhatsApp group >> Notion forms 10:1 at N=5 (Reflect.app retro). Indonesia tactic uniqueness: weekly public X thread "Otak Belajar Apa Minggu Ini" — narrate self-improving moat. |
| **67** | **JSX edits WAJIB verify variable scope FIRST + render BEFORE declare done** | Day 51 saya add WhatsApp button dengan `conversationId` (tebakan) — actual var `convId`. ReferenceError → JS fail top-level → React never render → BLANK page di production at moment-of-launch. User caught immediately. Rule: BEFORE declare any frontend edit done, (a) `grep -nE "varName"` untuk cek variable real ada, (b) reload browser dan verify render, (c) test Ctrl+Shift+R kalau cache stale. Backend semudah `import ast; ast.parse()` tapi frontend HARUS render-test. Cost: zero-tokens fix (3 char change), tapi reputasi 5 detik blank. |
| **68** | **Teacher API = MENTOR, NEVER live RESPONDER** | Day 52 saya hampir usulkan Hybrid Brain (Kimi K2 sebagai live chat responder). User tarik kembali — itu wrapper pattern, defeats vision. Teacher API (Anthropic/OpenAI/Kimi/Gemini) ROLE: synthetic data generator, CAI critique, DPO pair generator (chosen=teacher, rejected=migan_baseline) → SimPO trains Migan. **Migan harus respond ke user pakai own brain.** Read `docs/VISION_PRINCIPLES_LOCKED.md`. |
| **69** | **Standing alone principle — own tools default, third-party as teacher only** | ONAMIX pattern (took user-owned HYPERX, made own MCP) is the model. Don't add new third-party SDK as DEFAULT path. Acceptable trade-offs: (a) Gemini Vision as TEACHER for vision data → distill local Qwen-VL Day 60+, (b) fal.ai image gen (large diffusion impractical local). NEVER: route user chat to third-party. |
| **70** | **Speed problems → better local model, NOT wrapper** | When CPU 7B too slow, vision-aligned solutions ranked: (1) speculative decoding (Qwen 0.5B+7B, all local, 2-3x), (2) distill 7B→3B own model, (3) better quantization, (4) dedicated GPU, (5) Cycle N+ better Qwen. NEVER: live teacher API. Speed trade-off doesn't justify breaking vision. |
| **71** | **Speculative decoding on shared CPU = often a wash. Bench BEFORE flipping default** | Day 53: llama-server (Qwen 7B+0.5B) ran on same 8-vCPU host as Ollama. Both engines competed for L2/L3 cache + threads → spec-dec measured 2.63 tok/s, Ollama also degraded under contention. Theoretical 1.6-2x speedup needs (a) isolated CPU/RAM, (b) GPU draft offload, OR (c) single-engine deployment. Rule: NEVER flip `auto` default to a new inference engine without isolated apples-to-apples benchmark. Default stayed Ollama; speculative = opt-in via `X-Inference-Engine: speculative` header. Honest KPI report > shipping a regression to "look fast." |
| **72** | **Self-learning sources are Migan's "library card", NOT its tongue** | Day 53 user added w3schools/roadmap.sh/freecodecamp/discuss.python/stackoverflow as approved sources. Library card = read access (via web_read/onamix_search) for mentor knowledge. Tongue = response — always own model + own voice. Confusing the two = wrapper pattern (#68) extended to web. Right pattern: read source → distill to DPO pair → train → eventually answer without source. See `docs/SELF_LEARNING_SOURCES.md`. |
| **73** | **After flipping a default, audit ALL surfaces that re-derive the same decision** | Day 53 evening: I flipped `auto` from speculative→ollama (Lesson #71) but the response header `X-Inference-Engine-Resolved` re-derived the choice via duplicated logic that wasn't updated → header reported `speculative` while runtime used Ollama. Pure observability lie. External agent caught within hours. Rule: when a default flips, `grep` codebase for all parallel derivations of the same decision; either delete duplicates and pass the resolved value, or update atomically. **Single source of truth = drift-free.** Fix in `api/routers/chat.py` resolves engine ONCE, hands result to both header and generator. |
| **74** | **Spend on the bottleneck, not on the comfortable upgrade** | Day 53 evening Fahmi tanya "Hostinger VPS plan mana yang cukup?" karena local desktop penuh. Tapi blocker aktual = Cycle 1 (butuh GPU). Hostinger KVM = CPU only, 0% bantu Cycle 1. Comfortable upgrade ($25-51/mo dedicated VPS) tidak solve real problem ($5 RunPod top-up does). Rule: sebelum approve purchase, jawab "ini solve bottleneck atau comfort?" Pair dengan #57 (STOP — don't add tools/cloud when X already enough) + #70 (speed → better local model NOT vendor swap by default). Doc: `docs/VPS_DECISION_DAY53.md`. |
| **75** | **Audit vendor's first-class features BEFORE building custom from raw REST** | Day 54 morning: saya tulis 250-line `cycle1_runpod.py` dengan raw `urllib.request` REST calls. Fahmi tunjukin RunPod console punya Fine-tuning UI + Pod Templates + Network Volumes + `runpodctl` CLI — fitur yang dirancang persis untuk hindari boilerplate ini. Fine-tuning UI tidak fit SimPO+APO custom kita, tapi **Pod Templates** (pre-baked image, boot ~60-120s vs 300s+) dan **Network Volumes** (persist Qwen 7B base 15GB across cycles) absolutely would have helped. Rule: sebelum commit ke custom integration, spend 15min baca vendor's docs **table of contents** (bukan API reference). Identify high-leverage features ABOVE raw REST. Custom code only kalau tidak ada built-in match. Doc: `docs/RUNPOD_FEATURES_AUDIT.md`. Pair dengan #57 (STOP — don't build what already exists). |
| **76** | **Explicit timezone discipline in mixed-locale teams** | Day 54: server logs UTC (Docker default), Fahmi reads Jakarta WIB (UTC+7). Saya tulis "22:37" tanpa konteks WIB → cognitive load di Fahmi untuk mental convert. Rule: setiap operational timestamp di user-facing reports = sertakan UTC + WIB. Format: `22:37 UTC (05:37 WIB Jakarta)`. Logs internal boleh UTC-only, tapi any human-facing summary WAJIB dual. |
| **77** | **RunPod Serverless needs network volume FROM DAY ONE** | Endpoint without `networkVolumeId` = `/runpod-volume/` is worker EPHEMERAL storage, idleTimeout 5s = adapter LOST despite logs claiming "saved". Pre-flight: create volume in target GPU region → attach via PATCH `/v1/endpoints/{id}` → THEN submit jobs. Day 54 trained successfully 3x on serverless but lost ALL adapters. Cost: ~$1.50 + 24 min training time. |
| **78** | **When blocked at vendor abstraction tier, try NEXT HIGHER tier before debugging current** | Day 54: stuck direct REST API pod (5x boot timeout) → moved up to Hub Serverless (different bugs) → moved DOWN to dedicated pod via UI (combined: UI deploy reliability + manual training control). RunPod tier ladder: Direct REST → Pod Templates → runpodctl → Hub Serverless → Fine-tuning UI. Pair with #75 (audit) and #57 (STOP). |
| **79** | **Diversify vendor stack EARLY when training is the moat** | Day 54: RunPod direct boot 5/5 fail + Vast.ai marketplace flake same day. Single-vendor dependency = blocking. Free credits: $19.20 RunPod + $7 Vast + $100 DigitalOcean AMD MI300X. Stock 2-3 accounts BEFORE blocking on one vendor's bad day. Operational hygiene, not feature creep. |
| **80** | **Axolotl Hub Serverless `output_dir` doesn't persist to user network volume despite logs claiming saved** | RunPod's `axolotl-ai-cloud` Hub serverless writes cache (`/runpod-volume/prepared/`, `huggingface-cache/`) to volume but NOT `output_dir`. Empirical Day 54: 8 runs claimed save success in logs, 0 adapters retrievable. Workaround: dedicated pod with manual Axolotl install + explicit volume mount + `output_dir: /workspace/...`. |
| **81** | **UI-deploy via console more reliable than direct REST API spawn on RunPod (Day 54 empirical)** | 5/5 direct REST API pod spawn = boot timeout 5min. 4/4 UI-deploy via console = succeeded (endpoint serverless + CPU pod retrieve + A100 GPU pod train + checkpoint pod). Hypothesis: UI uses different scheduler path that handles network/SSH provisioning better. When REST blocks, switch to UI. |
| **82** | **Axolotl 0.16.0 install pitfalls — 3 sequential gotchas** | Manual `pip install axolotl==0.16.0` triggers chain: (1) torchvision::nms operator missing (incompatible torch) → `pip uninstall -y torchvision`, (2) `whitelist.yaml` missing in `axolotl/telemetry/` (packaging bug) → `mkdir + echo "models: []" > whitelist.yaml`, (3) auto-detected `is_qwen_derived_model: true` triggers Qwen1 `eod_id` AttributeError → force `false` in YAML. Plus `export AXOLOTL_DO_NOT_TRACK=1`. |
| **83** | **Save adapter to container disk if network volume tight (avoid disk quota mid-save)** | Day 54 r9 first attempt: training 75/75 succeed → save to `/workspace/r9_manual` → "Disk quota exceeded" mid-write after 14GB partial (volume 30GB filled by HF cache 15GB + checkpoint 14GB). Lesson: estimate save footprint = adapter (150MB) + merged model `save_only_model: false` default (+15GB) + checkpoint (~325MB) + tokenizer (11MB). Budget volume accordingly OR `output_dir: /root/...` (container ephemeral 30GB plenty) and upload to HF before pod stop. |
| **84** | **Production health > feature development** | Day 55 Kimi session: saya ship frontend link fix SEBELUM verify backend health. API 502 = semua fitur Day 40-55 tidak bisa diakses oleh user. Urutan WAJIB: (1) curl health endpoint, (2) fix critical blocker, (3) baru feature. **Rule: jangan deploy feature ke production yang sedang 502/unhealthy.** |
| **85** | **Frontend rendering adalah 50% UX — parse/linkify output correctly** | Backend bisa return data sempurna, tapi jika frontend tidak parse markdown/links/images correctly, user experience tetap buruk. Day 55: Wikipedia fix returned proper content (fixed) tapi link `[text](url)` tidak bisa diklik karena frontend render as raw text. Selalu test E2E: backend response → frontend display → user can interact. |
| **86** | **Single source of truth untuk repo = subrepo aktual, bukan root** | Root `c:\migancore` (stale Day 2 clone, banyak scripts lama) ≠ subrepo `c:\migancore\migancore` (main aktual, HEAD). Agent baru sering baca yang stale. Rule: **ALWAYS verify repo path** sebelum read atau commit. `git log --oneline -3` harus show expected recent commits. Pair dengan Disclaimer user di awal setiap session. |
| **87** | **"Guru" harus didokumentasikan, bukan diingat** | Agent memory tidak persist across sessions. Semua knowledge, config, lessons, working patterns WAJIB di-commit ke repo. Jangan assume "agent lain ingat" — mereka tidak. Every lesson = add baris ke AGENT_ONBOARDING.md. Every working config = commit ke docs/. Pair dengan Lesson #53 (parallel sessions coordination). |
| **88** | **Coordinate explicitly dengan concurrent agents; isolate edit domains** | Day 55: Claude active on backend (Docker rebuild + eval) saat Kimi active on frontend (linkify). Tanpa domain isolation, race condition: restart container saat build, edit same file concurrently. Protocol: (1) user announce domain per agent explicitly, (2) never restart container if other agent is mid-build, (3) gitblame check before editing file yang mungkin sedang di-edit agent lain. |
| **89** | **The SLM revolution is NOW — Qwen 7B self-hosted bet adalah keputusan yang benar** | Gartner 2026: 40% enterprise AI workloads pindah ke SLM by 2027. Market $3.42B→$12.85B (CAGR 30.27%). Qwen2.5-7B Q4_K_M on CPU VPS = sweet spot. Self-hosted = privacy-first = sovereign AI (tren kuat Asia-Pasifik, 34% CAGR). **Rule: jangan tergoda pindah ke cloud LLM. Validated bet. Stay the course.** |
| **90** | **Self-improvement requires verifiable outcomes — focus SimPO on measurable tasks** | Riset 2025-2026: self-improvement works di domain verifiable (code, math, structured tasks), sulit di subjective (writing quality, creative freeform). SWE-RL, GEPA, OpenAI Cookbook — semua butuh outcome evaluability. **Rule: Cycle N SimPO training WAJIB fokus pada task yang bisa di-eval objektif: tool calling accuracy, identity consistency, code correctness.** Random open-ended DPO pairs = wasted compute. |
| **91** | **Multi-agent orchestration = differentiator 2027 — tapi start simple** | Gartner: 80% customer-facing processes handled multi-agent by 2028. Framework consolidation (7+ frameworks → 2-3 winners) dalam 12 bulan. Pattern: start centralized orchestrator-worker → decentralize when proven. **Rule: MiganCore spawn system (L5 Director) adalah foundation yang benar. Evolve ke "Agent Swarm Mode" Q3 2026 — inter-agent communication + result aggregation. But don't over-engineer now.** |
| **92** | **Position MiganCore sebagai "digital employee" bukan "chatbot subscription"** | Riset monetisasi 2026: agent-based pricing ($29–97/month) dan outcome-based (15-20% value) paling sustainable saat AI cost → 0. "Digital employee that learns" = emotional anchoring ke ROI nyata, bukan feature list. **Rule: beta pitch = "Otak AI yang belajar sendiri dari kerja kamu" bukan "AI assistant with 23 tools".** Setiap feature HARUS bisa diframe sebagai employee capability. |
| **93** | **Framework consolidation window = 90 days to capture mindshare** | 2026 ada 7+ agent frameworks (LangGraph, CrewAI, OpenAI SDK, Swarms, Ruflo, AutoGen, ADK). Market akan konsolidasi ke 2-3 winner dalam 12 bulan. **Rule: ship beta + paid platform dalam 90 hari dari today (deadline: ~2026-08-06). First-mover advantage di Indonesian sovereign AI = compounding. Miss window = competing against funded incumbents.** |
| **94** | **Generic DPO data destroys identity — data curation > data volume** | Day 56: 596 DPO pairs dari UltraFeedback (generic preference) → adapter degrades identity 20.6% (0.8438 → 0.6697). DPO pada generic data membuat model "generically helpful" tapi kehilangan distinctive personality. **Rule:** Cycle N training WAJIB menggunakan data spesifik untuk domain improvement yang di-target. Identity training = identity pairs. Code training = code pairs. Generic mix = generic degradation. |
| **95** | **Eval gate saves production — measure before promote** | Day 56: adapter 0.6697 hampir serving traffic. Threshold 0.80 menangkap degradation sebelum user terkena. Tanpa eval gate, kita mungkin sudah deploy model yang "helpful" tapi tidak punya personality. **Rule:** Setiap adapter WAJIB eval sebelum promote. Zero exceptions. ROLLBACK is a success, not a failure. |
| **96** | **The self-improving loop pipeline works — it's the data that needs fixing** | Day 56: Train → convert → GGUF → Ollama → eval = end-to-end pipeline PROVEN. Adapter gagal karena data, bukan infrastructure. **Rule:** Infrastructure = solved. Problem = data curation. Double down pada synthetic pair generation (CAI quorum), bukan infrastructure tooling. |
| **97** | **Gemini = bulk synthetic teacher, Kimi = quality reviewer** | Day 57: Kimi K2 org concurrency limit=3 → 95% 429 errors pada batch generation. Gemini 2.5 Flash = no concurrency issues, $0.0076 untuk 200 calls (157x cheaper than Kimi). **Rule:** BULK pair generation (100+ calls) = Gemini. SINGLE high-stakes refinement/review = Kimi/Claude. Never batch Kimi at >2 concurrency. |
| **98** | **Synthetic pairs = source_message_id=None. Never random UUID.** | Day 57: FK violation `preference_pairs.source_message_id → messages.id` karena script menggunakan `str(uuid.uuid4())` untuk synthetic pairs. Random UUID tidak ada di tabel messages. **Rule:** Synthetic pairs ALWAYS `source_message_id=None`. Hanya real CAI pipeline pairs (dari actual user conversations) yang punya real message UUID. Check schema FK sebelum INSERT ke preference_pairs. |
| **99** | **Gemini 2.5 Flash thinking = maxOutputTokens budget drain** | Day 58: `max_tokens=300` menghasilkan response 30-67 karakter (truncated) karena Gemini menggunakan token untuk internal "thinking". Fix: `max_tokens≥1000` untuk code, `≥400` untuk structured output. **Rule:** Gemini 2.5 Flash + code/structured output = selalu ≥800 tokens. Never <300 untuk output >1 paragraf. |
| **100** | **Pre-bake training Docker images untuk reduce env setup waste** | Day 59: 21 attempts, 18 di antaranya adalah env setup debugging. Actual training hanya 186 detik (3 menit). **Rule:** Build Docker image dengan pinned TRL+transformers+peft+CUDA pre-installed. Spawn → train immediately. Env setup adalah waste yang bisa di-eliminate. |
| **101** | **ORPO > DPO untuk identity preservation** | Day 59: ORPO (Odds Ratio Preference Optimization) menggabungkan SFT + preference dalam single step → less forgetting daripada DPO yang butuh reference model. Hasil: identity 0.947 vs DPO 0.6697. **Rule:** Untuk identity preservation, gunakan ORPO atau SimPO (reference-free), bukan DPO. |
| **102** | **GGUF LoRA deploy = 80MB, bukan 14GB** | Day 59: `convert_lora_to_gguf.py` mengubah adapter-only (155MB) → GGUF LoRA (80.7MB). Ollama `ADAPTER` directive load di atas base model yang sudah ada. Deploy dalam menit, bukan jam. Bandwidth: 80MB vs 14GB base model. **Rule:** Selalu gunakan GGUF LoRA untuk hot-swap deploy, kecuali base model juga berubah. |
| **103** | **Data identity-specific = kunci self-improvement** | Day 56→59: 596 generic pairs → identity crash. 613 identity-anchored pairs → identity 0.947. **Rule:** Self-improvement hanya works dengan data yang spesifik untuk domain target. Generic data = generic degradation. Identity pairs = identity preservation. |
| **104** | **Eval gate category weights must reflect business priority** | Day 57: identity 40% + voice 30% = 70% personality-critical. Ini memastikan adapter tidak lolos kalau personality masih rusak. **Rule:** Category weights = business priority. Jika identity adalah moat, identity harus dominan di eval. |
| **105** | **Teacher API quality untuk identity = CAI quorum > single teacher** | Day 57-58: Gemini generate bulk pairs dengan baik, tapi quality review dari Kimi/Claude lebih akurat untuk edge cases. **Rule:** Bulk generation = Gemini. Quality review/edge case refinement = Kimi/Claude quorum. Two-stage pipeline: generate → review → filter. |
| **106** | **21 attempts → 1 root cause = persistence pays** | Day 59: 17 attempts memperbaiki hal yang salah (packages, env, collators). Attempt 18-20 menemukan root cause sebenarnya (bos_token_id). **Rule:** Jika training crash berulang, exhaustive diagnostic (None scan, token inspection) lebih valuable daripada trial-and-error fix. |
| **107** | **Qwen-derived models need BOS token fix untuk TRL** | Day 59: `tokenizer.bos_token_id is None` pada Qwen2.5 → TRL crash. Fix: `bos_token_id = eos_token_id[0]`. **Rule:** SEMUA model turunan Qwen WAJIB cek BOS token sebelum TRL init. Ini affects Qwen2.5, Qwen3, dan model lain yang tidak punya BOS eksplisit. |
| **108** | **PyTorch base image must match TRL/transformers era** | Day 59: PyTorch 2.4.0 (Aug 2024) incompatible dengan TRL 1.x+ (2026). Fix: pytorch:2.5.1-cuda12.4-cudnn9-devel. **Rule:** GPU cloud image WAJIB compatible dengan target package era. Check PyTorch release date vs TRL release date sebelum spawn. |
| **109** | **venv --system-site-packages isolates TRL tanpa breaking CUDA** | Day 59: pip install TRL ke user-site tapi conda site-packages take precedence. Fix: venv dengan `--system-site-packages` inherit CUDA/torch sementara venv TRL first in sys.path. **Rule:** Untuk package upgrade di conda base image, gunakan venv isolation — jangan pollute conda base atau rely pada user-site. |
| **110** | **TRL version pins must be era-consistent** | Day 59: `trl<0.14.0` tidak match post-1.0 TRL. `trl==0.9.6` (pre-1.0, punya ORPOTrainer) atau `trl>=1.0` (modern). Mixed era = import hell. **Rule:** Setiap version pin harus include era context di comment: "trl==0.9.6 (pre-1.0, has ORPOTrainer but not SimPOTrainer)". |
| **111** | **Package pinning adalah version archaeology** | Day 59: Future agents perlu tahu KENAPA pin tertentu dipilih — bukan hanya angkanya. **Rule:** Setiap pin WAJIB include comment dengan: (1) versi yang dicoba dan gagal, (2) versi yang works, (3) tanggal/era context. |
| **112** | **ORPO > CPO ketika DataCollator shared** | Day 59: CPOTrainer dan SimPOTrainer share buggy DataCollator di beberapa TRL versions. ORPOTrainer menggunakan path terpisah → reliable. **Rule:** Jika CPO crash dengan DataCollator error, coba ORPOTrainer sebagai fallback. |
| **113** | **SSH readiness ping + fatal install guard** | Day 59: Jangan asumsikan SSH ready setelah `instance_running`. Ping 12x dengan backoff. Jika pip install fails → FATAL, jangan lanjut ke training. **Rule:** Pre-training checklist WAJIB include: (1) SSH connectivity test, (2) package install verification, (3) trainer import smoke test. |
| **114** | **Qwen2.5 tokenizer has NO BOS token — fix before TRL init** | Day 59: `tokenizer.bos_token_id is None` → TRL prepend `[None]` → `torch.tensor([None])` → crash. Fix: `if tokenizer.bos_token_id is None: tokenizer.bos_token_id = tokenizer.eos_token_id[0]`. **Rule:** WAJIB cek BOS token untuk semua model sebelum TRL init. Log tokenizer config di awal training. |
| **115** | **GGUF LoRA = deploy revolution** | Day 59: Adapter-only GGUF 80.7MB → Ollama ADAPTER directive. No 14GB base download. Deploy dalam hitungan menit. **Rule:** Default deploy path = GGUF LoRA. Full GGUF merge hanya untuk base model change atau external distribution. |
| **116** | **Pre-bake training images = eliminate env setup waste** | Day 59: 21 attempts, 18 untuk env setup. Actual training 186 detik. **Rule:** Build Docker image dengan training stack pre-installed. Future cycles: spawn → train → done dalam <5 attempts. |
| **117** | **Evolution-aware data must match expected response style** | Day 60: 5 evolution pairs menyebabkan score crash 0.825 → 0.568. Data style tidak aligned dengan cara model sebenarnya menjawab. **Rule:** Sebelum generate pairs untuk category baru, definisikan EXACT response style yang diinginkan. Test dengan baseline model dulu untuk understand natural response pattern. |
| **118** | **Creativity must be trained explicitly** | Day 60: Creative score 0.695 — tidak pernah dilatih. Identity training tidak otomatis menghasilkan creativity. **Rule:** Setiap capability yang diinginkan WAJIB punya dedicated training pairs. Jangan assume transfer learning dari identity. |
| **119** | **Tool-use discrimination > tool-use execution** | Day 60: Tool-use 0.797 — model bisa execute tools tapi kurang baik memutuskan KAPAN menggunakan tool vs KAPAN tidak. **Rule:** Tool-use pairs harus include discrimination scenarios: "when to use", "when NOT to use", "which tool to use". |
| **120** | **Training cost decreases 10x per cycle** | Day 60: Cycle 1 $1.50 → Cycle 2 $0.15 → Cycle 3 $0.16. Pipeline efficiency + GGUF LoRA deploy = dramatic cost reduction. **Rule:** Early cycles invest in pipeline. Later cycles reap cost benefits. Budget future cycles at $0.10-0.20 each. |
| **121** | **License: HMAC-SHA256 for Phase 1, Ed25519 for Phase 2 air-gapped** | Day 61-62: HMAC sufficient for cloud-verified licensing. BERLIAN tier (air-gapped) needs asymmetric: Tiranyx private key signs, client public key verifies. Rule: HMAC valid Phase 1; Ed25519 mandatory for air-gapped distribution. Roadmap: docs/LICENSE_CRYPTO_ROADMAP.md. |
| **122** | **Router prefix mismatch = silent 404** | Day 62: license router registered as /license but tested at /v1/license = 404. Rule: when adding router, test with EXACT production URL prefix. |
| **123** | **Docker BUILD required after code change, not just restart** | Day 62: edit Python code → docker compose restart = old code still running. Rule: code change = . Restart only for config/env changes. |
| **124** | **Env vars in docker-compose must be explicit per service** | Day 62: var in .env not auto-injected to all containers. Must declare in service.environment block. Rule: after add env var, verify . |
| **127** | **httpx lazy import inside function = NameError on module load** | Day 63: import inside function body OK if called normally, but asyncio.create_task before httpx loaded = NameError. Rule: all imports at top-level module. |
| **128** | **Gemini thinking mode silently drains token budget** | Day 63: Gemini 2.5 Flash with thinking enabled: 0/180 pairs generated (all tokens used for thinking traces). Rule: for batch generation use thinking budget=0 or non-thinking variant. |
| **129** | **Voice score (weight=30%) dominates weighted_avg — fix high-weight first** | Day 63: Cycle 4 failed because voice=0.739 despite identity=0.963. Rule: priority order = weight descending. identity(40%) -> voice(30%) -> evo-aware(15%) -> tool-use(10%) -> creative(5%). |
| **130** | **Targeted 50 pairs = +0.134 creative score** | Day 63: proof that targeted pair generation works. Rule: for each category missing gate, generate MINIMUM 50 targeted pairs. Formula: (current_score - gate_score) x 200 = estimated pairs needed. |
| **131** | **Voice/evo seed dedup: seed pool MUST be >= target pairs** | Day 64: 30 voice seeds x 4 repeats = still only 30 unique prompts after dedup. Rule: seed pool size >= target pairs. 60 unique pairs needs 60 unique seeds. Check unique count after generation. |
| **132** | **NEVER scp -r full adapter directory** | Day 64-65: scp -r full dir = adapter (155MB) + 3 checkpoints (3x325MB) = 700MB. 600s timeout exceeded. Rule: only SCP adapter_model.safetensors + adapter_config.json = 155MB total, 60-90s. Checkpoints = temporary, not needed. |
| **133** | **Ollama all-cores triggers hypervisor CPU throttle** | Day 65: Ollama runner at 687% CPU (7/8 cores) -> hypervisor throttles VM -> %st=93.8% steal -> inference 16x slower. FIX: OLLAMA_NUM_THREAD=4 + cpus=4.0 in docker-compose ollama service. 4 dedicated cores without throttle > 8 throttled cores. Watchdog cron every 15min. |
| **134** | **SSE message_id: pre-generate UUID before stream starts** | Day 65: Feedback endpoint needs server DB message UUID, but SSE `done` fires BEFORE `_persist_assistant_message` task completes. Fix: `assistant_msg_id = uuid.uuid4()` at TOP of `generate()` → pass to ALL `done` events → pass `message_id=assistant_msg_id` to persist → Message ORM uses it. Pattern: pre-assign → stream → persist with pre-assigned ID → client never needs re-fetch. |
| **135** | **React message state: add serverId separate from local id** | Day 65: Frontend messages use `Date.now()` as local `id` (React key). Server uses UUID. CANNOT replace `id` with server UUID → React key change → component re-mount → state reset (bad). Fix: add `serverId: null` to initial message state; `onDone(cid, serverMsgId)` sets `msg.serverId = serverMsgId`. Feedback buttons check `msg.serverId && convId` before rendering. Applies to any pattern where frontend needs server-assigned ID post-stream. |
| **136** | **promote_cycle5.sh: always test gate scripts against actual JSON schema** | Day 65: Script read `d.get('eval_summary', {}).get('weighted_avg')` but eval JSON uses flat `d['weighted_avg_cosine_sim']` and `d['category_means']` at top level. Fix: support both formats with format detection. Rule: when writing gate/promote scripts, run against sample output JSON first. "Written against spec" ≠ "matches actual JSON output". |
| **137** | **Eval MUST have retry logic for Ollama 500 — no retry = unfair rollback** | Day 65: 3 Ollama HTTP 500 errors during Cycle 5 eval (CPU steal 58-65%) → scored 0.000 each → -0.099 on weighted_avg → ROLLBACK. Est. weighted_avg without errors: 0.944 → PROMOTE. Fix: all eval scripts must wrap each Ollama call with max 3 retries, 10s sleep. Without this, infrastructure noise causes unfair rollbacks that waste Vast.ai credits + training time. |
| **138** | **Supplement dedup = seed diversity problem, not generation bug** | Day 66: generate_cycle6_supplement.py generated 160 tool-use/creative/evo-aware pairs but export dedup left only 77 unique (120-char prefix dedup removes same-prompt duplicates). Root cause: generator reused 28-30 seed prompts × 3-4 repeats = many same-prompt pairs. Fix for Cycle 7: per-call prompt VARIATION — generate 60 UNIQUE scenarios (different filenames, content, contexts) instead of repeating same 5 seeds × 12 times. |
| **139** | **Kimi CAI fallback — graceful degradation is acceptable** | Day 67: Kimi API unreachable → CAI pipeline falls back to Gemini-only single teacher. Quorum (2-teacher) is ideal but single-teacher fallback is acceptable. Both fail = Ollama fallback. Never block training on teacher availability. Monitor Kimi failure rate weekly; if consistently fails, swap to GPT-4o or Claude API as secondary teacher. |
| **140** | **interactions_feedback = 0 is expected, not a bug (test with real user first)** | Day 67 audit: 0 rows in interactions_feedback despite 65 conversations + thumbs UI deployed. Root cause: 53 registered users are mostly automated test accounts from early development (Day 1-30). Real beta users = minimal. Frontend thumbs requires `msg.serverId && convId` which only works post-SSE-done-event. Rule: ZERO rows = "no real users triggered it yet", not "it's broken". Always E2E test flywheel manually (real login → chat → 👎 → verify DB row) before declaring broken. |
| **141** | **Delete rollbacked models same session — 4.8GB each** | Day 67: Found migancore:0.1, 0.2, 0.4, 0.5 still in Ollama = ~19GB wasted. After ROLLBACK decision, delete candidate model within same session. Only keep: production model + base qwen2.5. Protocol: post every ROLLBACK = `docker exec ado-ollama-1 ollama rm migancore:0.X` immediately. |
| **142** | **Resource audit pattern — run before every cycle plan** | Day 67: 30-second audit revealed 3 actionable findings: interactions_feedback=0, 68% preference_pairs unused, SIDIX 1,458 free pairs. Commands: `SELECT COUNT(*) FROM preference_pairs; SELECT COUNT(*) FROM interactions_feedback;` + `df -h` + `ollama list`. Create RESOURCE_AUDIT_DAY{N}.md as standard checkpoint doc every cycle. |

---

## 📋 SPRINT TEMPLATE (gunakan tiap day)

```markdown
# Day N Plan — <Title>
**Date:** YYYY-MM-DD
**Triggered by:** <user request quote>
**Research:** <agent dispatched? sources?>

## 1. CONTEXT (state morning)
| Item | State |
|------|-------|
| API | vX.Y.Z |
| DPO pool | NNN |
| Bulan N spend | $X.XX / $30 |
| Lessons | NN |

## 2. RESEARCH SYNTHESIS
<3-5 bullet points dari riset>

## 3. TASK LIST (H/R/B framework)
### A1 — <task>
**Hipotesis:** ...
**Risk:** LOW/MED/HIGH
**Benefit:** ...
**Effort:** ...
**KPI:** ...

## 4. KPI Day N
| Item | Target | Verifikasi |

## 5. BUDGET PROJECTION
<$ items + cumulative>

## 6. EXIT CRITERIA
- [ ] ...

## 7. SCOPE BOUNDARIES (per VISION)
DON'T: ...
DO: ...

## 8. LESSONS APPLIED + ANTICIPATED
NN. ...

## 9. POST-DAY-N LOOKAHEAD
```

Then closing: `docs/DAY{N}_RETRO.md` + `memory/day{N}_progress.md` + update `memory/MEMORY.md` index.

---

## 🧠 STRATEGIC COMPASS (jangan lupakan)

Per `docs/VISION_DISTINCTIVENESS_2026.md`:

**3 REAL MOATS** (yang membuat MiganCore beda dari Cline/Open WebUI/mem0):
1. Closed identity-evolution loop (CAI quorum + SimPO + SOUL.md + genealogy)
2. Modality-as-tool routing (image/voice/web/file via tools, MCP-portable)
3. ADO modular architecture — agent yang bisa SURVIVE model swap

**STOP LIST:** wrapper tools, chat UI polish, generic memory features (semua sudah ada Cline/Open WebUI/mem0 — commodity)

**DOUBLE DOWN:** identity preservation eval, hot-swap demo, Dream Cycle (Innovation #4 — bold move)

---

## 💰 BUDGET DISCIPLINE

| Pool | Cap | Note |
|------|-----|------|
| Bulan 2 (operational) | $30 | spent ~$1.44 (4.8%) |
| RunPod Cycle 1 | $7 | unspent |
| RunPod Cycle 2 | $7 | unspent |
| Emergency | $2 | reserved |

**JANGAN spawn pod RunPod tanpa user GO eksplisit.** Pre-flight $0 = OK. Actual training spend = ASK first.

---

## 🛑 ANTI-PATTERNS (DON'T)

1. **Don't run heavy command on VPS without checking other tenants** (sidix/mighantect/ixonomic/tiranyx-co-id)
2. **Don't `pkill -9` on shared VPS** — bisa bunuh sshd-related, putus session
3. **Don't asumsi `localhost:11434` = migancore Ollama** — itu mungkin host daemon dari sidix project
4. **Don't deploy `docker compose up -d --build`** while synthetic gen running — auto-resume mungkin gagal fire (Lesson #45)
5. **Don't push commit dengan API key inline** — GitHub secret-scanning akan tolak (gunakan `$VAR_NAME` placeholder)
6. **Don't add tool ke `skills.json` tanpa juga update `agents.json` `default_tools`** (Lesson #46/#48)
7. **Don't trigger Cycle 1 spot pod hanya** — community spot supply tight, fallback ke SECURE non-spot
8. **Don't biarkan synth gen jalan terus tanpa rate-limit** — saturasi Ollama, blokir user chat (Lesson #54)

---

## 🔁 SESSION CLOSE-OUT (sebelum break)

1. `git status` — pastikan zero uncommitted
2. `git log --oneline -5` — pastikan semua pushed
3. Tulis `docs/DAY{N}_RETRO.md` (ATAU `RESUME_DAY{N}_TO_DAY{N+1}.md` jika incomplete)
4. Tulis `memory/day{N}_progress.md`
5. Update `memory/MEMORY.md` entry
6. Update `docs/AGENT_HANDOFF_MASTER.md` log
7. Final state snapshot:
   - API health version
   - DPO count
   - Container statuses
   - Cumulative spend
   - Outstanding action items + WHO is GO/NO-GO blocker
8. **Tell user**: clear ASK if user GO needed; else clear NEXT-SESSION pickup command

---

## 📞 OWNER PROFILE (Fahmi Ghani)

- **Founder & Owner** PT Tiranyx Digitalis Nusantara (brand: Tiranyx) — visioner, non-technical
- **Concept:** iterasi → kognitif → optimasi → inovasi
- **Komunikasi:** Bahasa Indonesia primary
- **Wants:** comprehensive docs, no context loss, partner-honest assessment
- **Tone:** treat as engineering partner who needs honest signal (good AND bad)
- **Concerns:**
  - Time + money waste from re-doing work
  - Patch-on-patch instead of root cause
  - Anthropic should know about coordination issues
- **Does NOT want:** repeated mandatory protocol explanation in every message (THAT'S WHY THIS FILE EXISTS)

---

## 🎯 IF YOU'RE READING THIS FOR FIRST TIME

1. Take 15 min to read the 4 priority docs above
2. Run the 3-command health check
3. Check `memory/MEMORY.md` last 3 day entries
4. **Acknowledge to user** that you've read this onboarding before doing ANY task
5. Start with state assessment, not action

**Remember:** the user has 50+ days of investment. Every wrong assumption = real $ + real time wasted. **Read first, act second.**

---

**This file is THE permanent protocol. Update only with explicit user approval. Never delete.**

| **143** | **SSH blocking call timeout must exceed actual training time** | Day 67: cycle6_orpo_vast.py timeout=7200s (2hr) < actual training time (3.5hr on Q RTX 8000). At 16:02 UTC, subprocess.run fires TimeoutExpired, kills SSH, SIGHUP may kill training. Fix: timeout=14400 (4hr) + try/except to NOT delete instance on timeout. Also: use detached mode (nohup &) + separate polling script (vast_recovery.sh). Three-layer safety: tmux guard (restart if killed) + VPS downloader (periodic pull) + wait loop (trigger post-pipeline). |
| **144** | **Always list Vast.ai instances FIRST — orphan check before any work** | Day 67: instance 36263704 (A40) from prior session ran 16hr = $5.72 wasted. First command of any agent session that might use Vast.ai: `curl .../instances/` → list all → delete orphans. Never assume clean state. Budget burn from inaction is silent. |
