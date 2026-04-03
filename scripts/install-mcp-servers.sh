#!/bin/bash
# install-mcp-servers.sh — Install dependencies for all MCP servers.
#
# Installs Python packages from each MCP server's requirements.txt:
#   - audit-logger:       mcp SDK
#   - security-scanner:   mcp SDK, bandit, safety
#   - dependency-scanner: mcp SDK, pip-audit
#   - git-rollback:       mcp SDK, gitpython
#
# Requirements: 1.1, 1.2, 1.3, 1.5, 1.6
#
# SANDBOX BOUNDARIES:
#   - This script does NOT access production systems or credentials.
#   - All packages are installed locally (pip install).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

MCP_DIR="$PROJECT_ROOT/mcp-servers"

# ---------------------------------------------------------------------------
# Helper: print a status message
# ---------------------------------------------------------------------------
info() {
  echo "[install-mcp-servers] $*"
}

# ---------------------------------------------------------------------------
# Verify Python 3 and pip are available
# ---------------------------------------------------------------------------
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Run scripts/setup-sandbox.sh first."
  exit 1
fi

if ! python3 -m pip --version &>/dev/null; then
  echo "ERROR: pip not found. Ensure pip is installed for python3."
  exit 1
fi

info "Using Python: $(python3 --version)"
info "Using pip:    $(python3 -m pip --version)"
echo ""

# ---------------------------------------------------------------------------
# MCP servers to install — each subdirectory must contain a requirements.txt
# ---------------------------------------------------------------------------
MCP_SERVERS=(
  "audit-logger"
  "security-scanner"
  "dependency-scanner"
  "git-rollback"
)

FAILED=0

for server in "${MCP_SERVERS[@]}"; do
  REQ_FILE="$MCP_DIR/$server/requirements.txt"

  if [ ! -f "$REQ_FILE" ]; then
    echo "WARNING: $REQ_FILE not found — skipping $server"
    FAILED=$((FAILED + 1))
    continue
  fi

  info "Installing dependencies for $server..."
  if python3 -m pip install -r "$REQ_FILE" --quiet; then
    info "$server — dependencies installed successfully."
  else
    echo "ERROR: Failed to install dependencies for $server"
    FAILED=$((FAILED + 1))
  fi
  echo ""
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
if [ "$FAILED" -gt 0 ]; then
  echo ""
  info "=== MCP Server Installation Complete (with $FAILED warning(s)/error(s)) ==="
  exit 1
else
  echo ""
  info "=== All MCP Server Dependencies Installed Successfully ==="
fi

info "Next step: run scripts/setup-kiro.sh to configure Kiro CLI and verify the setup."
