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
  "finops-cost-estimator"
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

# Detect environment: CI (GitLab/GitHub) or local kiro-cli
# In CI: use python3 stdio transport (no Docker needed inside K8s pods)
# Locally: use Docker transport with resolved absolute paths
# NOTE: ${workspaceFolder} in static mcp.json is an IDE-only variable — kiro-cli
#       cannot resolve it. This script generates a resolved config at runtime.

if [ -n "${CI:-}" ]; then
  # --- CI mode: stdio transport (Python direct) ---
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
    },
    "finops-cost-estimator": {
      "command": "python3",
      "args": ["$PROJECT_ROOT/mcp-servers/finops-cost-estimator/server.py"],
      "env": {
        "AUDIT_LOG_PATH": "$PROJECT_ROOT/audit/audit.ndjson",
        "COST_MODEL_PATH": "$PROJECT_ROOT/config/finops-cost-model.yml",
        "REPORTS_DIR": "$PROJECT_ROOT/reports/finops",
        "BASELINES_PATH": "$PROJECT_ROOT/reports/finops/baselines.json"
      },
      "disabled": false,
      "autoApprove": ["estimate_workflow_cost", "calculate_workflow_cost", "get_cost_report", "get_historical_baseline"]
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
    },
    "finops-cost-estimator": {
      "command": "docker",
      "args": [
        "run", "--init", "--rm", "-i",
        "-e", "AUDIT_LOG_PATH",
        "-e", "COST_MODEL_PATH",
        "-e", "REPORTS_DIR",
        "-e", "BASELINES_PATH",
        "-v", "$PROJECT_ROOT/audit:/audit:ro",
        "-v", "$PROJECT_ROOT/config:/config:ro",
        "-v", "$PROJECT_ROOT/reports:/reports",
        "$ECR_REGISTRY/genai-finops-cost-estimator-mcp-server:latest"
      ],
      "env": {
        "AUDIT_LOG_PATH": "/audit/audit.ndjson",
        "COST_MODEL_PATH": "/config/finops-cost-model.yml",
        "REPORTS_DIR": "/reports/finops",
        "BASELINES_PATH": "/reports/finops/baselines.json"
      },
      "disabled": false,
      "autoApprove": ["estimate_workflow_cost", "calculate_workflow_cost", "get_cost_report", "get_historical_baseline"]
    }
  }
}
EOF

fi

info "  ✓ Generated $MCP_CONFIG_FILE"
info "    Project root: $PROJECT_ROOT"
info "    Transport:    $([ -n "${CI:-}" ] && echo 'stdio (python3)' || echo 'Docker')"
info "    Agent:        developer (--agent developer)"
echo ""

# ---------------------------------------------------------------------------
# 5. Patch agent configs for CI
#
# The developer.json and devops.json agent configs define mcpServers using
# Docker transport (confluence, gitlab, jira). These cannot run in EKS pods
# (no Docker-in-Docker). In CI mode, disable Docker-only servers so kiro-cli
# doesn't try to start them. The agent's useLegacyMcpJson=true means it
# falls back to .kiro/settings/mcp.json (generated above with stdio transport)
# for audit-logger, security-scanner, git-rollback, finops-cost-estimator.
# ---------------------------------------------------------------------------
if [ -n "${CI:-}" ]; then
  info "=== Step 5: Patching Agent Configs for CI (no Docker-in-Docker) ==="

  KIRO_AGENTS_DIR="$PROJECT_ROOT/.kiro/agents"
  for agent_file in "$KIRO_AGENTS_DIR"/*.json; do
    [ -f "$agent_file" ] || continue
    agent_name=$(basename "$agent_file")

    # In CI: disable Docker-only servers (confluence, gitlab, jira).
    # Keep useLegacyMcpJson=true so kiro-cli reads .kiro/settings/mcp.json
    # (generated in Step 4 with stdio transport and resolved paths).
    python3 -c "
import json, sys

with open('$agent_file') as f:
    agent = json.load(f)

mcp = agent.get('mcpServers', {})
patched = []

# Disable Docker-only servers
docker_only = ['confluence', 'gitlab', 'jira']
for name in docker_only:
    if name in mcp:
        mcp[name]['disabled'] = True
        patched.append(f'disabled:{name}')

# Ensure useLegacyMcpJson stays true so .kiro/settings/mcp.json is used
agent['useLegacyMcpJson'] = True

with open('$agent_file', 'w') as f:
    json.dump(agent, f, indent=2)
print(f'  ✓ {\"$agent_name\"}: {patched} (useLegacyMcpJson=true)')
"
  done

  # Also patch agents/ directory (legacy location) if it exists
  LEGACY_AGENTS_DIR="$PROJECT_ROOT/agents"
  if [ -d "$LEGACY_AGENTS_DIR" ]; then
    for agent_file in "$LEGACY_AGENTS_DIR"/*.json; do
      [ -f "$agent_file" ] || continue
      agent_name=$(basename "$agent_file")
      python3 -c "
import json
with open('$agent_file') as f:
    agent = json.load(f)
docker_only = ['confluence', 'gitlab', 'jira']
mcp = agent.get('mcpServers', {})
patched = []
for name in docker_only:
    if name in mcp:
        mcp[name]['disabled'] = True
        patched.append(name)
if patched:
    with open('$agent_file', 'w') as f:
        json.dump(agent, f, indent=2)
    print(f'  ✓ {\"$agent_name\"} (legacy): disabled {patched}')
"
    done
  fi
  echo ""
fi

# ---------------------------------------------------------------------------
# Local kiro-cli usage reminder
# ---------------------------------------------------------------------------
if [ -z "${CI:-}" ]; then
  info "=== Local kiro-cli Usage ==="
  info "  MCP config has been generated with resolved absolute paths."
  info "  Run this script once before each kiro-cli session:"
  info ""
  info "    bash scripts/setup-kiro.sh && kiro-cli chat --agent developer ..."
  info ""
  info "  NOTE: The committed .kiro/settings/mcp.json uses \${workspaceFolder}"
  info "  which only works in Kiro IDE. kiro-cli REQUIRES this script to"
  info "  generate a config with resolved absolute paths."
  echo ""
fi

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
