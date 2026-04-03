#!/bin/bash
# retry-wrapper.sh — Retry a command up to 3 times with exponential backoff.
# Usage: ./scripts/retry-wrapper.sh "your command here"
# Requirements: 6.6

set -euo pipefail

MAX_RETRIES=3
RETRY_DELAY=10

if [ $# -eq 0 ]; then
  echo "Usage: $0 <command>"
  echo "Example: $0 \"kiro-cli chat --no-interactive -a 'Execute WF3 dependency upgrade'\""
  exit 1
fi

COMMAND="$1"

for i in $(seq 1 "$MAX_RETRIES"); do
  echo "[retry-wrapper] Attempt $i of $MAX_RETRIES: $COMMAND"
  if eval "$COMMAND"; then
    echo "[retry-wrapper] Success on attempt $i."
    exit 0
  fi
  echo "[retry-wrapper] Attempt $i failed."
  if [ "$i" -lt "$MAX_RETRIES" ]; then
    echo "[retry-wrapper] Retrying in ${RETRY_DELAY}s..."
    sleep "$RETRY_DELAY"
    RETRY_DELAY=$((RETRY_DELAY * 2))
  fi
done

echo "[retry-wrapper] All $MAX_RETRIES attempts failed."
exit 1
