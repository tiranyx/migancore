#!/bin/bash
# Auto Eval Gate Cron Wrapper ??? Day 71e
# Run daily at 04:00 UTC (when distillation is idle)
# Crontab: 0 4 * * * /opt/ado/scripts/run_auto_eval.sh >> /var/log/auto_eval.log 2>&1

set -euo pipefail

cd /opt/ado

# Copy latest script into container /tmp/ (read-only rootfs workaround)
cat /opt/ado/api/scripts/auto_eval_gate.py | docker compose exec -T api tee /tmp/auto_eval_gate.py > /dev/null

# Run evaluation
docker compose exec -e PYTHONPATH=/app api python /tmp/auto_eval_gate.py
