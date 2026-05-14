#!/usr/bin/env bash
# Safe API deploy for MiganCore VPS.
#
# Run on VPS:
#   cd /opt/ado && bash scripts/vps_deploy_api_safe.sh
#
# Why this exists:
# - docker-compose.yml reads BUILD_COMMIT_SHA/BUILD_DAY/BUILD_TIME from the
#   deploy shell environment.
# - Plain `docker compose up -d api` leaves commit_sha="unknown".
# - This script keeps /health and /v1/system/status aligned with the live git
#   checkout every time.
set -euo pipefail

ROOT="${ADO_ROOT:-/opt/ado}"
REMOTE="${GIT_REMOTE:-origin}"
BRANCH="${GIT_BRANCH:-main}"
BUILD_DAY="${BUILD_DAY:-Day73-journal-proposal}"

cd "$ROOT"

echo "== MiganCore safe API deploy =="
echo "root:   $ROOT"
echo "remote: $REMOTE/$BRANCH"

echo
echo "== before =="
git rev-parse --short HEAD
git status --short

echo
echo "== pull =="
git fetch "$REMOTE" "$BRANCH"
git pull --ff-only "$REMOTE" "$BRANCH"

BUILD_COMMIT_SHA="$(git rev-parse --short HEAD)"
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export BUILD_COMMIT_SHA BUILD_TIME BUILD_DAY

echo
echo "== build metadata =="
echo "BUILD_COMMIT_SHA=$BUILD_COMMIT_SHA"
echo "BUILD_DAY=$BUILD_DAY"
echo "BUILD_TIME=$BUILD_TIME"

echo
echo "== build + recreate api =="
docker compose build api
docker compose up -d --no-deps --force-recreate api

echo
echo "== wait health =="
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:18000/health >/tmp/migancore_health.json; then
    cat /tmp/migancore_health.json
    echo
    break
  fi
  sleep 2
done

echo
echo "== status =="
docker compose ps api
docker compose exec -T api sh -lc 'printenv | grep -E "^(AUTO_TRAIN_MODE|DEFAULT_MODEL|OLLAMA_DEFAULT_MODEL|BUILD_COMMIT_SHA|BUILD_DAY|BUILD_TIME)=" | sort'

echo
echo "== done =="
