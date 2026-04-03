#!/bin/bash
# generate-docs.sh — Generate release notes, API changelog, and architecture
# diagram from workflow execution artifacts.
#
# Called by the finalize stage after all checkpoint-gates pass.
# Reads workflow-output/ and checkpoint-output/ artifacts to produce
# documentation in finalize-output/docs/.
#
# Usage:
#   JIRA_ISSUE_KEY=SAN-2 \
#   WORKFLOW=wf1-requirement-to-software \
#   SANDBOX_PATH=sandbox/services/python-processor \
#   REPO_PATH=services/python-processor \
#   ISSUE_SUMMARY="As a manager, I want to deactivate user accounts" \
#   MR_URL="https://gitlab.internal.ericsson.com/.../merge_requests/9" \
#   bash scripts/generate-docs.sh
#
# Output:
#   finalize-output/docs/release-notes.md
#   finalize-output/docs/api-changelog-entry.md
#   finalize-output/docs/architecture-diagram.md  (Mermaid)
#   finalize-output/docs/openapi.yaml              (if REST endpoints detected)

set -euo pipefail

DOCS_DIR="finalize-output/docs"
mkdir -p "$DOCS_DIR"

ISSUE_KEY="${JIRA_ISSUE_KEY:-UNKNOWN}"
WORKFLOW="${WORKFLOW:-wf1-requirement-to-software}"
SANDBOX="${SANDBOX_PATH:-sandbox}"
REPO="${REPO_PATH:-}"
SUMMARY="${ISSUE_SUMMARY:-AI-generated changes}"
MR="${MR_URL:-N/A}"
PIPELINE_URL="${CI_PIPELINE_URL:-N/A}"
DATE=$(date -u +%Y-%m-%d)
export DATE
export DOCS_DIR
# Branch name follows workflow/{name}/{key-lowercase} convention
BRANCH_NAME="workflow/${WORKFLOW}/$(echo "${ISSUE_KEY}" | tr '[:upper:]' '[:lower:]')"
export BRANCH_NAME

echo "=== Generating documentation for $ISSUE_KEY ==="

# ---------------------------------------------------------------------------
# 1. Release Notes
# ---------------------------------------------------------------------------
echo "--- Generating release notes ---"

python3 << 'PYEOF'
import json, os, glob

issue_key = os.environ.get("JIRA_ISSUE_KEY", "UNKNOWN")
workflow = os.environ.get("WORKFLOW", "")
summary = os.environ.get("ISSUE_SUMMARY", "")
mr_url = os.environ.get("MR_URL", "N/A")
pipeline_url = os.environ.get("CI_PIPELINE_URL", "N/A")
sandbox = os.environ.get("SANDBOX_PATH", "")
date = os.environ.get("DATE", "")
docs_dir = os.environ.get("DOCS_DIR", "finalize-output/docs")
branch_name = f"workflow/{workflow}/{issue_key.lower()}"

# Collect changed files from git diff (if available)
changed_files = []
try:
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "--cached", "FETCH_HEAD"],
        capture_output=True, text=True, cwd="sandbox"
    )
    if result.returncode == 0:
        changed_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
except Exception:
    pass

# Collect test results
tests_passed = tests_failed = 0
try:
    wf_result = glob.glob("workflow-output/wf*-result.json")
    if wf_result:
        with open(wf_result[0]) as f:
            data = json.load(f)
        cp = data.get("checkpoints", {}).get("test_coverage", {})
        tests_passed = cp.get("tests_passed", 0)
        tests_failed = cp.get("tests_failed", 0)
except Exception:
    pass

# Collect security results
security_findings = 0
try:
    for report in glob.glob("checkpoint-output/bandit-*.json"):
        with open(report) as f:
            data = json.load(f)
        security_findings += len(data.get("results", []))
except Exception:
    pass

# Detect new endpoints (Python FastAPI)
new_endpoints = []
try:
    for py_file in glob.glob(f"{sandbox}/src/**/*.py", recursive=True):
        with open(py_file) as f:
            for line in f:
                line = line.strip()
                for method in ("get", "post", "put", "delete", "patch"):
                    decorator = f"@app.{method}("
                    if decorator in line:
                        path = line.split('"')[1] if '"' in line else line.split("'")[1] if "'" in line else "?"
                        new_endpoints.append(f"| {method.upper()} | `{path}` | — | New |")
except Exception:
    pass

# Build release notes
lines = [
    f"# Release Notes — {issue_key}\n",
    f"## Summary\n",
    f"- **Issue:** {issue_key}",
    f"- **Title:** {summary}",
    f"- **Workflow:** `{workflow}`",
    f"- **Date:** {date}",
    f"- **Branch:** `{branch_name}`",
    f"- **MR:** {mr_url}",
    f"- **Pipeline:** {pipeline_url}\n",
    f"## Changes\n",
    f"### Files Modified\n",
]
if changed_files:
    for f in changed_files:
        lines.append(f"- `{f}`")
else:
    lines.append("- _(no diff available)_")

