# MIGANCORE — AGENT ONBOARDING PROTOCOL (PERMANENT)
**Owner:** Fahmi Wol (tiranyx.id@gmail.com) | non-technical founder/visioner
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

Top 6 yang HARUS diingat (83 lessons total — semua di MEMORY.md per-day notes):

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

## 📞 OWNER PROFILE (Fahmi Wol)

- **Non-technical founder** — visioner, not coder
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
