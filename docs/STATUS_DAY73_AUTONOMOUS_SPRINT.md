# STATUS_DAY73_AUTONOMOUS_SPRINT.md
**MiganCore ADO — Day 73 Status Document**
Generated: 2026-05-14 | Version: 0.5.x | Branch: master

---

## Section 1: System Architecture Overview

### Production Stack
- **VPS:** 72.62.125.6 (shared aaPanel host, 8 vCPU / 32 GB RAM / 400 GB SSD)
- **API:** https://api.migancore.com (FastAPI via nginx reverse proxy, port 8000 internal)
- **App:** https://app.migancore.com (nginx static + SSE streaming frontend)
- **Landing:** https://migancore.com

### Docker Containers (docker-compose.yml)
| Service | Image | Purpose |
|---------|-------|---------|
| `api` | Custom build (FastAPI) | Core brain API, tool executor, KG extractor |
| `postgres` | pgvector/pgvector:pg16 | Primary DB — all tenant data, preference pairs, KG |
| `redis` | redis:7.2-alpine | JWT refresh cache, tool_cache TTL, rate limiting |
| `qdrant` | qdrant/qdrant:v1.12.0 | Vector memory — episodic + hybrid BM42 search |
| `ollama` | ollama/ollama:0.6.5 | LLM inference — serves migancore:0.7c |
| `letta` | letta/letta:0.6.0 | Long-term memory layer (optional profile: memory) |

