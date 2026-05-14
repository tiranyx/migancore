# Kimi — VPS Access & Deploy Handoff

**Date written:** 2026-05-15 (Day 74)
**Audience:** Kimi Code CLI (or any AI agent picking up from Claude/Codex)
**Goal:** Connect to MiganCore production VPS, deploy a commit, run QA, without tripping the same bugs I (Claude) tripped earlier today.

---

## 1. SSH access

**Use these exact values. Do not guess.**

```bash
# Connection
Host:           72.62.125.6
User:           root
Key:            ~/.ssh/sidix_session_key

# One-shot
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 'whoami && hostname'
```

**Common mistake (Claude did this earlier):** confusing the IP with another VPS at `31.97.221.115`. That's NOT this VPS — it's a Hostinger box for another project. Always use `72.62.125.6`.

---

## 2. Repo path on VPS

**The repo lives at `/opt/ado` — NOT `/opt/ado/migancore`.**

```text
/opt/ado/                  ← git repo root (origin = git@github.com:tiranyx/migancore.git)
  api/                      ← FastAPI source
  config/                   ← agents.json + skills.json
  data/                     ← workspace, postgres, redis, qdrant, ollama
  docker-compose.yml
  docs/                     ← strategic docs + handoffs
  frontend/                 ← chat.html, admin_backlog.html, sw.js
  migrations/               ← raw SQL + alembic
  scripts/                  ← deploy + cleanup helpers
```

Other repos on the same VPS (do not touch unless asked):
- `/opt/sidix/`        — SIDIX research tools (used by ONAMIX bind-mount)
- `/opt/llama.cpp/`    — llama.cpp build tools

---

## 3. Production state (snapshot when this doc was written)

```text
HEAD:              896b14c  (fix(chat): empty-stream guard)
Branch:            main
Model:             migancore:0.7c   (DO NOT promote 0.7e without identity+latency eval)
AUTO_TRAIN_MODE:   proposal         (DO NOT flip to auto without Fahmi's explicit OK)
Build day:         Day 74
Containers:        api, ollama, postgres, redis, qdrant, letta — all healthy
```

Verify any time:

```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 \
  'curl -sS http://127.0.0.1:18000/health'
```

---

## 4. Deploy a new commit (the working recipe)

```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 'bash -s' <<'EOF'
set -e
cd /opt/ado
git fetch origin
git pull --ff-only origin main

# CRITICAL: pass build metadata so /health stops saying "unknown"
export BUILD_COMMIT_SHA=$(git rev-parse --short HEAD)
export BUILD_DAY="Day 74"
export BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

docker compose build api
docker compose up -d api

# Wait for healthcheck
sleep 18
curl -sS http://127.0.0.1:18000/health
EOF
```

If you skip the `BUILD_COMMIT_SHA` export, `/health` returns `commit_sha: "unknown"` and you won't be able to tell which deploy is live. Codex audit item 4 closed this — don't re-open it.

---

## 5. Admin auth + QA recipes

```bash
# Admin key (server-side env)
K=$(ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 \
  'grep ^ADMIN_SECRET_KEY /opt/ado/.env | cut -d= -f2')

# Quick QA: artifact preview-only (no DB write)
curl -sS -X POST https://api.migancore.com/v1/artifacts/preview \
  -H "Content-Type: application/json" -H "X-Admin-Key: $K" \
  -d '{"prompt":"smoke test","artifact_type":"markdown","title":"smoke"}' \
  | jq '.artifact_id, .safe_to_save'

# Artifact submit → finalize flow (writes file to workspace)
# Submit returns proposal_id; finalize that with verdict=approved
SUB=$(curl -sS -X POST https://api.migancore.com/v1/artifacts/submit \
  -H "Content-Type: application/json" -H "X-Admin-Key: $K" \
  -d '{"prompt":"kimi handoff test","artifact_type":"markdown","title":"kimi-test"}')
PID=$(echo "$SUB" | jq -r '.proposal.id')

curl -sS -X POST "https://api.migancore.com/v1/artifacts/finalize/$PID" \
  -H "Content-Type: application/json" -H "X-Admin-Key: $K" \
  -d '{"verdict":"approved"}' | jq '.status, .path'

# Verify file landed on host
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 \
  'ls -la /opt/ado/data/workspace/artifacts/'
```

---

## 6. Known gotchas — don't trip these

### A. Workspace permission (entrypoint TODO)

The api container runs as `ado` (uid=999). Host dir `/opt/ado/data/workspace` is owned by `root:root`. New subdirs need `chown 999:999` so the container can write. **One-time fix when adding a new subdir:**

```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 \
  'mkdir -p /opt/ado/data/workspace/<newdir> && chown -R 999:999 /opt/ado/data/workspace/<newdir>'
```

