#!/bin/bash
LOG=/tmp/wait_cycle6.log
ADAPTER_DIR="/opt/ado/cycle6_output/cycle6_adapter"

echo "[$(date -u +%H:%M) UTC] Waiting for Cycle 6 adapter at $ADAPTER_DIR..." | tee -a $LOG

while true; do
    # Check for BOTH required files (avoid race condition during SCP download)
    SAFETENSOR=$(ls "$ADAPTER_DIR"/*.safetensors 2>/dev/null | wc -l)
    CONFIG=$(ls "$ADAPTER_DIR"/adapter_config.json 2>/dev/null | wc -l)
    
    if [[ $SAFETENSOR -gt 0 && $CONFIG -gt 0 ]]; then
        echo "[$(date -u +%H:%M) UTC] Adapter READY (.safetensors=$SAFETENSOR + config=$CONFIG)!" | tee -a $LOG
        sleep 5  # Let SCP fully complete
        echo "[$(date -u +%H:%M) UTC] Running post_cycle6.sh..." | tee -a $LOG
        bash /opt/ado/scripts/post_cycle6.sh 2>&1 | tee -a $LOG
        echo "[$(date -u +%H:%M) UTC] POST CYCLE 6 COMPLETE" | tee -a $LOG
        break
    fi
    
    # Check that cycle6_orpo_vast.py is still running (did not crash)
    MONITOR_PID=$(pgrep -f cycle6_orpo_vast.py || echo "")
    if [[ -z "$MONITOR_PID" ]]; then
        echo "[$(date -u +%H:%M) UTC] WARNING: cycle6_orpo_vast.py not running. Adapter files: safetensor=$SAFETENSOR config=$CONFIG" | tee -a $LOG
        # Check if adapter appeared anyway
        if [[ $SAFETENSOR -gt 0 ]]; then
            echo "[$(date -u +%H:%M) UTC] Safetensor found but no config — waiting 60s for SCP to finish" | tee -a $LOG
            sleep 60
            continue
        fi
        echo "[$(date -u +%H:%M) UTC] Monitor exited with no adapter — check $LOG manually" | tee -a $LOG
        break
    fi
    
    echo "[$(date -u +%H:%M) UTC] Training in progress... (safetensor=$SAFETENSOR config=$CONFIG monitor_pid=$MONITOR_PID)" | tee -a $LOG
    sleep 300
done
