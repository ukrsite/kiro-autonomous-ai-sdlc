# Kiro CI Runner Image
# Base image for AI workflow pipeline jobs on EKS GitLab runners.
# Includes Python 3.12, OpenJDK 21, Maven, Node.js 20, kiro-cli, and common CI dependencies.

FROM python:3.12-slim

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
      curl git unzip \
      openjdk-21-jdk-headless maven && \
    rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME via shell so it resolves correctly on both amd64 and arm64
RUN JAVA_BIN=$(readlink -f $(which java)) && \
    echo "JAVA_HOME=$(dirname $(dirname $JAVA_BIN))" >> /etc/environment && \
    echo "export JAVA_HOME=$(dirname $(dirname $JAVA_BIN))" >> /etc/profile.d/java.sh

# Install Node.js 20 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install kiro-cli via official installer
COPY kiro-install.sh /tmp/kiro-install.sh
RUN chmod +x /tmp/kiro-install.sh && \
    /tmp/kiro-install.sh --force && \
    rm /tmp/kiro-install.sh

ENV PATH="/root/.local/bin:${PATH}"

# Python CI dependencies + MCP server deps (for stdio transport in CI)
RUN pip install --no-cache-dir \
    pyyaml ruff mypy bandit safety pytest pytest-cov hypothesis \
    mcp pip-audit gitpython

WORKDIR /workspace
