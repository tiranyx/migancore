#!/usr/bin/env bash
# Day 73 Codex audit — VPS worktree cleanup helper.
#
# Codex flagged /opt/ado as dirty (modified + untracked). This script snapshots
# state, stashes local files, pulls main, and leaves a deployable tree.
#
# Run on VPS after `git fetch origin`. Idempotent. Read-only on first run.
# Pass `commit` or `--commit` to actually apply.
set -euo pipefail

ROOT="/opt/ado"
MODE="${1:-dry}"   # dry|commit|--commit
if [ "$MODE" = "--commit" ]; then
  MODE="commit"
fi

cd "$ROOT"
echo "== Outer worktree ($ROOT) =="
git status --short | head -50 || true
OUTER_HEAD=$(git rev-parse --short HEAD)
echo "HEAD: $OUTER_HEAD"

if [ "$MODE" != "commit" ]; then
  echo
  echo "(dry run — pass 'commit' to actually clean)"
  exit 0
fi

# --- Actual cleanup ---
SNAP="/opt/ado/.day73_cleanup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SNAP"

cd "$ROOT"
# Save worktree changes (no commit history pollution)
if [ -n "$(git status --porcelain)" ]; then
  echo "Snapshotting changes → $SNAP/worktree.patch"
  git diff > "$SNAP/worktree.patch" || true
  git status --short > "$SNAP/worktree.status" || true
  git stash push -u -m "day73-cleanup-worktree" || true
fi

# Pull latest
cd "$ROOT"
git fetch origin
git pull --ff-only origin main || {
  echo "FF pull failed — manual review needed. Stashes preserved."
  exit 1
}

echo
echo "Clean. Snapshots saved at: $SNAP"
echo "Apply with: docker compose -f $ROOT/docker-compose.yml build api && docker compose -f $ROOT/docker-compose.yml up -d api"
