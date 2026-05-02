#!/bin/bash
# ============================================================
# MIGANCORE — Day 2 Setup Script
# Run on VPS after Day 1 is complete
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
info() { echo -e "${BLUE}[ℹ]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo "=========================================="
echo "  MIGANCORE — Day 2: Ollama + First Token"
echo "=========================================="

# --- Step 1: Navigate to project ---
cd /opt/ado

# --- Step 2: Start Core Infrastructure ---
echo ""
echo "[1/6] Starting PostgreSQL, Qdrant, Redis, Letta..."
docker compose up -d postgres qdrant redis letta
sleep 10

# Check health
for service in postgres qdrant redis; do
    if docker compose ps $service | grep -q "running"; then
        log "$service is running"
    else
        error "$service failed to start"
    fi
done

# --- Step 3: Start Ollama ---
echo ""
echo "[2/6] Starting Ollama..."
docker compose up -d ollama
sleep 5

if docker compose ps ollama | grep -q "running"; then
    log "Ollama is running"
else
    error "Ollama failed to start"
fi

# --- Step 4: Pull Models ---
echo ""
echo "[3/6] Pulling Qwen2.5-7B-Instruct..."
docker compose exec ollama ollama pull qwen2.5:7b-instruct-q4_K_M
log "Qwen2.5-7B pulled"

echo ""
echo "[4/6] Pulling Qwen2.5-0.5B (draft model for speculative decoding)..."
docker compose exec ollama ollama pull qwen2.5:0.5b
log "Qwen2.5-0.5B pulled"

# --- Step 5: Benchmark ---
echo ""
echo "[5/6] Running token benchmark..."
echo "Testing inference speed..."

# Run benchmark via API
START_TIME=$(date +%s%N)
RESPONSE=$(curl -s -X POST http://localhost:11434/api/generate \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen2.5:7b-instruct-q4_K_M","prompt":"Hello, this is a benchmark test.","stream":false,"options":{"num_predict":100}}')
END_TIME=$(date +%s%N)

# Extract metrics
TOKENS=$(echo "$RESPONSE" | grep -o '"eval_count":[0-9]*' | cut -d: -f2 || echo "0")
DURATION_MS=$(( (END_TIME - START_TIME) / 1000000 ))

if [ "$TOKENS" -gt 0 ] && [ "$DURATION_MS" -gt 0 ]; then
    TOKENS_PER_SEC=$(awk "BEGIN {printf \"%.2f\", $TOKENS / ($DURATION_MS / 1000)}")
    log "Benchmark: $TOKENS tokens in ${DURATION_MS}ms = $TOKENS_PER_SEC tok/sec"
    
    # Save benchmark
    echo "{\"date\":\"$(date -Iseconds)\",\"model\":\"qwen2.5:7b-instruct-q4_K_M\",\"tokens\":$TOKENS,\"duration_ms\":$DURATION_MS,\"tokens_per_sec\":$TOKENS_PER_SEC}" > /opt/ado/data/baseline.json
else
    warn "Could not parse benchmark, but model responded"
fi

# --- Step 6: Health Check ---
echo ""
echo "[6/6] Health check..."
HEALTH=$(curl -s http://localhost:11434/api/tags | grep -c "qwen2.5" || echo "0")
if [ "$HEALTH" -ge 1 ]; then
    log "Ollama has models loaded"
else
    warn "Ollama response unclear"
fi

# --- Summary ---
echo ""
echo "=========================================="
echo "           DAY 2 COMPLETE"
echo "=========================================="
echo ""
log "Services running:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""
log "Models available:"
docker compose exec ollama ollama list

echo ""
info "Next steps (Day 3-4):"
echo "  1. Start API service: docker compose up -d api"
echo "  2. Test: curl http://localhost:8000/health"
echo "  3. Run database migrations"
echo "  4. FastAPI hello-world endpoint"
echo ""
log "Day 2 complete!"
