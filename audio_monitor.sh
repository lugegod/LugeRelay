#!/bin/bash

# Audio System Monitor and Recovery Script
# This script checks audio system health and can reinitialize if needed

APP_URL="http://localhost:5000"
LOG_FILE="/tmp/audio_monitor.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_audio_health() {
    local response=$(curl -s "$APP_URL/health" 2>/dev/null)
    if [ $? -eq 0 ]; then
        local audio_status=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if data.get('audio_initialized') else 'false')" 2>/dev/null)
        echo "$audio_status"
    else
        echo "error"
    fi
}

reinit_audio() {
    local response=$(curl -s -X POST "$APP_URL/reinit_audio" 2>/dev/null)
    if [ $? -eq 0 ]; then
        local success=$(echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print('true' if data.get('success') else 'false')" 2>/dev/null)
        echo "$success"
    else
        echo "false"
    fi
}

case "$1" in
    "check")
        status=$(check_audio_health)
        if [ "$status" = "true" ]; then
            log_message "Audio system is healthy"
            exit 0
        elif [ "$status" = "false" ]; then
            log_message "Audio system is not initialized"
            exit 1
        else
            log_message "Failed to check audio system health"
            exit 2
        fi
        ;;
    "reinit")
        log_message "Attempting to reinitialize audio system..."
        success=$(reinit_audio)
        if [ "$success" = "true" ]; then
            log_message "Audio system reinitialized successfully"
            exit 0
        else
            log_message "Failed to reinitialize audio system"
            exit 1
        fi
        ;;
    "monitor")
        log_message "Starting audio system monitoring..."
        while true; do
            status=$(check_audio_health)
            if [ "$status" = "false" ]; then
                log_message "Audio system down, attempting recovery..."
                success=$(reinit_audio)
                if [ "$success" = "true" ]; then
                    log_message "Audio system recovered successfully"
                else
                    log_message "Failed to recover audio system"
                fi
            fi
            sleep 30
        done
        ;;
    *)
        echo "Usage: $0 {check|reinit|monitor}"
        echo "  check   - Check if audio system is initialized"
        echo "  reinit  - Reinitialize the audio system"
        echo "  monitor - Continuously monitor and auto-recover audio system"
        exit 1
        ;;
esac
