#!/bin/bash
# ============================================================
# Post-Cycle 6 Pipeline — GGUF Convert → Ollama → Eval → PROMOTE/ROLLBACK
# Day 67 | Run AFTER cycle6_orpo_vast.py completes
# ============================================================
# Usage: bash post_cycle6.sh
# Requires: cycle6_output/cycle6_adapter/ exists on VPS
# ============================================================

set -euo pipefail

ADAPTER_DIR="/opt/ado/cycle6_output/cycle6_adapter"
GGUF_F16="/opt/ado/cycle6_output/cycle6_lora_f16.gguf"
GGUF_Q4="/opt/ado/cycle6_output/cycle6_lora_q4.gguf"
MODELFILE="/opt/ado/cycle6_output/Modelfile_cycle6"
MODEL_TAG="migancore:0.6"
BASE_MODEL="qwen2.5:7b-instruct-q4_K_M"
LLAMA_CPP="/opt/llama.cpp"
LOG="/tmp/post_cycle6.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC} $(date +%H:%M:%S) $*" | tee -a "$LOG"; }
err()  { echo -e "${RED}[ERROR]${NC} $(date +%H:%M:%S) $*" | tee -a "$LOG"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $(date +%H:%M:%S) $*" | tee -a "$LOG"; }

info "=== POST CYCLE 6 PIPELINE ==="
info "Log: $LOG"

# ─── Step 1: Verify adapter exists ────────────────────────────────────────────
info "[1/5] Verifying Cycle 6 adapter..."
if [[ ! -d "$ADAPTER_DIR" ]]; then
    err "Adapter not found: $ADAPTER_DIR"
    err "Training may not be complete yet. Run cycle6_orpo_vast.py first."
    exit 1
fi

ADAPTER_FILES=$(ls "$ADAPTER_DIR"/*.bin 2>/dev/null | wc -l || echo 0)
info "  Adapter dir: $ADAPTER_DIR"
info "  Files: $(ls "$ADAPTER_DIR" | tr '\n' ' ')"
info "  .bin count: $ADAPTER_FILES"

# ─── Step 2: GGUF Conversion (LoRA merge → f16 → Q4_K_M) ────────────────────
info "[2/5] Converting LoRA adapter to GGUF..."

# Use llama.cpp convert_lora_to_gguf (Day 59 proven method)
if [[ ! -f "$LLAMA_CPP/convert_lora_to_gguf.py" ]]; then
    err "llama.cpp not found at $LLAMA_CPP"
    err "Run: cd /opt && git clone https://github.com/ggerganov/llama.cpp"
    exit 1
fi

info "  Converting to f16 GGUF (no base model download needed)..."
python3 "$LLAMA_CPP/convert_lora_to_gguf.py" \
    "$ADAPTER_DIR" \
    --outfile "$GGUF_F16" \
    --outtype f16 \
    2>&1 | tee -a "$LOG"

if [[ ! -f "$GGUF_F16" ]]; then
    err "f16 GGUF conversion failed"
    exit 1
fi
F16_SIZE=$(du -sh "$GGUF_F16" | cut -f1)
info "  f16 GGUF: $GGUF_F16 ($F16_SIZE)"

# Quantize to Q4_K_M (smaller, faster for inference)
info "  Quantizing to Q4_K_M..."
"$LLAMA_CPP/llama-quantize" "$GGUF_F16" "$GGUF_Q4" Q4_K_M 2>&1 | tee -a "$LOG"

if [[ -f "$GGUF_Q4" ]]; then
    Q4_SIZE=$(du -sh "$GGUF_Q4" | cut -f1)
    info "  Q4_K_M GGUF: $GGUF_Q4 ($Q4_SIZE)"
    FINAL_GGUF="$GGUF_Q4"
else
    warn "  Q4_K_M quantization failed — falling back to f16"
    FINAL_GGUF="$GGUF_F16"
fi

# ─── Step 3: Register in Ollama ───────────────────────────────────────────────
info "[3/5] Registering migancore:0.6 in Ollama..."

cat > "$MODELFILE" << EOF
FROM $BASE_MODEL
ADAPTER $FINAL_GGUF

# MiganCore Cycle 6 — ORPO apo_zero, 954 pairs
# Target: tool-use>=0.85, creative>=0.80, evo-aware>=0.80
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
EOF

info "  Modelfile:"
cat "$MODELFILE" | tee -a "$LOG"

docker compose -f /opt/ado/docker-compose.yml exec -T ollama \
    ollama create "$MODEL_TAG" -f "$MODELFILE" 2>&1 | tee -a "$LOG"

# Verify model is registered
docker compose -f /opt/ado/docker-compose.yml exec -T ollama \
    ollama list 2>&1 | grep -E "migancore|NAME" | tee -a "$LOG"
info "  $MODEL_TAG registered ✓"

# ─── Step 4: Run Eval with Retry (Lesson #137) ────────────────────────────────
info "[4/5] Running identity eval with retry=3..."
warn "  CPU steal check: $(vmstat 1 3 | tail -1 | awk '{print \"steal=\"$17\"%\"}')"

# Check CPU steal — if >30%, eval results will be unreliable
STEAL=$(vmstat 1 3 | tail -1 | awk '{print $17}')
if [[ $STEAL -gt 30 ]]; then
    warn "  HIGH CPU steal: ${STEAL}% — eval may be unreliable (Lesson #137)"
    warn "  Consider waiting for migration cleanup before running eval"
fi

docker compose -f /opt/ado/docker-compose.yml exec -T api \
    python /app/workspace/run_identity_eval.py \
    --model "$MODEL_TAG" \
    --reference /app/eval/baseline_day58.json \
    --retry 3 \
    2>&1 | tee -a "$LOG"

# ─── Step 5: PROMOTE or ROLLBACK ──────────────────────────────────────────────
info "[5/5] Checking eval result..."

EVAL_JSON="/opt/ado/data/workspace/eval_result_migancore-7b-soul-cycle6.json"
if [[ ! -f "$EVAL_JSON" ]]; then
    # Try alternative path
    EVAL_JSON=$(ls /opt/ado/data/workspace/eval_result_*cycle6*.json 2>/dev/null | tail -1 || echo "")
fi

if [[ -z "$EVAL_JSON" || ! -f "$EVAL_JSON" ]]; then
    err "Eval result not found. Check eval output above."
    exit 1
fi

# Parse result
WEIGHTED=$(python3 -c "import json; d=json.load(open('$EVAL_JSON')); print(d.get('weighted_avg', d.get('overall_score', 0)))" 2>/dev/null || echo "0")
DECISION=$(python3 -c "import json; d=json.load(open('$EVAL_JSON')); print(d.get('decision','ROLLBACK'))" 2>/dev/null || echo "ROLLBACK")

info "  Eval result:"
info "    weighted_avg: $WEIGHTED"
info "    decision: $DECISION"

# Gate thresholds (Lesson #140: single source of truth)
GATE_WEIGHTED=0.92
GATE_IDENTITY=0.90
GATE_VOICE=0.85
GATE_TOOL_USE=0.85
GATE_CREATIVE=0.80
GATE_EVO_AWARE=0.80

# Check all category gates
IDENTITY=$(python3 -c "import json; d=json.load(open('$EVAL_JSON')); cats=d.get('category_means',{}); print(cats.get('identity',cats.get('identity_score',0)))" 2>/dev/null || echo "0")
VOICE=$(python3 -c "import json; d=json.load(open('$EVAL_JSON')); cats=d.get('category_means',{}); print(cats.get('voice',cats.get('voice_score',0)))" 2>/dev/null || echo "0")

info "  Gates:"
info "    weighted_avg >= $GATE_WEIGHTED: $WEIGHTED"
info "    identity     >= $GATE_IDENTITY: $IDENTITY"
info "    voice        >= $GATE_VOICE: $VOICE"

# Decision based on gates
PROMOTE=true
python3 << PYEOF
import json
d = json.load(open("$EVAL_JSON"))
weighted = float(d.get("weighted_avg", d.get("overall_score", 0)))
cats = d.get("category_means", {})

gates = {
    "weighted_avg": ($GATE_WEIGHTED, weighted),
    "identity":     ($GATE_IDENTITY, cats.get("identity", cats.get("identity_score", 0))),
    "voice":        ($GATE_VOICE,    cats.get("voice", cats.get("voice_score", 0))),
    "tool_use":     ($GATE_TOOL_USE, cats.get("tool-use", cats.get("tool_use", 0))),
    "creative":     ($GATE_CREATIVE, cats.get("creative", 0)),
    "evo_aware":    ($GATE_EVO_AWARE, cats.get("evolution-aware", cats.get("evo_aware", 0))),
}

print("\n  Category gates:")
all_pass = True
for name, (threshold, score) in gates.items():
    status = "✅" if float(score) >= threshold else "❌"
    print(f"    {status} {name:15s}: {score:.4f} (gate >= {threshold})")
    if float(score) < threshold:
        all_pass = False

print(f"\n  OVERALL: {'PROMOTE ✅' if all_pass else 'ROLLBACK ❌'}")
PYEOF

if python3 -c "
import json, sys
d = json.load(open('$EVAL_JSON'))
weighted = float(d.get('weighted_avg', d.get('overall_score', 0)))
cats = d.get('category_means', {})
gates_pass = all([
    weighted >= $GATE_WEIGHTED,
    float(cats.get('identity', cats.get('identity_score', 0))) >= $GATE_IDENTITY,
    float(cats.get('voice', cats.get('voice_score', 0))) >= $GATE_VOICE,
    float(cats.get('tool-use', cats.get('tool_use', 0))) >= $GATE_TOOL_USE,
    float(cats.get('creative', 0)) >= $GATE_CREATIVE,
    float(cats.get('evolution-aware', cats.get('evo_aware', 0))) >= $GATE_EVO_AWARE,
])
sys.exit(0 if gates_pass else 1)
"; then
    info "=== PROMOTE === migancore:0.6 meets all gates"
    info "Updating DEFAULT_MODEL → migancore:0.6"
    sed -i 's/DEFAULT_MODEL: str = "migancore:[^"]*"/DEFAULT_MODEL: str = "migancore:0.6"/' /opt/ado/api/config.py
    info "Rebuilding + restarting API..."
    cd /opt/ado && docker compose build api && docker compose up -d api
    info "✅ PROMOTED: migancore:0.6 is now production brain"
    cd /opt/ado && git add api/config.py && git commit -m "feat(cycle6): PROMOTE migancore:0.6 — all gates PASS

weighted_avg: $WEIGHTED >= $GATE_WEIGHTED ✅
All category gates: identity/voice/tool-use/creative/evo-aware PASS

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
    git push origin main
else
    warn "=== ROLLBACK === migancore:0.6 did not meet all gates"
    warn "Production brain remains: migancore:0.3"
    warn "Analyze failed categories above and plan Cycle 7 supplement."
    warn "Consider GRPO for reasoning (score 0.500) + targeted voice/tool-use pairs."
fi

info "=== POST CYCLE 6 COMPLETE ==="
info "Log: $LOG"