if new_endpoints:
    lines.append(f"\n## API Changes\n")
    lines.append("| Method | Endpoint | Description | Status |")
    lines.append("|--------|----------|-------------|--------|")
    lines.extend(new_endpoints)

lines.extend([
    f"\n## Test Results\n",
    f"| Metric | Value |",
    f"|--------|-------|",
    f"| Tests passed | {tests_passed} |",
    f"| Tests failed | {tests_failed} |",
    f"\n## Security\n",
    f"- Bandit findings: {security_findings}",
    f"\n## Rollback\n",
    f"```bash",
    f"# Revert via MR or:",
    f"git revert {branch_name}",
    f"```\n",
])

with open(f"{docs_dir}/release-notes.md", "w") as f:
    f.write("\n".join(lines))

print(f"  ✓ {docs_dir}/release-notes.md")
PYEOF

# ---------------------------------------------------------------------------
# 2. API Changelog Entry
# ---------------------------------------------------------------------------
echo "--- Generating API changelog entry ---"

python3 << 'PYEOF'
import os, glob

issue_key = os.environ.get("JIRA_ISSUE_KEY", "UNKNOWN")
sandbox = os.environ.get("SANDBOX_PATH", "")
date = os.environ.get("DATE", "")
docs_dir = os.environ.get("DOCS_DIR", "finalize-output/docs")

added = []
try:
    for py_file in glob.glob(f"{sandbox}/src/**/*.py", recursive=True):
        with open(py_file) as f:
            for line in f:
                line = line.strip()
                for method in ("get", "post", "put", "delete", "patch"):
                    decorator = f"@app.{method}("
                    if decorator in line:
                        path = line.split('"')[1] if '"' in line else line.split("'")[1] if "'" in line else "?"
                        added.append(f"- `{method.upper()} {path}`")
except Exception:
    pass

if added:
    lines = [
        f"## [{issue_key}] — {date}\n",
        "### Added\n",
    ]
    lines.extend(added)
    lines.append("")

    with open(f"{docs_dir}/api-changelog-entry.md", "w") as f:
        f.write("\n".join(lines))
    print(f"  ✓ {docs_dir}/api-changelog-entry.md")
else:
    print("  — No API changes detected, skipping changelog entry")
PYEOF

# ---------------------------------------------------------------------------
# 3. Architecture Diagram (Mermaid)
# ---------------------------------------------------------------------------
echo "--- Generating architecture diagram ---"

python3 << 'PYEOF'
import os, glob

sandbox = os.environ.get("SANDBOX_PATH", "")
repo = os.environ.get("REPO_PATH", "")
docs_dir = os.environ.get("DOCS_DIR", "finalize-output/docs")

# Detect service type and endpoints
endpoints = []
service_type = "Service"
try:
    for py_file in glob.glob(f"{sandbox}/src/**/*.py", recursive=True):
        with open(py_file) as f:
            content = f.read()
        if "FastAPI" in content:
            service_type = "FastAPI"
        for line in content.split("\n"):
            line = line.strip()
            for method in ("get", "post", "put", "delete", "patch"):
                decorator = f"@app.{method}("
                if decorator in line:
                    path = line.split('"')[1] if '"' in line else line.split("'")[1] if "'" in line else "?"
                    endpoints.append((method.upper(), path))
    for java_file in glob.glob(f"{sandbox}/src/**/*.java", recursive=True):
        service_type = "Spring Boot"
        break
    for js_file in glob.glob(f"{sandbox}/src/**/*.js", recursive=True):
        with open(js_file) as f:
            if "express" in f.read():
                service_type = "Express"
        break
except Exception:
    pass

lines = [
    "# Architecture Diagram\n",
    f"Service: `{repo}` ({service_type})\n",
    "```mermaid",
    "graph TD",
    f'    Client["Client / API Consumer"]',
    f'    Service["{repo}<br/>{service_type}"]',
    '    Client -->|"HTTP"| Service',
]

for method, path in endpoints:
    safe_id = path.replace("/", "_").replace("{", "").replace("}", "").strip("_")
    lines.append(f'    Service -->|"{method}"| EP_{safe_id}["{method} {path}"]')


try:
    for py_file in glob.glob(f"{sandbox}/src/**/*.py", recursive=True):
        with open(py_file) as f:
            content = f.read()
        if "httpx" in content or "requests" in content:
            lines.append('    Service -->|"HTTP"| ExtAPI["External API"]')
            break
except Exception:
    pass

lines.extend([
    "```\n",
    "## Endpoint Summary\n",
    "| Method | Path |",
    "|--------|------|",
])
for method, path in endpoints:
    lines.append(f"| {method} | `{path}` |")

if not endpoints:
    lines.append("| — | No endpoints detected |")

lines.append("")

with open(f"{docs_dir}/architecture-diagram.md", "w") as f:
    f.write("\n".join(lines))

print(f"  ✓ {docs_dir}/architecture-diagram.md")
PYEOF

# ---------------------------------------------------------------------------
# 4. OpenAPI Spec (if REST endpoints detected)
# ---------------------------------------------------------------------------
echo "--- Generating OpenAPI spec ---"

