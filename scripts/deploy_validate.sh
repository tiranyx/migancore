#!/bin/bash
# Deploy Validation Script — MiganCore VPS
# Usage: ssh root@72.62.125.6 'bash -s' < deploy_validate.sh

set -euo pipefail

echo "=== MIGANCORE DEPLOY VALIDATION ==="
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# 1. Git state
cd /opt/ado
echo "[1/7] Git state"
echo "  HEAD: $(git rev-parse --short HEAD)"
echo "  Branch: $(git branch --show-current)"
echo "  Dirty: $(git status --short | wc -l) files"
echo ""

# 2. Container health
echo "[2/7] Docker containers"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}" 2>/dev/null || docker compose ps
echo ""

# 3. API health
echo "[3/7] API health"
HEALTH=$(curl -sS http://127.0.0.1:18000/health 2>/dev/null || echo '{"status":"DOWN"}')
echo "  $HEALTH"
echo ""

# 4. Ollama models
echo "[4/7] Ollama models"
docker compose exec -T ollama ollama list 2>/dev/null || echo "  (cannot exec into ollama container)"
echo ""

# 5. Resource usage
echo "[5/7] Resource usage"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "  (docker stats unavailable)"
echo ""

# 6. Recent errors
echo "[6/7] Recent errors (last 10 min)"
docker compose logs --since 10m api 2>&1 | grep -iE "error|exception|timeout|fail" | tail -5 || echo "  No errors found"
echo ""

# 7. Disk usage
echo "[7/7] Disk usage"
df -h /opt/ado | tail -1
echo ""

echo "=== VALIDATION COMPLETE ==="