### Production Model
- **Active:** `migancore:0.7c` (DEFAULT_MODEL in `api/config.py`)
- **Base:** Qwen2.5-7B-Instruct + LoRA adapter, ORPO trained
- **HF Adapter:** `Tiranyx/migancore-7b-soul-v0.7c`
- **Format:** GGUF Q4_K_M served via Ollama
- **Rule:** All cycles retrain from previous MiganCore adapter, never from raw Qwen base (Lesson #3)

---

## Section 2: Autonomous Growth Loop — Day 73 Deliverables

### 2.1 Knowledge Graph Extractor (`api/services/kg_extractor.py`)
- **Trigger:** Fire-and-forget `asyncio.create_task(extract_and_store(...))` after every streaming response completes (`api/routers/chat.py` line 640)
- **Extraction:** Local Ollama call — 18s timeout, temperature 0, max 5 entities + 4 relations per response, text capped at 1800 chars
- **Entity types:** PERSON, ORG, PLACE, CONCEPT, PRODUCT, SKILL
- **Storage:** `chat_entities` (upsert by name+tenant, increments `mention_count`) and `chat_relations` tables (migration 028)
- **Recall:** `recall_for_prompt()` called at chat.py line 149 — queries top entities by `mention_count`, matches against current user message, prepends `[Konteks yang diketahui]` block into system prompt
- **Cost:** Zero API cost (local Ollama only)

### 2.2 Auto-Training Watchdog (`api/services/auto_train_watchdog.py`)
- **Start:** `asyncio.create_task(auto_train_loop())` in `api/main.py` lifespan step 9c
- **Check interval:** Every 3 hours (`CHECK_INTERVAL_S = 3 * 3600`)
- **Trigger conditions:** `real_conversation` preference pairs >= 80 AND days_since_last_train >= 3
- **Training target:** Vast.ai A100/A40 — ORPO on 70% targeted synthetic + 30% real conversation pairs
- **Budget cap:** Hard `$3.00` per auto-trigger (`AUTO_TRAIN_BUDGET_CAP`)
- **Max frequency:** 1 auto-training per day
- **Base model:** `Tiranyx/migancore-7b-soul-v0.7c` (never Qwen base)
- **Post-train:** Writes `last_success.json` with `cycle_id`, `hf_repo`, `completed_at`; triggers auto eval via cron
- **Promote gate:** `weighted_avg >= 0.92` = auto-promote; `>= 0.88 + identity >= 0.90` = proposal for Fahmi
- **Audit trail:** Creates `DevOrganProposal` DB entry for every triggered run

### 2.3 Daily Harvest Cron (`scripts/daily_harvest.sh`)
- **Schedule:** `0 2 * * *` (02:00 UTC)
- **Method:** `docker exec ado-postgres-1 psql -U ado` — bypasses RLS as superuser
- **Query:** Extracts user→assistant message pairs: user >= 15 chars, assistant >= 60 chars, no tool calls, first message is from user
- **Output:** JSONL `live_harvest_YYYYMMDD_HHMM.jsonl` → `/opt/ado/data/workspace/`
- **Import:** Calls `training/import_real_pairs.py` — stores pairs as `source_method='real_conversation'` in `preference_pairs`
- **Log:** `/opt/ado/data/training/auto/harvest_cron.log`

### 2.4 Auto Eval + Hot-Swap (`scripts/run_auto_eval.sh`)
- **Schedule:** `0 4 * * *` (04:00 UTC)
- **Check:** Reads `last_success.json` — skips if `eval_done=True` or training > 18 hours old
- **GGUF pipeline:** Downloads adapter from HuggingFace → merge with base → convert F16 GGUF → quantize Q4_K_M — all using `/opt/llama.cpp/` on VPS host (no 14 GB download, Lesson #85)
- **Candidate model:** Creates `migancore:candidate` in Ollama
- **Eval:** Runs `eval/run_identity_eval.py` — 20 prompts, weighted gate
- **PROMOTE:** `weighted_avg >= 0.80` → updates `.env DEFAULT_MODEL` + restarts API container
- **ROLLBACK:** Score below gate → removes candidate, keeps production model
- **Log:** `/var/log/auto_eval.log`

---

## Section 3: Tool Registry (29 tools)

Defined in `api/services/tool_executor.py` `TOOL_REGISTRY` + `COGNITIVE_TOOLS` from `api/services/tools_cognitive.py`:

**Web & Search**
`web_search`, `web_read`, `onamix_get`, `onamix_search`, `onamix_scrape`, `onamix_post`, `onamix_crawl`, `onamix_history`, `onamix_links`, `onamix_config`, `onamix_multi`

**File & Output**
`read_file`, `write_file`, `export_pdf`, `export_slides`

**AI & Multimodal**
`generate_image`, `analyze_image`, `text_to_speech`

**Memory**
`memory_write`, `memory_search`

**Code & Python**
`python_repl`, `run_python`

**Cognitive (Day 67 — `tools_cognitive.py`)**
`think`, `synthesize`, `teacher_ask`, `multi_teacher`, `calculate`, `extract_insights`, `knowledge_discover`

Note: `web_search` and `python_repl` retained in registry for back-compat but schemas were dropped from `skills.json` Day 48.

---

## Section 4: Cron Schedule

| Time (UTC) | Script | Purpose |
|------------|--------|---------|
| 02:00 daily | `scripts/daily_harvest.sh` | Harvest live conversation pairs from DB |
| 03:00 daily | `scripts/backup_models.sh` | Ollama model backup |
| 04:00 daily | `scripts/run_auto_eval.sh` | Eval last training + hot-swap if PROMOTE |
| Every 6 hours | `api/services/distill_cron.sh` | Teacher API distillation (multi-teacher) |
| Every 3 hours | `auto_train_watchdog` (in-process) | Check thresholds, trigger Vast.ai training |

---

## Section 5: Training Data State

| Metric | Value |
|--------|-------|
| Total `preference_pairs` in DB | ~3,500+ |
| `real_conversation` pairs | 93 |
| Watchdog trigger threshold | 80 real pairs |
| Watchdog status | **ARMED** — threshold already crossed |
| `chat_entities` / `chat_relations` | Accumulating from every live chat |
| Training cycles completed | 7c (Cycle 1 through 7c) |
| HuggingFace org | `Tiranyx/` |

Cycle history (condensed):
- Cycle 1: UltraFeedback DPO → identity failed (rollback)
- Cycle 2: Identity-anchored ORPO → 0.8744 weighted (promoted, migancore:0.2)
- Cycle 3: +685 pairs → 0.9082 (promoted, migancore:0.3)
- Cycle 4: Domain pairs → voice drift (rollback)
- Cycle 5: Identity+voice fix → promoted
- Cycle 6: +engineering/UMKM/legal/creative → promoted
- Cycle 7c: Current production (migancore:0.7c)

---

## Section 6: What's Missing / Next Sprint

**High Priority**
- `generate_chart` tool — data visualization via matplotlib/plotly
- `read_pdf` tool — PDF ingestion for knowledge tasks
- `research_deep` tool — multi-step web research with synthesis
- Per-user KG isolation — currently all KG is per-tenant, not per-user

**Medium Priority**
- ONAMIX Node.js 6-tool verification — already in Dockerfile, needs E2E test of `onamix_post/crawl/history/links/config/multi`
- MCP server expansion — `api.migancore.com/mcp/` currently serves 7 tools; expand to full tool set
- Auto-eval gate tightening — current PROMOTE at `0.80`; raise to `0.88` once auto-pipeline is battle-tested

**Roadmap (Phase 2)**
- Clone mechanism (GAP-01): per-client Docker template + license isolation
- Asymmetric key licensing (GAP crypto roadmap): Ed25519 for BERLIAN air-gapped tier (docs/LICENSE_CRYPTO_ROADMAP.md)
- Dev Organ full loop: observe → diagnose → propose → sandbox → test → promote → monitor

---

## Section 7: Critical File Map

| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI lifespan — starts all background tasks including auto_train_watchdog (step 9c) |
| `api/routers/chat.py` | SSE streaming — wires KG recall into system prompt (line 149) and KG extraction after response (line 640) |
| `api/services/auto_train_watchdog.py` | 3-hour loop — monitors real pair count, triggers Vast.ai ORPO training |
| `api/services/kg_extractor.py` | Entity/relation extraction from every chat response; `recall_for_prompt()` for context injection |
| `api/services/tool_executor.py` | All tool handlers + TOOL_REGISTRY; Dev Organ failure signal emission |
| `api/services/tools_cognitive.py` | Cognitive tools: think, synthesize, teacher_ask, multi_teacher, calculate, run_python, extract_insights, knowledge_discover |
| `api/services/distillation.py` | Multi-teacher distillation pipeline (Kimi/Claude/GPT/Gemini) |
| `api/services/contracts.py` | Boot validator + safe_task + TaskRegistry watchdog + output contracts (Day 47) |
| `api/services/license.py` | HMAC-SHA256 license mint/validate; tiers BERLIAN/EMAS/PERAK/PERUNGGU |
| `api/config.py` | Settings — `DEFAULT_MODEL = "migancore:0.7c"` is production model pointer |
| `docker-compose.yml` | 6-service stack definition; resource limits; nginx proxy handled by aaPanel |
| `scripts/daily_harvest.sh` | Cron 02:00 UTC — dumps live DB conversations via superuser psql |
| `scripts/run_auto_eval.sh` | Cron 04:00 UTC — eval + hot-swap pipeline using llama.cpp on VPS host |
| `scripts/backup_models.sh` | Cron 03:00 UTC — Ollama model backup |
| `training/import_real_pairs.py` | Imports harvested JSONL to `preference_pairs` as `source_method='real_conversation'` |
| `training/harvest_live_conversations.py` | Harvests live DB conversations for training dataset construction |
| `training/cycle7c_orpo_vast.py` | Vast.ai ORPO training script for current cycle |
| `training/export_cycle7_dataset.py` | Builds training JSONL from DB (70% synthetic + 30% real mix) |
| `eval/run_identity_eval.py` | 20-prompt identity eval; gates: weighted_avg, identity, voice, tool-use categories |
| `docs/AGENT_ONBOARDING.md` | Permanent agent entry point — lessons, topology, anti-patterns (read every new session) |

---

## Appendix: Key Lessons Active

- **#3** Never retrain from Qwen base — always from previous MiganCore adapter
- **#57** STOP adding tools until existing ones are all verified E2E
- **#59** Verify pod DELETE via API list, never trust 204 alone
- **#60** SECURE cloud billing starts at allocation, not at boot
- **#83** Eval gate is absolute — rollback immediately if below floor, no exceptions
- **#129** Voice is 30% of weighted_avg — fix high-weight categories first
- **#130** Targeted 50 pairs per category → measurable +0.134 improvement proven

---

*End of STATUS_DAY73_AUTONOMOUS_SPRINT.md — total 185 lines*
