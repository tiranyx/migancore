# Sprint Day 73 Codex Optimization Log

Date: 2026-05-14
Owner: Codex
Status: Deployed to production API

## Direction

Fahmi clarified the operating doctrine: MiganCore should grow like an organism
being educated, not like a GPU job being forced to mature. Training is vitamin,
not oxygen. The system should first learn through interaction, reflection,
memory, tool practice, proposal review, and safe promotion gates.

## Changes Shipped

1. Auto-training watchdog moved to proposal mode by default.
   - `AUTO_TRAIN_MODE=proposal`
   - Thresholds create `dev_organ_proposals` rows.
   - No Vast.ai/GPU trigger unless explicitly switched to `AUTO_TRAIN_MODE=auto`.

2. Production model default locked to `migancore:0.7c`.
   - `DEFAULT_MODEL=migancore:0.7c`
   - `OLLAMA_DEFAULT_MODEL=migancore:0.7c`
   - Prevents accidental re-promotion of `0.7e` while alignment is still being reviewed.

3. Casual chat fast path.
   - Greetings and short acknowledgements route to zero tools.
   - Full memory, Letta, KG, CAI, and tool loops are skipped for low-information social turns.
   - Added reflex response path for tiny greetings/thanks/acks.

4. Daily growth journal scheduler verified.
   - `reflection.daily.scheduled`
   - Intended as a growth loop: what was learned, what failed, what tool is needed, what upgrade is proposed.

5. VPS worktree cleanup.
   - Dirty VPS state was snapshotted and stashed.
   - Recovery stash: `stash@{0}: codex-pre-ca3fcc9-deploy`.

## QA Evidence

Production health:

```text
status=healthy
version=0.5.16
model=migancore:0.7c
commit_sha=c309771
```

Watchdog:

```text
Auto-training watchdog started (mode=proposal)
real_pairs=93 threshold met
PROPOSAL created
No Vast/GPU trigger
```

Latency progression for casual chat:

```text
Before audit:              ~139s
Tool schema skipped:        44.5s
Lightweight casual path:     7.5s first, 2.5s warm
Reflex sync path:            0.03s - 0.05s
Reflex stream path:          0.08s
```

## Current Doctrine

Use a layered nervous system:

```text
reflex -> lightweight cognition -> full cognition + tools -> proposal -> sandbox -> promotion
```

Reflex handles tiny social turns. Lightweight cognition handles simple answers.
Full cognition handles tasks, memory, tools, research, coding, and decisions.
Training only happens after proposal review and clear evidence.

## Handoff Warning

Do not promote `migancore:0.7e` again until identity, latency, and behavioral
evals prove it is better than `0.7c`. Do not switch `AUTO_TRAIN_MODE=auto`
unless Fahmi explicitly approves a GPU training run. Current direction is
biomimetic education first, model churn later.

## Day73 Safe Deploy Follow-up

After the Jurnal & Proposal panel went live, Codex added two guardrails so the
same deployment mistake does not repeat:

1. `scripts/vps_deploy_api_safe.sh`
   - Runs `git pull --ff-only origin main`.
   - Exports `BUILD_COMMIT_SHA`, `BUILD_DAY`, and `BUILD_TIME` before recreating
     the API container.
   - Keeps `/health` and `/v1/system/status` aligned with the deployed commit.

2. `scripts/qa_day73_panel_live.py`
   - Verifies health, model lock, build metadata alignment, backlog panel HTML,
     pending proposal endpoint, and reflection endpoint.
   - Read-only: does not approve/reject proposals and does not trigger training.

Also updated `scripts/qa_day73_live.py`: casual chat QA now expects zero tools,
matching the reflex doctrine.

## Day73 Proposal Queue Security Follow-up

Codex tightened `POST /v1/sandbox/proposals` after the Jurnal & Proposal panel
went live:

- Public unauthenticated proposal creation now returns `401`.
- Brain-created proposals still work through the internal `propose_improvement`
  tool because it attaches `X-Admin-Key` server-side.
- Added `api/tests/test_sandbox_auth.py` to lock this behavior.

Reason: proposal mode should mean "Migan asks Fahmi", not "the internet can
write into Fahmi's review queue".

## Day73 Proposal Lifecycle Visibility

Codex added read-only lifecycle visibility to the proposal queue:

- Every proposal response now includes `lifecycle.required_gates`,
  `passed_gates`, `failed_gates`, `missing_gates`, and `next_action`.
- `backlog.html` shows gate chips directly under each proposal so Fahmi can see
  why a proposal is still waiting.
- No gate is auto-marked as passed. The UI exposes the checklist; actual gates
  still require evidence and explicit recording.

This keeps the education loop honest: Migan can ask, Fahmi can approve, and the
system can see which validation gates remain before promotion.
