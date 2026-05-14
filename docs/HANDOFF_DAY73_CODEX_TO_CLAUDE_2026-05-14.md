# Handoff Day 73 - Codex to Claude

Date: 2026-05-14
Prepared by: Codex
Audience: Claude Code / next agent
Status: Safe checkpoint for continued work

## Current Production State

Production API is healthy and intentionally locked to the stable brain:

```text
API: https://api.migancore.com
health.status: healthy
version: 0.5.16
model: migancore:0.7c
commit_sha: c309771
build_day: Day73-reflex
```

VPS:

```text
repo: /opt/ado
HEAD: c309771
dirty worktree: none at last Codex check
backup stash: stash@{0}: codex-pre-ca3fcc9-deploy
```

Root platform repo was bumped to:

```text
c71ec56 chore(sync): bump submodule - Day73 reflex optimization
```

## What Changed

### 1. Biomimetic Training Policy

Auto-training is no longer allowed to launch GPU jobs by default.

```text
AUTO_TRAIN_MODE=proposal
```

Thresholds now create a `dev_organ_proposals` row and stop. GPU training is
vitamin, not oxygen. Do not set `AUTO_TRAIN_MODE=auto` unless Fahmi explicitly
approves.

Confirmed behavior:

```text
real_pairs=93 threshold met
PROPOSAL created
pending proposal exists -> skipped
NO Vast.ai trigger
```

### 2. Stable Model Lock

Production defaults are intentionally back on:

```text
DEFAULT_MODEL=migancore:0.7c
OLLAMA_DEFAULT_MODEL=migancore:0.7c
```

Do not re-promote `migancore:0.7e` until evals prove better identity,
latency, and behavior than `0.7c`.

### 3. Reflex Path for Tiny Social Turns

Tiny greetings/thanks/acks now use a reflex path instead of waking the full
7B model.

Examples:

```text
halo       -> Halo. Aku di sini.
makasih ya -> Sama-sama. Aku standby kalau mau lanjut.
apa kabar -> Aku stabil dan siap belajar bareng. Ada yang mau kita bangun hari ini?
```

QA evidence:

```text
sync reflex latency:   0.03s - 0.05s
stream reflex latency: 0.08s
model_used: reflex:migancore
tool_calls_made: 0
```

This creates a layered nervous system:

```text
reflex -> lightweight cognition -> full cognition + tools -> proposal -> sandbox -> promotion
```

## Commits Shipped by Codex

```text
ca3fcc9 fix(day73): harden biomimetic deploy defaults
9190ad4 fix(chat): add lightweight casual fast path
71b8447 fix(auto-train): match proposal table schema
f79732b fix(auto-train): honor proposal constraints
c309771 fix(chat): add reflex path for tiny social turns
```

## QA Commands Already Run

Health:

```bash
curl -s https://api.migancore.com/health
curl -s https://api.migancore.com/v1/system/status
```

Live chat QA:

```text
register -> login -> create agent -> POST /chat "halo"
result: 200, model_used=reflex:migancore, latency ~0.05s
```

Stream QA:

```text
POST /chat/stream "halo"
result: start + chunk + done, latency ~0.08s
```

Watchdog QA:

```text
auto_train mode=proposal
proposal inserted
later checks skip because pending proposal exists
```

## Do Not Do

- Do not launch Vast.ai/GPU training automatically.
- Do not promote `0.7e` back to production without eval evidence and Fahmi approval.
- Do not add more default tools to `core_brain` until latency is measured.
- Do not remove the reflex path unless replacing it with a faster/simpler equivalent.
- Do not pop/drop `stash@{0}` without inspecting it; it is the backup of the dirty VPS worktree before Codex cleanup.

## Recommended Next Work

1. Build a small admin surface for `dev_organ_proposals`.
2. Turn growth journal output into visible daily learning notes for Fahmi.
3. Add evals for reflex/lightweight/full cognition routing.
4. Improve `/v1/system/status` so it reports the same build day/commit as `/health`.
5. Continue Code Lab as practice arena, but keep it adaptive, not always-on.

The next sprint should strengthen the organism's learning environment, not push
another model by force.

