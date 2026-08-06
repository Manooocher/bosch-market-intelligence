#!/bin/bash
# Production bootstrap wrapper script
# Usage: ./bootstrap.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/data/logs"
LOG_FILE="$LOG_DIR/bootstrap_$(date +%Y%m%d).log"

mkdir -p "$LOG_DIR"

echo "$(date -Iseconds) [START] Bootstrap initiated"

cd "$PROJECT_DIR"
python -m cli.bootstrap >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$(date -Iseconds) [OK] Bootstrap completed successfully" >> "$LOG_FILE"
else
    echo "$(date -Iseconds) [FAIL] Bootstrap failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

echo "$(date -Iseconds) [END] Bootstrap finished (exit code: $EXIT_CODE)"
exit $EXIT_CODE
