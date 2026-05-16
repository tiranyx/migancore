#!/bin/bash
# Daily Iteration Script — MiganCore Organic Growth Sprint
# Run automatically every day to: eval → log → notify
# 
# Usage (cron): 0 6 * * * /opt/ado/scripts/daily_iteration.sh >> /opt/ado/logs/organic_sprint/daily_cron.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs/organic_sprint"
DATE=$(date +%Y%m%d)
TIME=$(date +%H:%M:%S)

mkdir -p "$LOG_DIR"

log() {
    echo "[$DATE $TIME] $1" | tee -a "$LOG_DIR/daily_iteration.log"
}

log "=== Daily Iteration Started ==="

# 1. Health check
cd "$PROJECT_DIR"
API_HEALTH=$(curl -sf http://localhost:18000/health || echo "DOWN")
if [ "$API_HEALTH" = "DOWN" ]; then
    log "❌ API is DOWN — aborting iteration"
    exit 1
fi
log "✅ API healthy"

# 2. Ollama health
OLLAMA_HEALTH=$(curl -sf http://localhost:11434/api/tags > /dev/null && echo "UP" || echo "DOWN")
if [ "$OLLAMA_HEALTH" = "DOWN" ]; then
    log "❌ Ollama is DOWN — aborting iteration"
    exit 1
fi
log "✅ Ollama healthy"

# 3. Run identity eval (quick version — 3 prompts)
log "Running quick identity eval..."
python3 "$SCRIPT_DIR/eval_identity_gate_v2.py" --model migancore:0.8 --ollama_url http://localhost:11434 > "$LOG_DIR/eval_${DATE}.log" 2>&1 || true

# Extract score from log
SCORE=$(grep "Score:" "$LOG_DIR/eval_${DATE}.log" | tail -1 | awk '{print $2}' || echo "N/A")
log "  Identity eval score: $SCORE"

# 4. Check feedback stats
log "Checking feedback pipeline..."
FEEDBACK_COUNT=$(docker exec ado-postgres-1 psql -U ado -d ado -t -c "SELECT COUNT(*) FROM interactions_feedback" 2>/dev/null | xargs || echo "0")
PAIRS_COUNT=$(docker exec ado-postgres-1 psql -U ado -d ado -t -c "SELECT COUNT(*) FROM preference_pairs" 2>/dev/null | xargs || echo "0")
KG_ENTITIES=$(docker exec ado-postgres-1 psql -U ado -d ado -t -c "SELECT COUNT(*) FROM chat_entities" 2>/dev/null | xargs || echo "0")
KG_RELATIONS=$(docker exec ado-postgres-1 psql -U ado -d ado -t -c "SELECT COUNT(*) FROM chat_relations" 2>/dev/null | xargs || echo "0")

log "  Feedback events: $FEEDBACK_COUNT"
log "  Preference pairs: $PAIRS_COUNT"
log "  KG entities: $KG_ENTITIES"
log "  KG relations: $KG_RELATIONS"

# 5. Check dataset growth
SFT_PAIRS=$(wc -l < "$PROJECT_DIR/training_data/identity_sft_200_ORGANIC.jsonl" 2>/dev/null | xargs || echo "0")
DPO_PAIRS=$(wc -l < "$PROJECT_DIR/data/training_new/dpo_export.jsonl" 2>/dev/null | xargs || echo "0")
log "  SFT dataset: $SFT_PAIRS pairs"
log "  DPO dataset: $DPO_PAIRS pairs"

# 6. Log metrics to file for trend analysis
METRICS_FILE="$LOG_DIR/metrics_history.csv"
if [ ! -f "$METRICS_FILE" ]; then
    echo "date,identity_score,feedback_count,pairs_count,kg_entities,kg_relations,sft_pairs,dpo_pairs" > "$METRICS_FILE"
fi
echo "$DATE,$SCORE,$FEEDBACK_COUNT,$PAIRS_COUNT,$KG_ENTITIES,$KG_RELATIONS,$SFT_PAIRS,$DPO_PAIRS" >> "$METRICS_FILE"

# 7. Check if training threshold reached
if [ "$PAIRS_COUNT" -ge 1000 ] 2>/dev/null && [ "$SFT_PAIRS" -ge 200 ] 2>/dev/null; then
    log "🚀 TRAINING THRESHOLD REACHED! ($PAIRS_COUNT DPO + $SFT_PAIRS SFT)"
    log "  Ready for CPU LoRA training or cloud GPU training."
else
    log "  Training threshold not yet reached (need 1000 DPO + 200 SFT)"
fi

# 8. Backup daily log
cp "$LOG_DIR/daily_iteration.log" "$LOG_DIR/daily_iteration_${DATE}.log"

log "=== Daily Iteration Complete ==="
