#!/bin/bash
# Script to view Django application logs

LOG_FILE="/root/seminer/logs/django.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "Log file not found: $LOG_FILE"
    exit 1
fi

echo "=== Django Application Logs ==="
echo "Press Ctrl+C to exit"
echo ""
tail -f "$LOG_FILE"
