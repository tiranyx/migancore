#!/bin/bash
# Deploy v0.5.19 — ADO License System (Day 61)
# Run from LOCAL machine: bash scripts/deploy_v0519.sh
# Prerequisites: VPS SSH access, git pull already done on VPS OR deploy via SCP

set -euo pipefail
VPS="root@72.62.125.6"
ADO_PATH="/opt/ado"
CONTAINER="ado-api-1"

echo "=== Deploy v0.5.19 (ADO License System) ==="

# Step 1: Copy new/modified files to VPS
echo "[1/5] Copying files to VPS..."
scp api/services/license.py   $VPS:$ADO_PATH/api/services/license.py
scp api/routers/license.py    $VPS:$ADO_PATH/api/routers/license.py
scp api/config.py              $VPS:$ADO_PATH/api/config.py
scp api/main.py                $VPS:$ADO_PATH/api/main.py

echo "[2/5] Files copied. Checking VPS git status..."
ssh $VPS "cd $ADO_PATH && git add api/services/license.py api/routers/license.py api/config.py api/main.py && git status --short"

# NOTE (Day 62, Lesson #124): 'restart' is NOT enough — code is baked into image.
# Always: build api → up -d api (so new code is actually applied)
echo "[3/5] Building + recreating API container with new code..."
ssh $VPS "cd $ADO_PATH && docker compose build api && docker compose up -d api"

echo "[4/5] Waiting 15s for startup (embedding models load)..."
sleep 15

echo "[5/5] Smoke test — license info endpoint (Codex fix: was /license/info)..."
curl -s https://api.migancore.com/v1/license/info | python3 -m json.tool

echo ""
echo "=== Deploy v0.5.19 DONE ==="
echo "Expected: {\"mode\": \"DEMO\", \"ado_display_name\": \"Migan\", \"is_operational\": true}"
echo ""
echo "NEXT: Ensure .env has required license vars (already done if Day 62 deploy ran):"
echo "  LICENSE_SECRET_KEY   — 64-char hex"
echo "  LICENSE_DEMO_MODE    — True (for beta app.migancore.com)"
echo "  ADO_DISPLAY_NAME     — Migan"
echo "  LICENSE_INTERNAL_KEY — 48-char hex (for /v1/license/mint protection)"
echo "  All must be in docker-compose.yml environment: block (Lesson #125)"
