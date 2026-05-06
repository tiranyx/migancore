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

echo "[3/5] Restarting API container..."
ssh $VPS "cd $ADO_PATH && docker compose restart api"

echo "[4/5] Waiting 10s for startup..."
sleep 10

echo "[5/5] Smoke test — license info endpoint..."
curl -s https://api.migancore.com/license/info | python3 -m json.tool

echo ""
echo "=== Deploy v0.5.19 DONE ==="
echo "Expected: {\"mode\": \"DEMO\", \"ado_display_name\": \"Migan\", ...}"
echo ""
echo "NEXT: Add LICENSE_SECRET_KEY to VPS .env:"
echo "  ssh $VPS 'cd $ADO_PATH && grep -q LICENSE_SECRET_KEY .env || echo LICENSE_SECRET_KEY=$(python3 -c \"import secrets; print(secrets.token_hex(32))\") >> .env'"
echo "  Then: docker compose restart api"
