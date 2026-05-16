#!/bin/bash
# Distillation Worker Cron — runs every 6 hours
# Install: crontab -e
#   0 */6 * * * /opt/ado/api/services/distill_cron.sh >> /opt/ado/logs/distill_cron.log 2>&1

set -euo pipefail

LOG_DIR="/opt/ado/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_FILE="$LOG_DIR/distill_${TIMESTAMP}.json"

echo "[${TIMESTAMP}] Starting distillation cycle..."

cd /opt/ado || exit 1

# Run worker inside API container (ensures same Python env)
docker compose exec -T api python -m services.distillation_worker \
  --run-once \
  --hours 6 \
  --limit 20 \
  > "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[${TIMESTAMP}] Distillation OK. Output: $LOG_FILE"
    # Training readiness is handled by auto_train_watchdog in proposal mode.
    # The old services.training_trigger module was removed in Day 76.
    echo "[${TIMESTAMP}] Training proposal check handled by auto_train_watchdog." >> "$LOG_FILE"
else
    echo "[${TIMESTAMP}] Distillation FAILED (exit $EXIT_CODE). Log: $LOG_FILE"
fi

# Cleanup old logs (>30 days)
find "$LOG_DIR" -name "distill_*.json" -mtime +30 -delete 2>/dev/null || true

exit $EXIT_CODE