python3 << 'PYEOF'
import os, glob, re

sandbox = os.environ.get("SANDBOX_PATH", "")
repo = os.environ.get("REPO_PATH", "")
issue_key = os.environ.get("JIRA_ISSUE_KEY", "UNKNOWN")
workflow = os.environ.get("WORKFLOW", "")
docs_dir = os.environ.get("DOCS_DIR", "finalize-output/docs")

endpoints = []
models = {}

try:
    for py_file in sorted(glob.glob(f"{sandbox}/src/**/*.py", recursive=True)):
        with open(py_file) as f:
            content = f.read()
            lines_list = content.split("\n")

        # Detect FastAPI route decorators
        for i, line in enumerate(lines_list):
            stripped = line.strip()
            for method in ("get", "post", "put", "delete", "patch"):
                decorator = f"@app.{method}("
                if decorator in stripped:
                    path = stripped.split('"')[1] if '"' in stripped else stripped.split("'")[1] if "'" in stripped else None
                    if not path:
                        continue
                    func_name = ""
                    description = ""
                    if i + 1 < len(lines_list):
                        func_line = lines_list[i + 1].strip()
                        match = re.match(r"def\s+(\w+)", func_line)
                        if match:
                            func_name = match.group(1)
                    if i + 2 < len(lines_list):
                        doc_line = lines_list[i + 2].strip().strip('"""').strip("'''")
                        if doc_line and not doc_line.startswith("def "):
                            description = doc_line

                    endpoints.append({
                        "method": method,
                        "path": path,
                        "operation_id": func_name,
                        "description": description,
                    })

        # Detect Pydantic models
        for i, line in enumerate(lines_list):
            match = re.match(r"class\s+(\w+)\(BaseModel\):", line.strip())
            if match:
                model_name = match.group(1)
                props = {}
                for j in range(i + 1, min(i + 20, len(lines_list))):
                    prop_line = lines_list[j].strip()
                    if prop_line.startswith("class ") or prop_line.startswith("def ") or prop_line.startswith("@"):
                        break
                    prop_match = re.match(r"(\w+):\s*([\w\[\],\s|]+)", prop_line)
                    if prop_match:
                        pname = prop_match.group(1)
                        ptype = prop_match.group(2).strip()
                        if pname.startswith("_"):
                            continue
                        json_type = "string"
                        if "int" in ptype:
                            json_type = "integer"
                        elif "float" in ptype:
                            json_type = "number"
                        elif "bool" in ptype:
                            json_type = "boolean"
                        elif "dict" in ptype:
                            json_type = "object"
                        elif "list" in ptype or "List" in ptype:
                            json_type = "array"
                        required = "Optional" not in ptype and "None" not in ptype and "=" not in prop_line
                        props[pname] = {"type": json_type, "required": required}
                if props:
                    models[model_name] = props
except Exception:
    pass

if not endpoints:
    print("  — No REST endpoints detected, skipping OpenAPI spec")
    exit(0)

# Build OpenAPI YAML manually (no pyyaml dependency needed)
spec_lines = [
    'openapi: "3.0.3"',
    "info:",
    f'  title: "{repo} API"',
    '  version: "1.0.0"',
    f"  description: |",
    f"    Auto-generated API specification for {repo}.",
    f"    Generated by Kiro CI workflow {workflow} for {issue_key}.",
    "servers:",
    '  - url: "http://localhost:8000"',
    '    description: "Local development"',
    "paths:",
]

for ep in endpoints:
    spec_lines.append(f'  {ep["path"]}:')
    spec_lines.append(f'    {ep["method"]}:')
    spec_lines.append(f'      summary: "{ep["description"] or ep["operation_id"]}"')
    spec_lines.append(f'      operationId: {ep["operation_id"]}')
    if ep["method"] == "post":
        spec_lines.append("      requestBody:")
        spec_lines.append("        required: true")
        spec_lines.append("        content:")
        spec_lines.append("          application/json:")
        spec_lines.append("            schema:")
        spec_lines.append('              type: object')
    spec_lines.append("      responses:")
    spec_lines.append('        "200":')
    spec_lines.append('          description: "Success"')

if models:
    spec_lines.append("components:")
    spec_lines.append("  schemas:")
    for model_name, props in models.items():
        spec_lines.append(f"    {model_name}:")
        spec_lines.append("      type: object")
        required_fields = [k for k, v in props.items() if v.get("required")]
        if required_fields:
            spec_lines.append("      required:")
            for rf in required_fields:
                spec_lines.append(f"        - {rf}")
        spec_lines.append("      properties:")
        for pname, pinfo in props.items():
            spec_lines.append(f"        {pname}:")
            spec_lines.append(f'          type: {pinfo["type"]}')

with open(f"{docs_dir}/openapi.yaml", "w") as f:
    f.write("\n".join(spec_lines) + "\n")

print(f"  ✓ {docs_dir}/openapi.yaml ({len(endpoints)} endpoints, {len(models)} schemas)")
PYEOF

echo "=== Documentation generation complete ==="
