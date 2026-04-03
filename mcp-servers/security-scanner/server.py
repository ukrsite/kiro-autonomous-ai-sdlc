"""Security Scanner MCP Server.

Wraps existing security scanning tools for each supported language (Python, Node JS, Java).
Exposes tools for running code security scans, dependency vulnerability scans, and
retrieving detailed scan reports. Returns structured results with severity levels.
"""

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from enum import Enum
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("security-scanner")

# In-memory store for scan reports keyed by scan_id
_scan_reports: dict[str, dict] = {}

SUPPORTED_LANGUAGES = ("python", "node", "java")


class Severity(str, Enum):
    """Severity levels for security findings."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def _generate_scan_id() -> str:
    """Generate a unique scan identifier."""
    return str(uuid.uuid4())


def _now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _store_report(scan_id: str, report: dict) -> None:
    """Store a scan report in the in-memory report store."""
    _scan_reports[scan_id] = report


def _map_bandit_severity(severity: str) -> str:
    """Map bandit severity strings to our Severity enum values."""
    mapping = {"HIGH": Severity.HIGH.value, "MEDIUM": Severity.MEDIUM.value, "LOW": Severity.LOW.value}
    return mapping.get(severity.upper(), Severity.LOW.value)


def _map_bandit_confidence_to_severity(severity: str, confidence: str) -> str:
    """Elevate severity to CRITICAL when both severity and confidence are HIGH."""
    if severity.upper() == "HIGH" and confidence.upper() == "HIGH":
        return Severity.CRITICAL.value
    return _map_bandit_severity(severity)


def _run_bandit(path: str) -> dict:
    """Run bandit security scan on Python code.

    Args:
        path: Path to the Python source directory or file.

    Returns:
        A dict with scan findings and metadata.
    """
    try:
        result = subprocess.run(
            ["bandit", "-r", path, "-f", "json"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return {
            "tool": "bandit",
            "status": "error",
            "error": "bandit is not installed. Install it with: pip install bandit",
            "findings": [],
        }

    findings: list[dict] = []
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
        for issue in data.get("results", []):
            findings.append({
                "severity": _map_bandit_confidence_to_severity(
                    issue.get("issue_severity", "LOW"),
                    issue.get("issue_confidence", "LOW"),
                ),
                "description": issue.get("issue_text", ""),
                "file": issue.get("filename", ""),
                "line": issue.get("line_number", 0),
                "rule_id": issue.get("test_id", ""),
            })
    except (json.JSONDecodeError, KeyError):
        return {
            "tool": "bandit",
            "status": "error",
            "error": f"Failed to parse bandit output: {result.stderr or result.stdout}",
            "findings": [],
        }

    return {"tool": "bandit", "status": "completed", "findings": findings}


def _map_npm_severity(severity: str) -> str:
    """Map npm audit severity strings to our Severity enum values."""
    mapping = {
        "critical": Severity.CRITICAL.value,
        "high": Severity.HIGH.value,
        "moderate": Severity.MEDIUM.value,
        "low": Severity.LOW.value,
        "info": Severity.LOW.value,
    }
    return mapping.get(severity.lower(), Severity.LOW.value)


def _parse_npm_audit_output(stdout: str) -> list[dict]:
    """Parse npm audit JSON output into standardized findings."""
    findings: list[dict] = []
    try:
        data = json.loads(stdout) if stdout.strip() else {}
    except json.JSONDecodeError:
        return findings

    vulnerabilities = data.get("vulnerabilities", {})
    for pkg_name, vuln_info in vulnerabilities.items():
        findings.append({
            "severity": _map_npm_severity(vuln_info.get("severity", "low")),
            "description": vuln_info.get("title", vuln_info.get("name", pkg_name)),
            "file": f"package.json ({pkg_name})",
            "line": 0,
            "rule_id": str(vuln_info.get("via", [{}])[0].get("url", ""))
            if isinstance(vuln_info.get("via", [None])[0], dict)
            else "",
        })
    return findings


def _run_npm_audit_code(path: str) -> dict:
    """Run npm audit for Node JS code security issues.

    Args:
        path: Path to the Node JS project directory.

    Returns:
        A dict with scan findings and metadata.
    """
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True,
            text=True,
            cwd=path,
        )
    except FileNotFoundError:
        return {
            "tool": "npm-audit",
            "status": "error",
            "error": "npm is not installed. Install Node.js and npm first.",
            "findings": [],
        }

    findings = _parse_npm_audit_output(result.stdout)
    return {"tool": "npm-audit", "status": "completed", "findings": findings}


def _map_spotbugs_priority(priority: str) -> str:
    """Map SpotBugs priority to our Severity enum values.

    SpotBugs uses priority 1 (high) to 3+ (low).
    """
    mapping = {"1": Severity.HIGH.value, "2": Severity.MEDIUM.value}
    return mapping.get(str(priority), Severity.LOW.value)


def _run_spotbugs(path: str) -> dict:
    """Run SpotBugs security scan on Java code.

    Args:
        path: Path to the Java project directory.

    Returns:
        A dict with scan findings and metadata.
    """
    pom_path = os.path.join(path, "pom.xml")
    if not os.path.isfile(pom_path):
        return {
            "tool": "spotbugs",
            "status": "error",
            "error": f"No pom.xml found at {pom_path}",
            "findings": [],
        }

    try:
        result = subprocess.run(
            [
                "mvn",
                "com.github.spotbugs:spotbugs-maven-plugin:check",
                "-f",
                pom_path,
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return {
            "tool": "spotbugs",
            "status": "error",
            "error": "mvn (Maven) is not installed. Install Apache Maven first.",
            "findings": [],
        }

    findings: list[dict] = []
    # SpotBugs Maven plugin outputs bug instances in its text output.
    # Parse lines that match the pattern: [ERROR] <description> [<bugType>]
    for line in result.stdout.splitlines() + result.stderr.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # SpotBugs reports bugs in format like:
        # High: <description> At File.java:[line <N>]
        for sev_label in ("High", "Medium", "Low"):
            if stripped.startswith(f"{sev_label}:") or stripped.startswith(f"[{sev_label}]"):
                description = stripped.split(":", 1)[-1].strip() if ":" in stripped else stripped
                file_name = ""
                line_num = 0
                # Try to extract file and line from description
                if " At " in description:
                    parts = description.rsplit(" At ", 1)
                    description = parts[0].strip()
                    loc = parts[1].strip()
                    if ":[line " in loc:
                        file_name = loc.split(":[line ")[0]
                        try:
                            line_num = int(loc.split(":[line ")[1].rstrip("]"))
                        except (ValueError, IndexError):
                            pass
                    else:
                        file_name = loc
                findings.append({
                    "severity": _map_spotbugs_priority(
                        "1" if sev_label == "High" else ("2" if sev_label == "Medium" else "3")
                    ),
                    "description": description,
                    "file": file_name,
                    "line": line_num,
                    "rule_id": "",
                })
                break

    status = "completed" if result.returncode == 0 else "completed_with_findings"
    return {"tool": "spotbugs", "status": status, "findings": findings}


def _run_safety(path: str) -> dict:
    """Run safety to scan Python dependencies for known CVEs.

    Args:
        path: Path to the Python project directory containing requirements.txt.

    Returns:
        A dict with dependency vulnerability findings.
    """
    req_file = os.path.join(path, "requirements.txt")
    if not os.path.isfile(req_file):
        return {
            "tool": "safety",
            "status": "error",
            "error": f"No requirements.txt found at {req_file}",
            "findings": [],
        }

    try:
        result = subprocess.run(
            ["safety", "check", "--json", "-r", req_file],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return {
            "tool": "safety",
            "status": "error",
            "error": "safety is not installed. Install it with: pip install safety",
            "findings": [],
        }

    findings: list[dict] = []
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else []
        # safety JSON output is a list of vulnerability entries.
        # Each entry: [package_name, affected_version, installed_version, description, advisory_id]
        # Newer safety versions may return a dict with a "vulnerabilities" key.
        vuln_list: list = []
        if isinstance(data, list):
            vuln_list = data
        elif isinstance(data, dict):
            vuln_list = data.get("vulnerabilities") or data.get("results") or []

        for vuln in vuln_list:
            if isinstance(vuln, list) and len(vuln) >= 5:
                # Legacy format: [pkg, spec, installed, description, advisory_id]
                findings.append({
                    "severity": Severity.HIGH.value,
                    "description": f"{vuln[0]} ({vuln[2]}): {vuln[3]}",
                    "file": req_file,
                    "line": 0,
                    "rule_id": str(vuln[4]),
                })
            elif isinstance(vuln, dict):
                # Newer dict format
                sev = vuln.get("severity", "high").upper()
                if sev not in {s.value for s in Severity}:
                    sev = Severity.HIGH.value
                findings.append({
                    "severity": sev,
                    "description": vuln.get("advisory", vuln.get("vulnerability_id", "")),
                    "file": req_file,
                    "line": 0,
                    "rule_id": str(vuln.get("vulnerability_id", vuln.get("id", ""))),
                })
    except (json.JSONDecodeError, KeyError, TypeError):
        return {
            "tool": "safety",
            "status": "error",
            "error": f"Failed to parse safety output: {result.stderr or result.stdout}",
            "findings": [],
        }

    return {"tool": "safety", "status": "completed", "findings": findings}


def _run_npm_audit_deps(path: str) -> dict:
    """Run npm audit to scan Node JS dependencies for known CVEs.

    Args:
        path: Path to the Node JS project directory.

    Returns:
        A dict with dependency vulnerability findings.
    """
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True,
            text=True,
            cwd=path,
        )
    except FileNotFoundError:
        return {
            "tool": "npm-audit",
            "status": "error",
            "error": "npm is not installed. Install Node.js and npm first.",
            "findings": [],
        }

    findings = _parse_npm_audit_output(result.stdout)
    return {"tool": "npm-audit", "status": "completed", "findings": findings}


def _run_owasp_dependency_check(path: str) -> dict:
    """Run OWASP dependency-check on Java dependencies.

    Args:
        path: Path to the Java Maven project directory.

    Returns:
        A dict with dependency vulnerability findings.
    """
    pom_path = os.path.join(path, "pom.xml")
    if not os.path.isfile(pom_path):
        return {
            "tool": "owasp-dependency-check",
            "status": "error",
            "error": f"No pom.xml found at {pom_path}",
            "findings": [],
        }

    try:
        result = subprocess.run(
            [
                "mvn",
                "org.owasp:dependency-check-maven:check",
                "-f",
                pom_path,
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return {
            "tool": "owasp-dependency-check",
            "status": "error",
            "error": "mvn (Maven) is not installed. Install Apache Maven first.",
            "findings": [],
        }

    findings: list[dict] = []
    # OWASP dependency-check Maven plugin generates a report file.
    # Try to parse the JSON report if available, otherwise parse text output.
    report_path = os.path.join(path, "target", "dependency-check-report.json")
    if os.path.isfile(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report_data = json.load(f)
            for dep in report_data.get("dependencies", []):
                for vuln in dep.get("vulnerabilities", []):
                    sev_str = vuln.get("severity", "LOW").upper()
                    if sev_str not in {s.value for s in Severity}:
                        sev_str = Severity.LOW.value
                    findings.append({
                        "severity": sev_str,
                        "description": vuln.get("description", vuln.get("name", "")),
                        "file": dep.get("fileName", ""),
                        "line": 0,
                        "rule_id": vuln.get("name", ""),
                    })
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback: parse Maven text output for vulnerability summaries
    if not findings:
        for line in result.stdout.splitlines() + result.stderr.splitlines():
            stripped = line.strip()
            if "CVE-" in stripped:
                findings.append({
                    "severity": Severity.HIGH.value,
                    "description": stripped,
                    "file": pom_path,
                    "line": 0,
                    "rule_id": "",
                })

    status = "completed" if result.returncode == 0 else "completed_with_findings"
    return {"tool": "owasp-dependency-check", "status": status, "findings": findings}


@mcp.tool()
def scan_code(path: str, language: str) -> dict:
    """Run a security scan on source code.

    Executes the appropriate security scanning tool based on the target language:
    - Python: bandit
    - Node JS: npm audit
    - Java: SpotBugs

    Args:
        path: Path to the source directory or file to scan.
        language: Target language — one of "python", "node", or "java".

    Returns:
        A dict containing:
        - scan_id: Unique identifier for this scan (use with get_scan_report).
        - language: The language that was scanned.
        - path: The path that was scanned.
        - timestamp: ISO 8601 timestamp of the scan.
        - summary: High-level summary with finding counts by severity.
        - findings: List of individual security findings, each with severity,
          description, file, and line information.
    """
    lang = language.lower().strip()
    if lang not in SUPPORTED_LANGUAGES:
        return {
            "error": f"Unsupported language: {language}. Supported: {', '.join(SUPPORTED_LANGUAGES)}"
        }

    scan_id = _generate_scan_id()
    timestamp = _now_iso()

    # Dispatch to the appropriate scanner stub
    if lang == "python":
        raw_result = _run_bandit(path)
    elif lang == "node":
        raw_result = _run_npm_audit_code(path)
    elif lang == "java":
        raw_result = _run_spotbugs(path)
    else:
        raw_result = {"tool": "unknown", "status": "error", "findings": []}

    findings = raw_result.get("findings", [])

    # Build severity summary
    severity_counts = {s.value: 0 for s in Severity}
    for finding in findings:
        sev = finding.get("severity", "LOW")
        if sev in severity_counts:
            severity_counts[sev] += 1

    report = {
        "scan_id": scan_id,
        "scan_type": "code",
        "language": lang,
        "path": path,
        "timestamp": timestamp,
        "tool": raw_result.get("tool", "unknown"),
        "summary": {
            "total_findings": len(findings),
            "severity_counts": severity_counts,
        },
        "findings": findings,
    }

    _store_report(scan_id, report)

    return {
        "scan_id": scan_id,
        "language": lang,
        "path": path,
        "timestamp": timestamp,
        "summary": report["summary"],
        "findings": findings,
    }


@mcp.tool()
def scan_dependencies(path: str, language: str) -> dict:
    """Scan project dependencies for known CVEs.

    Executes the appropriate dependency vulnerability scanner based on the target language:
    - Python: safety
    - Node JS: npm audit
    - Java: OWASP dependency-check Maven plugin

    Args:
        path: Path to the project directory containing dependency manifests
              (requirements.txt, package.json, or pom.xml).
        language: Target language — one of "python", "node", or "java".

    Returns:
        A dict containing:
        - scan_id: Unique identifier for this scan (use with get_scan_report).
        - language: The language that was scanned.
        - path: The path that was scanned.
        - timestamp: ISO 8601 timestamp of the scan.
        - summary: High-level summary with vulnerability counts by severity.
        - vulnerabilities: List of dependency vulnerabilities, each with severity,
          package name, installed version, and advisory details.
    """
    lang = language.lower().strip()
    if lang not in SUPPORTED_LANGUAGES:
        return {
            "error": f"Unsupported language: {language}. Supported: {', '.join(SUPPORTED_LANGUAGES)}"
        }

    scan_id = _generate_scan_id()
    timestamp = _now_iso()

    # Dispatch to the appropriate dependency scanner stub
    if lang == "python":
        raw_result = _run_safety(path)
    elif lang == "node":
        raw_result = _run_npm_audit_deps(path)
    elif lang == "java":
        raw_result = _run_owasp_dependency_check(path)
    else:
        raw_result = {"tool": "unknown", "status": "error", "findings": []}

    findings = raw_result.get("findings", [])

    # Build severity summary
    severity_counts = {s.value: 0 for s in Severity}
    for finding in findings:
        sev = finding.get("severity", "LOW")
        if sev in severity_counts:
            severity_counts[sev] += 1

    report = {
        "scan_id": scan_id,
        "scan_type": "dependencies",
        "language": lang,
        "path": path,
        "timestamp": timestamp,
        "tool": raw_result.get("tool", "unknown"),
        "summary": {
            "total_vulnerabilities": len(findings),
            "severity_counts": severity_counts,
        },
        "vulnerabilities": findings,
    }

    _store_report(scan_id, report)

    return {
        "scan_id": scan_id,
        "language": lang,
        "path": path,
        "timestamp": timestamp,
        "summary": report["summary"],
        "vulnerabilities": findings,
    }


@mcp.tool()
def get_scan_report(scan_id: str) -> dict:
    """Retrieve a detailed scan report by scan ID.

    Returns the full scan report for a previously executed scan_code or
    scan_dependencies invocation.

    Args:
        scan_id: The unique scan identifier returned by scan_code or scan_dependencies.

    Returns:
        The full scan report dict if found, or an error dict if the scan_id is unknown.
    """
    report = _scan_reports.get(scan_id)
    if report is None:
        return {"error": f"No scan report found for scan_id: {scan_id}"}
    return report


if __name__ == "__main__":
    mcp.run()
