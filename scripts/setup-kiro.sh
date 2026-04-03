#!/bin/bash
# setup-kiro.sh — Install Kiro CLI, verify agent/MCP server configuration,
#                  and generate Docker-based MCP server configs.
#
# Steps:
#   1. Install Kiro CLI (placeholder — not publicly available yet)
#   2. Verify agent JSON configuration files exist and are valid JSON
#   3. Verify MCP server scripts are present and importable
#   4. Generate .kiro/settings/mcp.json with Docker-based config (resolved paths)
#
# Requirements: 1.1, 1.2, 1.3, 1.5, 1.6
#
# SANDBOX BOUNDARIES:
#   - This script does NOT access production systems or credentials.
#   - All verification is performed against local files only.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

AGENTS_DIR="$PROJECT_ROOT/agents"
MCP_DIR="$PROJECT_ROOT/mcp-servers"

ECR_REGISTRY="905418281081.dkr.ecr.us-east-1.amazonaws.com"

# ---------------------------------------------------------------------------
# Helper: print a status message
# ---------------------------------------------------------------------------
info() {
  echo "[setup-kiro] $*"
}

ERRORS=0

# ---------------------------------------------------------------------------
# 1. Verify Kiro CLI is available
#
# Kiro CLI is installed via the Docker image (docker/kiro-ci/Dockerfile).
# This step only verifies it's on PATH.
# ---------------------------------------------------------------------------
info "=== Step 1: Kiro CLI Verification ==="

if command -v kiro-cli &>/dev/null; then
  info "Kiro CLI found: $(kiro-cli --version 2>/dev/null || echo 'version unknown')"
else
  info "Kiro CLI not found on PATH. Ensure it is installed in the CI image."
fi
echo ""

# ---------------------------------------------------------------------------
# 2. Verify agent configuration files
#
# Each agent JSON file defines the role, skills, and MCP server connections.
# We check that the expected files exist and contain valid JSON.
# ---------------------------------------------------------------------------
info "=== Step 2: Verifying Agent Configurations ==="

EXPECTED_AGENTS=(
  "developer.json"
  "devops.json"
)

for agent_file in "${EXPECTED_AGENTS[@]}"; do
  AGENT_PATH="$AGENTS_DIR/$agent_file"
  if [ ! -f "$AGENT_PATH" ]; then
    echo "ERROR: Agent config not found: $AGENT_PATH"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  # Validate JSON syntax
  if python3 -c "import json; json.load(open('$AGENT_PATH'))" 2>/dev/null; then
    info "  ✓ $agent_file — valid JSON"
  else
    echo "  ✗ $agent_file — INVALID JSON"
    ERRORS=$((ERRORS + 1))
  fi
done
echo ""

# ---------------------------------------------------------------------------
# 3. Verify MCP server setup
#
# Check that each MCP server directory contains server.py and requirements.txt.
# Optionally verify that server.py is importable (no syntax errors).
# ---------------------------------------------------------------------------
info "=== Step 3: Verifying MCP Server Setup ==="

MCP_SERVERS=(
  "audit-logger"
  "security-scanner"
  "dependency-scanner"
  "git-rollback"
)

for server in "${MCP_SERVERS[@]}"; do
  SERVER_DIR="$MCP_DIR/$server"
  SERVER_PY="$SERVER_DIR/server.py"
  REQ_TXT="$SERVER_DIR/requirements.txt"

  if [ ! -d "$SERVER_DIR" ]; then
    echo "  ✗ $server — directory not found"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  if [ ! -f "$SERVER_PY" ]; then
    echo "  ✗ $server — server.py not found"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  if [ ! -f "$REQ_TXT" ]; then
    echo "  ✗ $server — requirements.txt not found"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  # Check Python syntax of server.py
  if python3 -c "import py_compile; py_compile.compile('$SERVER_PY', doraise=True)" 2>/dev/null; then
    info "  ✓ $server — server.py valid, requirements.txt present"
  else
    echo "  ✗ $server — server.py has syntax errors"
    ERRORS=$((ERRORS + 1))
  fi
done
echo ""

# ---------------------------------------------------------------------------
# 4. Generate .kiro/settings/mcp.json
#
# In CI (detected via $CI variable): uses stdio transport running Python
# servers directly — no Docker needed inside Kubernetes pods.
# Locally: uses Docker-based transport with resolved absolute paths.
# ---------------------------------------------------------------------------
info "=== Step 4: Generating MCP Server Configuration ==="

