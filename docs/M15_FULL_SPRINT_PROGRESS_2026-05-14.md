# M1.5 Full Sprint Progress - 2026-05-14

Owner: Codex  
Timezone: Asia/Jakarta  
Scope: M1.5 Autonomy Hardening, starting from `docs/MIGANCORE_AI_HANDOFF_2026-05-12.md`

## Process Log

### 00:42 WIB - Sprint start
- Read the handoff direction and transfer checklist.
- Checked root repo and `migancore` sub-repo git status.
- Confirmed `migancore` sub-repo is clean on `main...origin/main`; root repo has unrelated existing local files.

### 00:42 WIB - P0 ONAMIX root cause
- Inspected `api/Dockerfile`, `docker-compose.yml`, `api/services/onamix_mcp.py`, `api/services/tool_executor.py`, and `config/skills.json`.
- Found runtime image explicitly omitted Node.js while ONAMIX requires `/usr/bin/node`.
- Found `config/skills.json` exposes MCP-only ONAMIX tools, but `TOOL_REGISTRY` still had those handlers commented out.

### 00:42 WIB - P0 ONAMIX patch
- Added `nodejs` and `npm` to API runtime image.
- Added entrypoint bootstrap for mounted `/app/hyperx` dependencies when `node_modules` is missing.
- Made ONAMIX path and Node binary configurable via `ONAMIX_DIR`, `ONAMIX_BIN`, `ONAMIX_MCP_BIN`, and `NODE_BIN`.
- Re-enabled ONAMIX MCP-only handlers in `TOOL_REGISTRY` so schemas and executor are aligned.

## Current Status

- P0 ONAMIX: patched; static verification passed, Docker build blocked by local Docker daemon not running.
- P1 auto-training trigger: patched; static verification passed.
- P1 knowledge graph writes: patched; static verification passed.
- P2 Kimi rotation: patched; Kimi disabled by default until explicitly re-enabled.

## Verification Log

- Passed: Python `py_compile` for ONAMIX files.
- Passed: AST parse and static registry check for all 9 `onamix_*` tools.
- Passed: Python `py_compile` for all touched Python files.
- Passed: AST/static checks for ONAMIX, training trigger, KG writer, and Kimi gating.
- Blocked: full pytest because local Python environment is missing repo dependencies (`structlog`, `pytest`).
- Blocked: Docker build because Docker Desktop daemon is not running.

### 00:43 WIB - P1 auto-training trigger root cause
- `config.py` already had `TRAINING_AUTO_TRIGGER`, pair thresholds, provider, and GPU API key settings.
- `docker-compose.yml` did not pass those training settings into the API container.
- `distillation_worker.py` stopped at a TODO after detecting threshold readiness.
- `training_orchestrator.py` used hardcoded `/opt/ado/data/training` paths despite the container mount being `/app/data/training`.

### 00:43 WIB - P1 auto-training patch
- Added training env passthrough to `docker-compose.yml`.
- Moved orchestrator state/export/deploy paths to `settings.TRAINING_OUTPUT_DIR`.
- Replaced distillation TODO with `maybe_auto_trigger_training()`.
- Auto-trigger now requires both SFT and DPO thresholds, respects `TRAINING_AUTO_TRIGGER`, and blocks clearly if provider credentials are missing.

### 00:44 WIB - P1 knowledge graph bridge
- Added `api/services/knowledge_graph.py`.
- Connected `fact_extractor.maybe_update_knowledge_block()` to also write extracted memory facts into `kg_entities`.
- Added `kg_relations` edges from `agent:{letta_agent_id}` to each `memory_fact`.
- KG write is non-blocking from a reliability standpoint: it logs and returns an error report instead of breaking chat memory updates.

### 00:44 WIB - P2 Kimi rotation
- Added `KIMI_ENABLED` setting and compose passthrough.
- `teacher_api.list_available_teachers()` now excludes Kimi unless both `KIMI_API_KEY` and `KIMI_ENABLED=true` are set.
- This prevents suspended/empty-balance Kimi from wasting quorum attempts; after recharge, set `KIMI_ENABLED=true`.

### 00:50 WIB - Release preflight
- Ran `git pull --rebase --autostash origin main`.
- Result: already up to date; no remote conflicts before commit.

### 00:55 WIB - Production QA finding
- Deployed commit `5bab088` to VPS and API became healthy.
- ONAMIX validated: Node/NPM present, `/app/hyperx/bin/hyperx.js` present, `/app/hyperx/bin/hyperx-mcp.js` present, `onamix.mcp.lifespan_started` logged.
- Found startup contract errors: `core_brain` and `aria_template` referenced `web_search` and `python_repl`, but `skills.json` had no schemas for those IDs.
- Patched `config/skills.json` to restore lightweight schemas for `web_search` and `python_repl`.
