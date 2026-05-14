#!/bin/bash
# Auto eval + hot-swap after watchdog training completes.
# Cron: 0 4 * * * /opt/ado/scripts/run_auto_eval.sh >> /var/log/auto_eval.log 2>&1
#
# Flow:
#   1. Check last_success.json (written by auto_train_watchdog after training)
#   2. If training completed in last 18 hours + not yet eval'd:
#      a. Download adapter from HuggingFace
#      b. Merge + convert to GGUF Q4_K_M using llama.cpp on VPS host
#      c. Create Ollama candidate model
#      d. Run eval gate (run_identity_eval.py --model migancore:candidate)
#      e. PROMOTE (weighted_avg >= 0.80) or ROLLBACK

set -euo pipefail

ADO_DIR="/opt/ado"
LAST_SUCCESS_JSON="$ADO_DIR/data/training/auto/last_success.json"
LOG_DIR="$ADO_DIR/data/training/auto"
WORKSPACE="$ADO_DIR/data/workspace"
LOG_FILE="/var/log/auto_eval.log"
LLAMA_CPP="/opt/llama.cpp"
HF_TOKEN=$(cat /opt/secrets/migancore/hf_token 2>/dev/null || echo "")
EVAL_REFERENCE="$WORKSPACE/eval/baseline_day55.json"

_log() {
    echo "[$(date -u +%Y-%m-%d %H:%M:%S)] [auto_eval] $1" | tee -a "$LOG_FILE"
}

_log "=== Auto eval check started ==="

# 1. Check last_success.json
if [ ! -f "$LAST_SUCCESS_JSON" ]; then
    _log "No last_success.json — nothing to eval. Exiting."
    exit 0
fi

CYCLE_ID=$(python3 -c "import json; d=json.load(open('$LAST_SUCCESS_JSON')); print(d.get('cycle_id',''))" 2>/dev/null)
HF_REPO=$(python3 -c "import json; d=json.load(open('$LAST_SUCCESS_JSON')); print(d.get('hf_repo',''))" 2>/dev/null)
COMPLETED_AT=$(python3 -c "import json; d=json.load(open('$LAST_SUCCESS_JSON')); print(d.get('completed_at',''))" 2>/dev/null)
EVAL_DONE=$(python3 -c "import json; d=json.load(open('$LAST_SUCCESS_JSON')); print(d.get('eval_done', False))" 2>/dev/null)

if [ -z "$CYCLE_ID" ] || [ -z "$HF_REPO" ]; then
    _log "last_success.json missing cycle_id or hf_repo. Exiting."
    exit 0
fi

if [ "$EVAL_DONE" = "True" ]; then
    _log "Cycle $CYCLE_ID already eval'd. Exiting."
    exit 0
fi