MCP_CONFIG_DIR="$PROJECT_ROOT/.kiro/settings"
MCP_CONFIG_FILE="$MCP_CONFIG_DIR/mcp.json"

mkdir -p "$MCP_CONFIG_DIR"

if [ -n "${CI:-}" ]; then
  # --- CI mode: stdio transport (Python direct) ---
  # Jira/GitLab/Confluence MCP servers are Docker images that can't run in K8s pods.
  # They are excluded here — the pipeline handles Jira/GitLab API calls directly.
  info "  CI environment detected — using stdio transport"

  cat > "$MCP_CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "audit-logger": {
      "command": "python3",
      "args": ["$PROJECT_ROOT/mcp-servers/audit-logger/server.py"],
      "env": {
        "AUDIT_LOG_PATH": "$PROJECT_ROOT/audit/audit.ndjson"
      },
      "disabled": false,
      "autoApprove": ["log_interaction", "log_checkpoint", "log_event", "query_audit"]
    },
    "security-scanner": {
      "command": "python3",
      "args": ["$PROJECT_ROOT/mcp-servers/security-scanner/server.py"],
      "env": {},
      "disabled": false,
      "autoApprove": ["scan_code", "scan_dependencies", "get_scan_report"]
    },
    "dependency-scanner": {
      "command": "python3",
      "args": ["$PROJECT_ROOT/mcp-servers/dependency-scanner/server.py"],
      "env": {},
      "disabled": false,
      "autoApprove": ["scan_outdated", "check_compatibility", "get_upgrade_plan"]
    },
    "git-rollback": {
      "command": "python3",
      "args": ["$PROJECT_ROOT/mcp-servers/git-rollback/server.py"],
      "env": {
        "GIT_REPO_PATH": "$PROJECT_ROOT"
      },
      "disabled": false,
      "autoApprove": ["create_restore_point", "rollback", "verify_consistency", "list_restore_points"]
    }
  }
}
EOF

else
  # --- Local mode: Docker transport ---
  info "  Local environment — using Docker transport"

  cat > "$MCP_CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "audit-logger": {
      "command": "docker",
      "args": ["run", "--init", "--rm", "-i", "-e", "AUDIT_LOG_PATH", "-v", "$PROJECT_ROOT/audit:/audit", "$ECR_REGISTRY/genai-audit-logger-mcp-server:latest"],
      "env": {
        "AUDIT_LOG_PATH": "/audit/audit.ndjson"
      },
      "disabled": false,
      "autoApprove": ["log_interaction", "log_checkpoint", "log_event", "query_audit"]
    },
    "security-scanner": {
      "command": "docker",
      "args": ["run", "--init", "--rm", "-i", "-v", "$PROJECT_ROOT:/workspace:ro", "$ECR_REGISTRY/genai-security-scanner-mcp-server:latest"],
      "env": {},
      "disabled": false,
      "autoApprove": ["scan_code", "scan_dependencies", "get_scan_report"]
    },
    "dependency-scanner": {
      "command": "docker",
      "args": ["run", "--init", "--rm", "-i", "-v", "$PROJECT_ROOT:/workspace:ro", "$ECR_REGISTRY/genai-dependency-scanner-mcp-server:latest"],
      "env": {},
      "disabled": false,
      "autoApprove": ["scan_outdated", "check_compatibility", "get_upgrade_plan"]
    },
    "git-rollback": {
      "command": "docker",
      "args": ["run", "--init", "--rm", "-i", "-e", "GIT_REPO_PATH", "-v", "$PROJECT_ROOT:/workspace", "$ECR_REGISTRY/genai-git-rollback-mcp-server:latest"],
      "env": {
        "GIT_REPO_PATH": "/workspace"
      },
      "disabled": false,
      "autoApprove": ["create_restore_point", "rollback", "verify_consistency", "list_restore_points"]
    }
  }
}
EOF

fi

info "  ✓ Generated $MCP_CONFIG_FILE"
info "    Project root: $PROJECT_ROOT"
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
if [ "$ERRORS" -gt 0 ]; then
  info "=== Kiro Setup Complete (with $ERRORS error(s)) ==="
  info "Please fix the errors above before proceeding."
  exit 1
else
  info "=== Kiro Setup Verification Complete — All Checks Passed ==="
fi
