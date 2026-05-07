#!/bin/bash
# Kill Ollama runner subprocesses that have been running >30min
# Lesson #133: Stuck ollama runner = 692% CPU steal, blocks ALL inference
# Run via cron every 15min: */15 * * * * /opt/ado/scripts/kill_stuck_ollama_runners.sh

THRESHOLD_MINUTES=30
LOG=/tmp/ollama_runner_watchdog.log

# Find ollama runner processes older than threshold
while IFS= read -r line; do
    pid=$(echo "$line" | awk '{print $2}')
    elapsed=$(echo "$line" | awk '{print $10}')  # CPU time in h:mm or mm:ss

    # Convert elapsed to minutes (rough)
    if echo "$elapsed" | grep -q ':'; then
        hrs=$(echo "$elapsed" | cut -d: -f1)
        mins=$(echo "$elapsed" | cut -d: -f2 | cut -d: -f1)
        total_min=$((hrs * 60 + mins))
    else
        total_min=0
    fi

    if [ "$total_min" -ge "$THRESHOLD_MINUTES" ]; then
        cpu=$(echo "$line" | awk '{print $3}')
        echo "$(date): Killing stuck ollama runner PID=$pid elapsed=${elapsed} CPU=${cpu}%" >> $LOG
        kill -9 "$pid" 2>/dev/null
    fi
done < <(ps aux | grep 'ollama runner' | grep -v grep)