# Check if completed within last 18 hours
AGE_HOURS=$(python3 -c "
from datetime import datetime, timezone
completed = datetime.fromisoformat('$COMPLETED_AT'.replace('Z', '+00:00'))
if completed.tzinfo is None:
    completed = completed.replace(tzinfo=timezone.utc)
now = datetime.now(timezone.utc)
delta = (now - completed).total_seconds() / 3600
print(f'{delta:.1f}')
" 2>/dev/null || echo "999")

if (( $(echo "$AGE_HOURS > 18" | bc -l) )); then
    _log "Cycle $CYCLE_ID completed ${AGE_HOURS}h ago — too old (>18h). Skipping."
    exit 0
fi

_log "Evaluating cycle: $CYCLE_ID  adapter: $HF_REPO  (${AGE_HOURS}h ago)"

WORK_DIR="$LOG_DIR/eval_${CYCLE_ID}"
ADAPTER_DIR="$WORK_DIR/adapter"
MERGED_DIR="$WORK_DIR/merged"
F16_GGUF="$WORK_DIR/${CYCLE_ID}_f16.gguf"
Q4_GGUF="$WORK_DIR/${CYCLE_ID}_q4km.gguf"
MODELFILE="$WORK_DIR/Modelfile"
CANDIDATE_MODEL="migancore:candidate"

mkdir -p "$ADAPTER_DIR" "$MERGED_DIR"

# 2a. Download adapter from HuggingFace
_log "Downloading adapter $HF_REPO..."
HF_TOKEN_VAL=$(cat /opt/secrets/migancore/hf_token)
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('$HF_REPO', local_dir='$ADAPTER_DIR', token='$HF_TOKEN_VAL')
print('DOWNLOAD_OK')
" 2>&1 | tee -a "$LOG_FILE"

if ! grep -q "DOWNLOAD_OK" "$LOG_FILE" 2>/dev/null; then
    _log "WARNING: download may have failed, checking dir..."
    ls "$ADAPTER_DIR" 2>/dev/null | head -5 || true
fi

# 2b. Merge LoRA adapter into base model
_log "Merging LoRA adapter with Qwen2.5-7B base (CPU, ~600s)..."
python3 - <<PYEOF 2>&1 | tee -a "$LOG_FILE"
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import sys

BASE = "Qwen/Qwen2.5-7B-Instruct"
ADAPTER = "$ADAPTER_DIR"
OUTPUT = "$MERGED_DIR"

print(f"Loading base model from cache: {BASE}")
tokenizer = AutoTokenizer.from_pretrained(BASE, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    BASE, torch_dtype=torch.bfloat16, device_map="cpu", trust_remote_code=True
)
print("Loading adapter...")
model = PeftModel.from_pretrained(model, ADAPTER)
print("Merging...")
model = model.merge_and_unload()
print(f"Saving merged model to {OUTPUT}...")
model.save_pretrained(OUTPUT, safe_serialization=True)
tokenizer.save_pretrained(OUTPUT)
print("MERGE_COMPLETE")
PYEOF

if ! grep -q "MERGE_COMPLETE" "$LOG_FILE" 2>/dev/null; then
    _log "ERROR: Merge failed. Aborting eval."
    exit 1
fi

# 2c. Convert to GGUF f16
_log "Converting to GGUF f16..."
python3 "$LLAMA_CPP/convert_hf_to_gguf.py" \
    "$MERGED_DIR" --outtype f16 --outfile "$F16_GGUF" \
    2>&1 | tail -5 | tee -a "$LOG_FILE"

# 2d. Quantize to Q4_K_M
_log "Quantizing Q4_K_M..."
"$LLAMA_CPP/llama-quantize" "$F16_GGUF" "$Q4_GGUF" Q4_K_M \
    2>&1 | tail -3 | tee -a "$LOG_FILE"

# Remove f16 to save disk
rm -f "$F16_GGUF"
_log "GGUF ready: $(du -sh $Q4_GGUF | cut -f1)"

# 2e. Create candidate Ollama model
cat > "$MODELFILE" <<MODELEOF
FROM $Q4_GGUF
PARAMETER num_ctx 4096
PARAMETER temperature 0.7
PARAMETER stop "<|im_end|>"
MODELEOF

_log "Creating Ollama candidate: $CANDIDATE_MODEL"
ollama create "$CANDIDATE_MODEL" -f "$MODELFILE" 2>&1 | tee -a "$LOG_FILE"

# 3. Run eval gate
_log "Running identity eval against $CANDIDATE_MODEL..."
EVAL_OUTPUT="$WORK_DIR/eval_result.json"
cd "$ADO_DIR" && docker compose exec -T api python /app/workspace/run_identity_eval.py \
    --mode eval \
    --model "$CANDIDATE_MODEL" \
    --model-tag "$CYCLE_ID" \
    --reference "/app/workspace/eval/baseline_day55.json" \
    2>&1 | tee -a "$LOG_FILE"

# Copy eval output out of container
docker compose exec -T api cat "/app/workspace/eval_result_${CYCLE_ID}.json" > "$EVAL_OUTPUT" 2>/dev/null || true

# 4. Parse decision
DECISION=$(python3 -c "
import json, sys
try:
    d = json.load(open('$EVAL_OUTPUT'))
    print(d.get('decision', 'ROLLBACK'))
except:
    print('ROLLBACK')
" 2>/dev/null || echo "ROLLBACK")

WEIGHTED_AVG=$(python3 -c "
import json
try:
    d = json.load(open('$EVAL_OUTPUT'))
    print(d.get('weighted_avg', 0))
except:
    print(0)
" 2>/dev/null || echo "0")

_log "Eval result: decision=$DECISION  weighted_avg=$WEIGHTED_AVG"

# 5. Promote or rollback
if [ "$DECISION" = "PROMOTE" ]; then
    # Determine next version number
    CURRENT_VER=$(ollama list 2>/dev/null | grep 'migancore:' | grep -v candidate | grep -oP '(?<=migancore:)\S+' | sort -V | tail -1)
    _log "Promoting! Current production: migancore:${CURRENT_VER}"

    # New version: increment patch (0.7c → 0.8, auto_20260514 → 0.8)
    NEXT_VER="auto_${CYCLE_ID}"
    _log "Creating migancore:$NEXT_VER as new production..."

    # Copy candidate to new named version
    # Ollama doesn't support 'cp' so we recreate from same GGUF
    cat > "/tmp/Modelfile_promote" <<MODELEOF2
FROM $Q4_GGUF
PARAMETER num_ctx 4096
PARAMETER temperature 0.7
PARAMETER stop "<|im_end|>"
MODELEOF2
    ollama create "migancore:$NEXT_VER" -f "/tmp/Modelfile_promote" 2>&1 | tee -a "$LOG_FILE"

    # Update API to use new model
    _log "Updating DEFAULT_MODEL in .env..."
    if grep -q "DEFAULT_MODEL=" "$ADO_DIR/.env"; then
        OLD_MODEL=$(grep "DEFAULT_MODEL=" "$ADO_DIR/.env" | cut -d= -f2)
        sed -i "s/DEFAULT_MODEL=.*/DEFAULT_MODEL=migancore:$NEXT_VER/" "$ADO_DIR/.env"
        _log "Changed DEFAULT_MODEL: $OLD_MODEL → migancore:$NEXT_VER"
    fi

    # Restart API container
    _log "Restarting API container..."
    cd "$ADO_DIR" && docker compose up -d api 2>&1 | tee -a "$LOG_FILE"
    sleep 10

    # Verify health
    if curl -sf "http://localhost:18000/health" > /dev/null 2>&1; then
        _log "✅ Hot-swap COMPLETE: migancore:$NEXT_VER is now production"
    else
        _log "⚠️  Health check failed after swap — monitor manually"
    fi

    # Mark eval done
    python3 -c "
import json
d = json.load(open('$LAST_SUCCESS_JSON'))
d['eval_done'] = True
d['eval_decision'] = 'PROMOTE'
d['eval_weighted_avg'] = $WEIGHTED_AVG
d['production_model'] = 'migancore:$NEXT_VER'
json.dump(d, open('$LAST_SUCCESS_JSON', 'w'), indent=2)
"

else
    _log "⚠️  ROLLBACK: weighted_avg=$WEIGHTED_AVG — keeping current model"

    # Mark eval done (rollback)
    python3 -c "
import json
d = json.load(open('$LAST_SUCCESS_JSON'))
d['eval_done'] = True
d['eval_decision'] = 'ROLLBACK'
d['eval_weighted_avg'] = $WEIGHTED_AVG
json.dump(d, open('$LAST_SUCCESS_JSON', 'w'), indent=2)
"
fi

# Cleanup candidate and temp files
_log "Cleaning up candidate model and temp files..."
ollama rm "$CANDIDATE_MODEL" 2>/dev/null || true
rm -rf "$MERGED_DIR" "$WORK_DIR/adapter" 2>/dev/null || true

_log "=== Auto eval done. Decision: $DECISION ==="
