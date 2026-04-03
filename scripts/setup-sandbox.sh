#!/bin/bash
# setup-sandbox.sh — Provision the sandbox environment with required runtimes.
#
# Installs Python 3.11+, Java 17+, Node JS 18+, and Git.
# Idempotent: checks if each tool is already installed at the required version
# before attempting installation.
#
# Requirements: 1.1, 1.2, 1.3, 1.5, 1.6
#
# SANDBOX BOUNDARIES:
#   - This script does NOT access production systems or credentials.
#   - All installations are local to the sandbox environment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Minimum required versions
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=11
MIN_JAVA_MAJOR=17
MIN_NODE_MAJOR=18

# ---------------------------------------------------------------------------
# Helper: print a status message
# ---------------------------------------------------------------------------
info() {
  echo "[setup-sandbox] $*"
}

# ---------------------------------------------------------------------------
# Helper: compare a detected version against a minimum requirement.
# Returns 0 (true) if detected >= required.
# ---------------------------------------------------------------------------
version_gte() {
  local detected_major="$1"
  local detected_minor="$2"
  local required_major="$3"
  local required_minor="$4"

  if [ "$detected_major" -gt "$required_major" ]; then
    return 0
  elif [ "$detected_major" -eq "$required_major" ] && [ "$detected_minor" -ge "$required_minor" ]; then
    return 0
  fi
  return 1
}

# ---------------------------------------------------------------------------
# Detect the OS package manager
# ---------------------------------------------------------------------------
detect_package_manager() {
  if command -v apt-get &>/dev/null; then
    echo "apt"
  elif command -v yum &>/dev/null; then
    echo "yum"
  elif command -v dnf &>/dev/null; then
    echo "dnf"
  elif command -v brew &>/dev/null; then
    echo "brew"
  else
    echo "unknown"
  fi
}

PKG_MANAGER="$(detect_package_manager)"
info "Detected package manager: $PKG_MANAGER"

# ---------------------------------------------------------------------------
# 1. Git — required for version control within the sandbox
# ---------------------------------------------------------------------------
if command -v git &>/dev/null; then
  GIT_VERSION="$(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
  info "Git already installed: v$GIT_VERSION"
else
  info "Installing Git..."
  case "$PKG_MANAGER" in
    apt)  sudo apt-get update && sudo apt-get install -y git ;;
    yum)  sudo yum install -y git ;;
    dnf)  sudo dnf install -y git ;;
    brew) brew install git ;;
    *)    echo "ERROR: Unsupported package manager. Install Git manually." && exit 1 ;;
  esac
  info "Git installed: $(git --version)"
fi

# ---------------------------------------------------------------------------
# 2. Python 3.11+ — required for MCP servers and Python sample module
# ---------------------------------------------------------------------------
PYTHON_CMD=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    PY_VER="$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')"
    PY_MAJOR="${PY_VER%%.*}"
    PY_MINOR="${PY_VER##*.}"
    if version_gte "$PY_MAJOR" "$PY_MINOR" "$MIN_PYTHON_MAJOR" "$MIN_PYTHON_MINOR"; then
      PYTHON_CMD="$cmd"
      break
    fi
  fi
done

if [ -n "$PYTHON_CMD" ]; then
  info "Python already installed: $($PYTHON_CMD --version)"
else
  info "Installing Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+..."
  case "$PKG_MANAGER" in
    apt)
      sudo apt-get update
      sudo apt-get install -y python3.11 python3.11-venv python3-pip
      ;;
    yum|dnf)
      sudo "$PKG_MANAGER" install -y python3.11 python3.11-pip
      ;;
    brew)
      brew install python@3.11
      ;;
    *)
      echo "ERROR: Unsupported package manager. Install Python 3.11+ manually." && exit 1
      ;;
  esac
  info "Python installed: $(python3 --version)"
fi

# ---------------------------------------------------------------------------
# 3. Java 17+ — required for Java sample module (Maven builds)
# ---------------------------------------------------------------------------
JAVA_INSTALLED=false
if command -v java &>/dev/null; then
  JAVA_VER="$(java -version 2>&1 | head -1 | grep -oE '[0-9]+' | head -1)"
  if [ "$JAVA_VER" -ge "$MIN_JAVA_MAJOR" ] 2>/dev/null; then
    JAVA_INSTALLED=true
    info "Java already installed: version $JAVA_VER"
  fi
fi

if [ "$JAVA_INSTALLED" = false ]; then
  info "Installing Java ${MIN_JAVA_MAJOR}+..."
  case "$PKG_MANAGER" in
    apt)
      sudo apt-get update
      sudo apt-get install -y openjdk-17-jdk
      ;;
    yum|dnf)
      sudo "$PKG_MANAGER" install -y java-17-openjdk-devel
      ;;
    brew)
      brew install openjdk@17
      ;;
    *)
      echo "ERROR: Unsupported package manager. Install Java 17+ manually." && exit 1
      ;;
  esac
  info "Java installed: $(java -version 2>&1 | head -1)"
fi

# ---------------------------------------------------------------------------
# 4. Node JS 18+ — required for Node JS sample module
# ---------------------------------------------------------------------------
NODE_INSTALLED=false
if command -v node &>/dev/null; then
  NODE_VER="$(node --version | grep -oE '[0-9]+' | head -1)"
  if [ "$NODE_VER" -ge "$MIN_NODE_MAJOR" ] 2>/dev/null; then
    NODE_INSTALLED=true
    info "Node JS already installed: $(node --version)"
  fi
fi

if [ "$NODE_INSTALLED" = false ]; then
  info "Installing Node JS ${MIN_NODE_MAJOR}+..."
  case "$PKG_MANAGER" in
    apt)
      # Use NodeSource repository for up-to-date Node JS
      curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
      sudo apt-get install -y nodejs
      ;;
    yum|dnf)
      curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
      sudo "$PKG_MANAGER" install -y nodejs
      ;;
    brew)
      brew install node@18
      ;;
    *)
      echo "ERROR: Unsupported package manager. Install Node JS 18+ manually." && exit 1
      ;;
  esac
  info "Node JS installed: $(node --version)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
info "=== Sandbox Environment Setup Complete ==="
info "Git:    $(git --version)"
info "Python: $(python3 --version 2>&1)"
info "Java:   $(java -version 2>&1 | head -1)"
info "Node:   $(node --version 2>&1)"
echo ""
info "Next step: run scripts/install-mcp-servers.sh to install MCP server dependencies."
