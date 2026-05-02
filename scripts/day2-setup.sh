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

# --- Step 2: Start Core Infrastructure (WITHOUT Letta — needs Ollama first) ---
echo ""
echo "[1/6] Starting PostgreSQL, Qdrant, Redis..."
docker compose up -d postgres qdrant redis
sleep 10

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

# Wait for Ollama to be healthy (max 60s)
for i in {1..12}; do
    if docker compose ps ollama | grep -q "healthy"; then
        log "Ollama is healthy"
        break
    fi
    if [ "$i" -eq 12 ]; then
        error "Ollama did not become healthy within 60s"
    fi
    info "Waiting for Ollama to be healthy... ($i/12)"
    sleep 5
done

# --- Step 3.5: Start Letta (depends on Ollama healthy) ---
echo ""
echo "[2.5/6] Starting Letta (depends on Ollama)..."
docker compose up -d letta
sleep 5

if docker compose ps letta | grep -q "running"; then
    log "Letta is running"
else
    warn "Letta may still be starting — check later with: docker compose ps"
fi

# --- Step 4: Pull Models ---
echo ""
echo "[3/6] Pulling Qwen2.5-7B-Instruct..."
docker compose exec -T ollama ollama pull qwen2.5:7b-instruct-q4_K_M
log "Qwen2.5-7B pulled"

echo ""
echo "[4/6] Pulling Qwen2.5-0.5B (draft model for speculative decoding)..."
docker compose exec -T ollama ollama pull qwen2.5:0.5b
log "Qwen2.5-0.5B pulled"

# --- Step 5: Benchmark ---
echo ""
echo "[5/6] Running token benchmark..."
info "Testing inference speed..."

# Run benchmark via Ollama API inside container
BENCH_RESULT=$(docker compose exec -T ollama ollama run qwen2.5:7b-instruct-q4_K_M --verbose "Hello, this is a benchmark test. Count 1 2 3 4 5." 2>&1 || true)

# Try to extract tokens from verbose output
TOKENS=$(echo "$BENCH_RESULT" | grep -oP 'eval rate:\s*\K[0-9.]+' || echo "")
if [ -n "$TOKENS" ]; then
    log "Benchmark: ~${TOKENS} tok/sec"
    echo "{\"date\":\"$(date -Iseconds)\",\"model\":\"qwen2.5:7b-instruct-q4_K_M\",\"tokens_per_sec\":$TOKENS}" > /opt/ado/data/baseline.json
else
    warn "Could not parse benchmark, but model is available"
fi

# --- Step 6: Health Check ---
echo ""
echo "[6/6] Health check..."
MODEL_COUNT=$(docker compose exec -T ollama ollama list | grep -c "qwen2.5" || echo "0")
if [ "$MODEL_COUNT" -ge 2 ]; then
    log "Ollama has both models loaded"
else
    warn "Expected 2 models, found $MODEL_COUNT"
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
docker compose exec -T ollama ollama list

echo ""
info "Next steps (Day 3-4):"
echo "  1. Start API service: docker compose up -d api"
echo "  2. Test: curl http://localhost:8000/health"
echo "  3. Run database migrations"
echo "  4. FastAPI hello-world endpoint"
echo ""
log "Day 2 complete!"
