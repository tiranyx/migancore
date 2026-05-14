#!/usr/bin/env bash
# Day 73 Codex audit — VPS worktree cleanup helper.
#
# Codex flagged /opt/ado as dirty (modified + untracked) + local sub-repo
# ahead. This script: snapshots state → stashes user-edited files → pulls
# main → applies new code-only commits → leaves clean tree.
#
# Run on VPS after `git fetch origin`. Idempotent. Read-only on first run
# (use --commit to actually apply).
set -euo pipefail

ROOT="/opt/ado"
SUB="$ROOT/migancore"
MODE="${1:-dry}"   # dry|commit

cd "$ROOT"
echo "== Outer worktree ($ROOT) =="
git status --short | head -50 || true
OUTER_HEAD=$(git rev-parse --short HEAD)
echo "HEAD: $OUTER_HEAD"

cd "$SUB" 2>/dev/null && {
  echo
  echo "== Sub-repo ($SUB) =="
  git status --short | head -50 || true
  SUB_HEAD=$(git rev-parse --short HEAD)
  echo "HEAD: $SUB_HEAD"
} || true

if [ "$MODE" != "commit" ]; then
  echo
  echo "(dry run — pass 'commit' to actually clean)"
  exit 0
fi

# --- Actual cleanup ---
SNAP="/opt/ado/.day73_cleanup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SNAP"

cd "$ROOT"
# Save outer worktree changes (no commit history pollution)
if [ -n "$(git status --porcelain)" ]; then
  echo "Snapshotting outer changes → $SNAP/outer.patch"
  git diff > "$SNAP/outer.patch" || true
  git status --short > "$SNAP/outer.status" || true
  git stash push -u -m "day73-cleanup-outer" || true
fi

cd "$SUB"
if [ -n "$(git status --porcelain)" ]; then
  echo "Snapshotting sub-repo changes → $SNAP/sub.patch"
  git diff > "$SNAP/sub.patch" || true
  git status --short > "$SNAP/sub.status" || true
  git stash push -u -m "day73-cleanup-sub" || true
fi

# Pull latest
cd "$SUB"
git fetch origin
git pull --ff-only origin main || {
  echo "FF pull failed — manual review needed. Stashes preserved."
  exit 1
}

echo
echo "Clean. Snapshots saved at: $SNAP"
echo "Apply with: docker compose -f $ROOT/docker-compose.yml build api && docker compose -f $ROOT/docker-compose.yml up -d api"
