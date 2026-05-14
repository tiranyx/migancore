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
commit_sha=f79732b
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
Reflex path target:          sub-second to low single-digit
```

## Current Doctrine

Use a layered nervous system:

```text
reflex -> lightweight cognition -> full cognition + tools -> proposal -> sandbox -> promotion
```

Reflex handles tiny social turns. Lightweight cognition handles simple answers.
Full cognition handles tasks, memory, tools, research, coding, and decisions.
Training only happens after proposal review and clear evidence.