A permanent fix in `api/entrypoint.sh` is on the TODO list but not shipped yet.

### B. Cache key scope (already fixed at eaf8bfd)

`services/response_cache.py` hashes on `agent_id + message`, NOT `system_prompt + message`. Don't revert that — system_prompt churns from episodic memory each turn and would defeat the cache.

### C. Tool relevance threshold (already shipped at e767992 + 19dcb57)

`services/tool_relevance.py` returns `[]` (empty list, no memory_*) when top semantic score < 0.60. This forces brain to answer organically rather than enter Ollama's tool-call mode at low confidence (which times out 90s on CPU 7B).

`OLLAMA_TOOL_CALL_TIMEOUT_S = 90` (env override). Don't bump it without a reason — 180s default was the bug we just fixed.

### D. Empty-stream guard (896b14c)

If Phase B (plain stream after tool fallback) yields 0 chunks because Ollama is busy serializing requests (`OLLAMA_NUM_PARALLEL=1`), the response is replaced with a friendly Indonesian retry message. Don't remove this guard — it's the last line of defense against blank bubbles.

### E. UnboundLocalError trap

Don't assign to a variable in a nested async generator if that name is also defined in the enclosing scope. Use `nonlocal` or use a different local name. I (Claude) tripped this at commit 296fcac and fixed at 28fae27. Mark of shame.

### F. Stash management

The VPS used to have 5 historical stashes (Codex's pre-cleanup backups). I audited + dropped all 5 today, after archiving each as a `.patch` file at `/opt/ado/.archived_stashes_20260514_2003/`. If you need to recover something: `git apply /opt/ado/.archived_stashes_20260514_2003/stash_N.patch`. That dir is gitignored.

---

## 7. Background daemons (running on VPS, hands-off unless debugging)

- `auto_train_watchdog` — every 3 hours, checks if real_pairs threshold met (currently 93 ≥ 80). In `proposal` mode it ONLY writes a row to `dev_organ_proposals`; never triggers Vast.ai. Don't switch to `auto` mode without Fahmi.
- `daily_growth_journal_loop` — fires once per 24h, writes a "belajar/gagal/perlu alat/usul upgrade" reflection to `nafs` bucket via memory_write. Viewable in `https://app.migancore.com/backlog.html` → 🌱 REFLEKSI tab.

---

## 8. Things you MUST NOT do

- **Don't promote `migancore:0.7e`.** Production stays at `0.7c` until identity + latency evals say otherwise.
- **Don't flip `AUTO_TRAIN_MODE` to `auto`** — that re-enables autonomous Vast.ai GPU training, which violates Fahmi's biomimetic doctrine (tools/training = vitamin, not oxygen).
- **Don't `git push --force` to main.** Production VPS reflog should stay clean.
- **Don't run `docker compose down` without checking `keep_alive` state on Ollama** — model offload then reload eats 5-15s on next chat.
- **Don't commit secrets.** API keys live in `/opt/ado/.env` and `/opt/secrets/migancore/`. Never paste them in chat or commit.

---

## 9. Where to look for context

| What | Where |
|---|---|
| Latest sprint state | `/opt/ado/docs/HANDOFF_DAY73_CODEX_TO_CLAUDE_2026-05-14.md` |
| Day 74 changes audit | `~/.claude/projects/C--migancore/memory/day74_artifact_save_perf_qa.md` (on Fahmi's laptop) |
| Architecture map | `/opt/ado/docs/ORGANISM_ARCHITECTURE_MAP.md` |
| Build metadata | `git rev-parse --short HEAD` on VPS + `/health` |
| Backlog UI | `https://app.migancore.com/backlog.html` (admin key required) |
| Memory index | `~/.claude/projects/C--migancore/memory/MEMORY.md` (Fahmi's laptop) |

---

## 10. If something breaks

Cheap diagnostics:

```bash
# Container state
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 \
  'docker compose -f /opt/ado/docker-compose.yml ps'

# Recent errors
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 \
  'docker compose -f /opt/ado/docker-compose.yml logs --since 10m api 2>&1 | grep -iE "error|exception|timeout|fail" | tail -20'

# Resource pressure
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 \
  'docker stats --no-stream'

# Rollback to previous deploy
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 'bash -s' <<'EOF'
cd /opt/ado
PREV=$(git log -n 2 --pretty=%H | tail -1)
git reset --hard $PREV
export BUILD_COMMIT_SHA=$(git rev-parse --short HEAD)
docker compose build api && docker compose up -d api
EOF
```

Never `--force` unless Fahmi greenlights it.

---

Good luck. Read **section 2** carefully — the wrong-IP / wrong-path mistake costs a full session of confused errors.
