#!/bin/bash
# VPS-side recovery downloader for Cycle 6 adapter
# Runs on VPS, periodically SSHs to Vast.ai to check training and download

VAST_SSH_KEY="/root/.ssh/id_ed25519"
VAST_HOST="ssh7.vast.ai"
VAST_PORT=15754
VAST_KEY_FILE="/root/.vastai_api_key"
INSTANCE_ID=36295755
LOCAL_ADAPTER="/opt/ado/cycle6_output/cycle6_adapter"
LOG="/tmp/vast_recovery.log"

echo "[$(date -u +%H:%M) UTC] VPS recovery monitor started (instance $INSTANCE_ID)" | tee -a $LOG
mkdir -p "$LOCAL_ADAPTER"

while true; do
    sleep 600  # Check every 10 minutes
    
    echo "[$(date -u +%H:%M) UTC] Checking Vast.ai training status..." | tee -a $LOG
    
    # Check if training is done (adapter_config.json present on Vast.ai)
    ADAPTER_READY=$(ssh -i "$VAST_SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=20 -p "$VAST_PORT" root@"$VAST_HOST" \
        "ls /root/cycle6_adapter/adapter_config.json 2>/dev/null && echo READY || echo NOT_READY" 2>/dev/null || echo "SSH_FAIL")
    
    echo "[$(date -u +%H:%M) UTC] Adapter status: $ADAPTER_READY" | tee -a $LOG
    
    if [[ "$ADAPTER_READY" == "READY" ]]; then
        echo "[$(date -u +%H:%M) UTC] Adapter READY! Downloading from Vast.ai..." | tee -a $LOG
        
        # Download adapter files
        for fname in adapter_model.safetensors adapter_config.json; do
            scp -i "$VAST_SSH_KEY" -o StrictHostKeyChecking=no -P "$VAST_PORT" \
                root@"$VAST_HOST":/root/cycle6_adapter/"$fname" \
                "$LOCAL_ADAPTER/$fname" 2>&1 | tee -a $LOG
        done
        
        # Verify download
        SAFETENSOR_OK=$(ls "$LOCAL_ADAPTER/adapter_model.safetensors" 2>/dev/null && echo "OK" || echo "MISSING")
        CONFIG_OK=$(ls "$LOCAL_ADAPTER/adapter_config.json" 2>/dev/null && echo "OK" || echo "MISSING")
        
        echo "[$(date -u +%H:%M) UTC] Download: safetensors=$SAFETENSOR_OK config=$CONFIG_OK" | tee -a $LOG
        
        if [[ "$SAFETENSOR_OK" == "OK" && "$CONFIG_OK" == "OK" ]]; then
            echo "[$(date -u +%H:%M) UTC] Both files downloaded! Deleting Vast.ai instance..." | tee -a $LOG
            
            # Delete instance
            VAST_KEY=$(cat "$VAST_KEY_FILE")
            curl -s -X DELETE "https://console.vast.ai/api/v0/instances/$INSTANCE_ID/?api_key=$VAST_KEY" | tee -a $LOG
            
            echo "[$(date -u +%H:%M) UTC] Instance $INSTANCE_ID deleted. Recovery complete." | tee -a $LOG
            break
        fi
    elif [[ "$ADAPTER_READY" == "SSH_FAIL" ]]; then
        echo "[$(date -u +%H:%M) UTC] SSH failed - instance may have been deleted already. Checking local adapter..." | tee -a $LOG
        SAFETENSOR_OK=$(ls "$LOCAL_ADAPTER/adapter_model.safetensors" 2>/dev/null && echo "OK" || echo "MISSING")
        if [[ "$SAFETENSOR_OK" == "OK" ]]; then
            echo "[$(date -u +%H:%M) UTC] Local adapter exists - training completed previously. Done." | tee -a $LOG
            break
        fi
    fi
done
echo "[$(date -u +%H:%M) UTC] VPS recovery monitor EXIT" | tee -a $LOG
