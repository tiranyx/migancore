#!/bin/bash
# Daily auto-harvest of live conversation pairs into preference_pairs DB.
# Runs as cron: 0 2 * * * /opt/ado/scripts/daily_harvest.sh
# Logs to: /opt/ado/data/training/auto/harvest_cron.log

set -euo pipefail

ADO_DIR="/opt/ado"
WORKSPACE="/opt/ado/data/workspace"
LOG_DIR="/opt/ado/data/training/auto"
TIMESTAMP=$(date -u +%Y%m%d_%H%M)
JSONL_PATH="$WORKSPACE/live_harvest_${TIMESTAMP}.jsonl"
LOG_FILE="$LOG_DIR/harvest_cron.log"

mkdir -p "$LOG_DIR" "$WORKSPACE"

_log() {
    echo "[$(date -u +%H:%M:%S)] [daily_harvest] $1" | tee -a "$LOG_FILE"
}

_log "=== Daily harvest started ${TIMESTAMP} ==="

# Step 1: Dump conversation pairs via postgres superuser (bypasses RLS)
_log "Dumping conversation pairs from DB..."
docker exec ado-postgres-1 psql -U ado -d ado -t -A -c "
WITH first_msg AS (
  SELECT conversation_id, role AS first_role
  FROM messages
  WHERE created_at = (
    SELECT MIN(created_at) FROM messages m2
    WHERE m2.conversation_id = messages.conversation_id
  )
)
SELECT json_build_object(
  'conv_id', u.conversation_id::text,
  'prompt',  u.content,
  'chosen',  a.content
)
FROM messages u
JOIN LATERAL (
  SELECT content FROM messages a2
  WHERE a2.conversation_id = u.conversation_id
    AND a2.role = 'assistant'
    AND a2.created_at > u.created_at
    AND a2.tool_calls IS NULL
    AND length(a2.content) >= 60
  ORDER BY a2.created_at ASC
  LIMIT 1
) a ON true
JOIN first_msg f ON f.conversation_id = u.conversation_id
                 AND f.first_role = 'user'
WHERE u.role = 'user'
  AND length(u.content) >= 15
  AND u.content NOT LIKE '[KONTEKS%'
ORDER BY u.conversation_id, u.created_at;
" > "$JSONL_PATH" 2>&1

PAIR_COUNT=$(wc -l < "$JSONL_PATH" | tr -d ' ')
_log "Dumped ${PAIR_COUNT} candidate pairs → ${JSONL_PATH}"

if [ "$PAIR_COUNT" -eq 0 ]; then
    _log "No pairs found, exiting."
    exit 0
fi

# Step 2: Import via API container (handles dedup + insert)
_log "Importing into preference_pairs (skipping duplicates)..."
CONTAINER_PATH="/app/workspace/live_harvest_${TIMESTAMP}.jsonl"
cd "$ADO_DIR" && docker compose exec -T api \
    python /app/workspace/import_real_pairs.py --path "$CONTAINER_PATH" \
    2>&1 | tee -a "$LOG_FILE"

# Step 3: Check real_conversation count
_log "Checking real_conversation count..."
REAL_COUNT=$(cd "$ADO_DIR" && docker compose exec -T api python -c "
import asyncio, os, sys
sys.path.insert(0, '/app')
os.chdir('/app')
async def c():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    dsn = os.environ.get('DATABASE_URL','').replace('postgresql://','postgresql+asyncpg://')
    e = create_async_engine(dsn, echo=False)
    S = sessionmaker(e, class_=AsyncSession, expire_on_commit=False)
    async with S() as db:
        r = await db.execute(text(\"SELECT COUNT(*) FROM preference_pairs WHERE source_method='real_conversation' AND used_in_training_run_id IS NULL\"))
        print(r.scalar())
asyncio.run(c())
" 2>/dev/null)

_log "real_conversation unused pairs: ${REAL_COUNT} (threshold=80)"
_log "=== Daily harvest done ==="
