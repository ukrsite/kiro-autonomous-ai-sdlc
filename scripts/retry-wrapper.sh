#!/bin/bash
# retry-wrapper.sh — Retry a command with exponential backoff and rate-limit awareness.
#
# Usage: ./scripts/retry-wrapper.sh "your command here"
#
# Features:
#   - Exponential backoff: 15s → 30s → 60s → 120s → 240s
#   - Rate-limit detection: if output contains "rate limit" or "quota exceeded",
#     applies a longer cooldown (60s minimum) before retrying
#   - Captures command output to a temp file for rate-limit detection
#   - Configurable via environment variables
#
# Environment variables:
#   MAX_RETRIES       — max attempts (default: 5)
#   RETRY_DELAY       — initial delay in seconds (default: 15)
#   RATE_LIMIT_DELAY  — minimum delay on rate limit (default: 60)
#   RETRY_LOG         — path to log file (default: /tmp/retry-wrapper.log)

set -euo pipefail

MAX_RETRIES="${MAX_RETRIES:-5}"
RETRY_DELAY="${RETRY_DELAY:-15}"
RATE_LIMIT_DELAY="${RATE_LIMIT_DELAY:-60}"
RETRY_LOG="${RETRY_LOG:-/tmp/retry-wrapper.log}"
CURRENT_DELAY="$RETRY_DELAY"

if [ $# -eq 0 ]; then
  echo "Usage: $0 <command>"
  echo "Example: $0 \"kiro-cli chat --no-interactive -a 'Execute WF1'\""
  exit 1
fi

COMMAND="$1"

is_rate_limited() {
  local output_file="$1"
  if [ ! -f "$output_file" ]; then
    return 1
  fi
  # Check for common rate-limit signals (case-insensitive)
  if grep -qi "rate.limit\|quota.exceeded\|too.many.requests\|429\|throttl" "$output_file" 2>/dev/null; then
    return 0
  fi
  return 1
}

for i in $(seq 1 "$MAX_RETRIES"); do
  echo "[retry-wrapper] Attempt $i of $MAX_RETRIES"

  # Run command, tee output to both stdout and a temp file for analysis
  OUTPUT_FILE=$(mktemp /tmp/retry-output-XXXXXX)
  set +e
  eval "$COMMAND" 2>&1 | tee "$OUTPUT_FILE"
  EXIT_CODE=${PIPESTATUS[0]}
  set -e

  if [ "$EXIT_CODE" -eq 0 ]; then
    echo "[retry-wrapper] Success on attempt $i."
    rm -f "$OUTPUT_FILE"
    exit 0
  fi

  echo "[retry-wrapper] Attempt $i failed (exit code: $EXIT_CODE)."

  if [ "$i" -lt "$MAX_RETRIES" ]; then
    # Check if this was a rate limit
    if is_rate_limited "$OUTPUT_FILE"; then
      # Use the longer rate-limit delay, or current delay if already longer
      if [ "$CURRENT_DELAY" -lt "$RATE_LIMIT_DELAY" ]; then
        CURRENT_DELAY="$RATE_LIMIT_DELAY"
      fi
      echo "[retry-wrapper] Rate limit detected — waiting ${CURRENT_DELAY}s before retry..."
    else
      echo "[retry-wrapper] Retrying in ${CURRENT_DELAY}s..."
    fi

    # Log the retry event
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) attempt=$i exit=$EXIT_CODE delay=${CURRENT_DELAY}s rate_limited=$(is_rate_limited "$OUTPUT_FILE" && echo yes || echo no)" >> "$RETRY_LOG" 2>/dev/null || true

    sleep "$CURRENT_DELAY"
    # Exponential backoff: double the delay, cap at 5 minutes
    CURRENT_DELAY=$((CURRENT_DELAY * 2))
    if [ "$CURRENT_DELAY" -gt 300 ]; then
      CURRENT_DELAY=300
    fi
  fi

  rm -f "$OUTPUT_FILE"
done

echo "[retry-wrapper] All $MAX_RETRIES attempts failed."
exit 1
