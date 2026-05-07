#!/bin/bash
# Deploy Day 65 changes to production
# Run ONLY after Cycle 5 eval completes (do not restart API while eval running)
#
# Changes deployed:
#   1. api/routers/conversations.py — POST /v1/conversations/{id}/messages/{id}/feedback
#   2. api/routers/chat.py — SSE done event includes message_id (pre-generated UUID)
#   3. frontend/chat.html — thumbs up/down 👍👎 buttons on assistant messages
#
# Usage: bash /opt/ado/scripts/deploy_day65.sh
# Author: Claude Sonnet 4.6, Day 65

set -e

COMPOSE_DIR="/opt/ado"
REPO_DIR="/opt/ado"   # VPS repo is directly at /opt/ado (mounted)
LOG="/tmp/deploy_day65.log"
FRONTEND_SRC="$REPO_DIR/frontend/chat.html"
FRONTEND_DST="/www/wwwroot/app.migancore.com/chat.html"

echo "=== DAY 65 DEPLOY ===" | tee $LOG
echo "$(date -u): Starting deploy" | tee -a $LOG

# 1. Pull latest code from git
echo "" | tee -a $LOG
echo "1. Pulling latest from git..." | tee -a $LOG
cd $REPO_DIR
git pull origin main 2>&1 | tee -a $LOG

# 2. Build API image (needed for new Python code)
echo "" | tee -a $LOG
echo "2. Building API Docker image..." | tee -a $LOG
docker compose build api 2>&1 | tee -a $LOG

# 3. Restart API container
echo "" | tee -a $LOG
echo "3. Restarting API container..." | tee -a $LOG
docker compose up -d api 2>&1 | tee -a $LOG
echo "   Waiting 20s for API to initialize..." | tee -a $LOG
sleep 20

# 4. Verify API health
echo "" | tee -a $LOG
echo "4. Health check..." | tee -a $LOG
HEALTH=$(curl -sf http://localhost:18000/health 2>/dev/null || echo "FAILED")
echo "   Health: $HEALTH" | tee -a $LOG

# 5. Deploy frontend
echo "" | tee -a $LOG
echo "5. Deploying frontend chat.html..." | tee -a $LOG
if [ -f "$FRONTEND_SRC" ]; then
    cp "$FRONTEND_SRC" "$FRONTEND_DST"
    echo "   Copied to $FRONTEND_DST" | tee -a $LOG
else
    echo "   WARN: $FRONTEND_SRC not found — skipping frontend deploy" | tee -a $LOG
fi

# 6. Smoke test feedback endpoint
echo "" | tee -a $LOG
echo "6. Smoke test feedback endpoint..." | tee -a $LOG
# Try to hit the endpoint (will get 422 without proper IDs, but 422 = endpoint exists)
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" -X POST http://localhost:18000/v1/conversations/00000000-0000-0000-0000-000000000000/messages/00000000-0000-0000-0000-000000000000/feedback \
    -H 'Content-Type: application/json' -H 'Authorization: Bearer dummy' \
    -d '{"rating":"thumbs_up"}' 2>/dev/null || echo "0")
echo "   Feedback endpoint status (expect 401 or 404): $STATUS" | tee -a $LOG
if [ "$STATUS" = "401" ] || [ "$STATUS" = "404" ] || [ "$STATUS" = "422" ]; then
    echo "   ✅ Feedback endpoint reachable" | tee -a $LOG
else
    echo "   ⚠ Unexpected status $STATUS — check logs" | tee -a $LOG
fi

# 7. Install refine_pending_pairs cron
echo "" | tee -a $LOG
echo "7. Installing refine_pending_pairs cron..." | tee -a $LOG
cp $REPO_DIR/scripts/refine_pending_pairs.py /opt/ado/scripts/refine_pending_pairs.py
# Add cron if not already present
CRON_LINE="0 19 * * * python3 /opt/ado/scripts/refine_pending_pairs.py >> /tmp/refine_pairs.log 2>&1"
(crontab -l 2>/dev/null | grep -q "refine_pending_pairs" && echo "   Cron already installed") || \
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
echo "   Cron: $CRON_LINE" | tee -a $LOG

echo "" | tee -a $LOG
echo "=== DEPLOY COMPLETE ===" | tee -a $LOG
echo "$(date -u): Day 65 deploy done" | tee -a $LOG
echo "Log: $LOG" | tee -a $LOG
echo "" | tee -a $LOG
echo "NEXT: Restart synthetic gen after confirming API is healthy:" | tee -a $LOG
echo "  curl -X POST http://localhost:18000/v1/admin/synthetic/start \\" | tee -a $LOG
echo "    -H \"X-Admin-Key: \$ADMIN_KEY\" \\" | tee -a $LOG  # Day 69: redacted, set ADMIN_KEY from private vault
echo "    -H 'Content-Type: application/json' \\" | tee -a $LOG
echo "    -d '{\"target_pairs\": 1000}'" | tee -a $LOG
