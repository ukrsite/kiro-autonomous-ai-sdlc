#!/bin/bash
# cron-triggers.sh — Example crontab entries for scheduled AI workflow triggers.
# Requirements: 6.2, 6.6
#
# These entries use kiro-cli in headless (non-interactive) mode combined with
# the retry-wrapper.sh script for exponential-backoff retries.
#
# SETUP:
#   1. Ensure kiro-cli is installed and on the PATH.
#   2. Ensure scripts/retry-wrapper.sh is executable:
#        chmod +x scripts/retry-wrapper.sh
#   3. Edit your crontab:
#        crontab -e
#   4. Paste the desired entries below (uncomment them first).
#   5. Adjust WORKSPACE_DIR to the absolute path of this repository.
#
# VARIABLES (set these before the cron entries):
#   WORKSPACE_DIR=/absolute/path/to/this/repo
#   RETRY_WRAPPER=$WORKSPACE_DIR/scripts/retry-wrapper.sh
#   LOG_DIR=$WORKSPACE_DIR/logs
#
# ─── Nightly dependency security scan (every day at 2:00 AM) ───
# 0 2 * * * $RETRY_WRAPPER "kiro-cli chat --no-interactive -a 'Execute WF3 dependency upgrade for sample-app/ with scope=security'" >> $LOG_DIR/wf3-nightly.log 2>&1
#
# ─── Weekly full dependency upgrade (every Sunday at 3:00 AM) ───
# 0 3 * * 0 $RETRY_WRAPPER "kiro-cli chat --no-interactive -a 'Execute WF3 dependency upgrade for sample-app/ with scope=all'" >> $LOG_DIR/wf3-weekly.log 2>&1
#
# ─── Weekly documentation update (every Saturday at 4:00 AM) ───
# 0 4 * * 6 $RETRY_WRAPPER "kiro-cli chat --no-interactive -a 'Execute WF5 documentation workflow for sample-app/'" >> $LOG_DIR/wf5-weekly.log 2>&1
#
# ─── Nightly security scan on all code (every day at 1:00 AM) ───
# 0 1 * * * $RETRY_WRAPPER "kiro-cli chat --no-interactive -a 'Run security scan on sample-app/ using security-scanner MCP'" >> $LOG_DIR/security-nightly.log 2>&1

echo "=== Kiro Scheduled Trigger Setup ==="
echo ""
echo "This script documents the crontab entries for scheduled AI workflow triggers."
echo "It is not meant to be executed directly — copy the cron entries into your crontab."
echo ""
echo "Quick setup:"
echo "  1. Run: crontab -e"
echo "  2. Add the entries from this file (see comments above)"
echo "  3. Set WORKSPACE_DIR to: $(cd "$(dirname "$0")/.." && pwd)"
echo "  4. Create the logs directory: mkdir -p logs"
echo ""
echo "Scheduled triggers use kiro-cli in headless mode:"
echo "  kiro-cli chat --no-interactive -a \"<workflow prompt>\""
echo ""
echo "Retries are handled by scripts/retry-wrapper.sh (3 attempts, exponential backoff)."
