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

# 2. Read 4 docs (priority order, total ~15 min):
#    a) docs/AGENT_ONBOARDING.md (THIS FILE)
#    b) docs/ENVIRONMENT_MAP.md (VPS topology — CRITICAL, shared with 4 other projects)
#    c) docs/RESUME_DAY*_TO_DAY*.md (latest break-state checkpoint)
#    d) docs/VISION_DISTINCTIVENESS_2026.md (strategic compass)

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

Top 6 yang HARUS diingat (53 lessons total — semua di MEMORY.md per-day notes):

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
