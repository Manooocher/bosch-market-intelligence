#!/bin/bash
# Production monitor wrapper script for Linux/cron
# Usage: ./monitor.sh
# Cron: 0 6 * * * /path/to/scripts/monitor.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/data/logs"
LOCK_FILE="$PROJECT_DIR/data/.monitor.lock"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Log file with date
LOG_FILE="$LOG_DIR/monitor_$(date +%Y%m%d).log"

echo "$(date -Iseconds) [START] Monitor run initiated"

# Check if another instance is running
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null)
    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "$(date -Iseconds) [ERROR] Monitor already running (PID $LOCK_PID)"
        exit 1
    else
        echo "$(date -Iseconds) [WARN] Stale lock file found, removing"
        rm -f "$LOCK_FILE"
    fi
fi

# Run monitor
cd "$PROJECT_DIR"
python -m cli.monitor >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# Log result
if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date -Iseconds) [OK] Monitor completed successfully" >> "$LOG_FILE"
else
    echo "$(date -Iseconds) [FAIL] Monitor failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

# Rotate logs older than 30 days
find "$LOG_DIR" -name "monitor_*.log" -mtime +30 -delete 2>/dev/null

echo "$(date -Iseconds) [END] Monitor run finished (exit code: $EXIT_CODE)"
exit $EXIT_CODE
