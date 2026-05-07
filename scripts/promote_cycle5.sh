#!/bin/bash
# promote_cycle5.sh — Hot-swap migancore:0.5 as production brain
# Run ONLY after eval passes all gates (weighted_avg >= 0.92, all cats pass)
# Usage: bash /opt/ado/scripts/promote_cycle5.sh
# Author: Claude Sonnet 4.6, Day 65

set -e

COMPOSE_DIR="/opt/ado"
NEW_MODEL="migancore:0.5"
OLD_MODEL="migancore:0.3"
EVAL_RESULT="/opt/ado/data/workspace/eval_result_migancore-7b-soul-cycle5.json"
LOG="/tmp/promote_cycle5.log"

echo "=== CYCLE 5 PROMOTE SCRIPT ===" | tee $LOG
echo "$(date): Starting promote from $OLD_MODEL -> $NEW_MODEL" | tee -a $LOG

# 1. Verify eval result exists and passed
echo "" | tee -a $LOG
echo "1. Verifying eval gates..." | tee -a $LOG
if [ ! -f "$EVAL_RESULT" ]; then
    echo "ERROR: eval result not found at $EVAL_RESULT" | tee -a $LOG
    echo "Run eval first, then promote." | tee -a $LOG
    exit 1
fi

python3 -c "
import json, sys
with open('$EVAL_RESULT') as f:
    d = json.load(f)

# Support both old format (eval_summary nested) and new flat format
if 'eval_summary' in d:
    wavg = d['eval_summary'].get('weighted_avg', 0)
    cats = d['eval_summary'].get('category_means', {})
else:
    wavg = d.get('weighted_avg_cosine_sim', 0)
    cats = d.get('category_means', {})

gates = {
    'weighted_avg': (wavg, 0.92),
    'identity': (cats.get('identity', 0), 0.90),
    'voice': (cats.get('voice', 0), 0.85),
    'evolution-aware': (cats.get('evolution-aware', 0), 0.80),
    'tool-use': (cats.get('tool-use', 0), 0.85),
    'creative': (cats.get('creative', 0), 0.80),
}

all_pass = True
print('Gate results:')
for cat, (val, gate) in gates.items():
    status = 'PASS' if val >= gate else 'FAIL'
    if val < gate:
        all_pass = False
    print(f'  {status} {cat}: {val:.3f} (gate {gate})')

if not all_pass:
    print('VERDICT: ROLLBACK — gates not met. Do not promote.')
    sys.exit(2)
else:
    print('VERDICT: PROMOTE — all gates passed!')
    sys.exit(0)
" 2>&1 | tee -a $LOG

VERDICT=$?
if [ $VERDICT -ne 0 ]; then
    echo "Promote ABORTED — eval gates not met." | tee -a $LOG
    exit 1
fi

# 2. Add DEFAULT_MODEL to docker-compose.yml
echo "" | tee -a $LOG
echo "2. Updating docker-compose.yml DEFAULT_MODEL..." | tee -a $LOG

# Check if DEFAULT_MODEL already exists in compose file
if grep -q "DEFAULT_MODEL" $COMPOSE_DIR/docker-compose.yml; then
    # Update existing entry
    sed -i "s/DEFAULT_MODEL:.*/DEFAULT_MODEL: $NEW_MODEL/" $COMPOSE_DIR/docker-compose.yml
    echo "   Updated existing DEFAULT_MODEL to $NEW_MODEL" | tee -a $LOG
else
    # Add after OLLAMA_URL line
    sed -i "/OLLAMA_URL: http:\/\/ollama:11434/a\\      DEFAULT_MODEL: $NEW_MODEL" $COMPOSE_DIR/docker-compose.yml
    echo "   Added DEFAULT_MODEL: $NEW_MODEL after OLLAMA_URL" | tee -a $LOG
fi

# Verify
grep "DEFAULT_MODEL" $COMPOSE_DIR/docker-compose.yml | tee -a $LOG

# 3. Restart API container
echo "" | tee -a $LOG
echo "3. Restarting API container..." | tee -a $LOG
cd $COMPOSE_DIR
docker compose restart api 2>&1 | tee -a $LOG
echo "   Waiting 15s for API to start..." | tee -a $LOG
sleep 15

# 4. Verify API is healthy
echo "" | tee -a $LOG
echo "4. Verifying API health..." | tee -a $LOG
HEALTH=$(curl -sf http://localhost:18000/health 2>/dev/null || echo "FAILED")
echo "   Health: $HEALTH" | tee -a $LOG

# 5. Quick smoke test — ask identity question
echo "" | tee -a $LOG
echo "5. Identity smoke test..." | tee -a $LOG
# Get a test token first
TOKEN=$(curl -sf -X POST http://localhost:18000/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"test@example.com","password":"test"}' 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || echo "")

if [ -n "$TOKEN" ]; then
    RESP=$(curl -sf -X POST http://localhost:18000/v1/chat/completions \
        -H "Authorization: Bearer $TOKEN" \
        -H 'Content-Type: application/json' \
        -d '{"messages":[{"role":"user","content":"Siapa kamu?"}],"stream":false}' \
        --max-time 120 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
content = d.get('choices',[{}])[0].get('message',{}).get('content','')
print(content[:200])
" 2>/dev/null || echo "smoke test failed")
    echo "   Response: $RESP" | tee -a $LOG
else
    echo "   No test token — skipping smoke test" | tee -a $LOG
fi

echo "" | tee -a $LOG
echo "=== PROMOTE COMPLETE ===" | tee -a $LOG
echo "$(date): migancore:0.5 is now production brain" | tee -a $LOG
echo "Log: $LOG" | tee -a $LOG
echo "" | tee -a $LOG
echo "NEXT STEPS:" | tee -a $LOG
echo "1. Update MEMORY.md: Production Brain = migancore:0.5" | tee -a $LOG
echo "2. Update docs/DAY65_PROGRESS.md: eval result + promote timestamp" | tee -a $LOG
echo "3. Restart synthetic gen: curl -X POST http://localhost:18000/v1/admin/synthetic/start ..." | tee -a $LOG
echo "4. Commit changes to git" | tee -a $LOG
