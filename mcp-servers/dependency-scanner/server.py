"""Dependency Scanner MCP Server.

Identifies outdated dependencies and available updates across Python, Node JS, and Java projects.
Exposes tools for scanning outdated dependencies, checking compatibility between versions,
and generating ordered upgrade plans considering the dependency graph.
Wraps pip-audit/pip list --outdated (Python), npm outdated (Node), mvn versions:display-dependency-updates (Java).
"""

import json
import os
import re
import subprocess
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("dependency-scanner")

SUPPORTED_LANGUAGES = ("python", "node", "java")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _run_pip_outdated(project_path: str) -> list[dict]:
    """Run pip list --outdated for a Python project.

    Args:
        project_path: Path to the Python project directory.

    Returns:
        A list of dicts, each describing an outdated package with keys:
        name, current_version, latest_version, type (major/minor/patch).
    """
    try:
        result = subprocess.run(
            ["pip", "list", "--outdated", "--format=json"],
            capture_output=True,
            text=True,
            cwd=project_path,
        )
    except FileNotFoundError:
        return []

    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    outdated: list[dict] = []
    for entry in data:
        current = entry.get("version", "0.0.0")
        latest = entry.get("latest_version", current)
        outdated.append({
            "name": entry.get("name", ""),
            "current_version": current,
            "latest_version": latest,
            "type": _classify_version_bump(current, latest),
        })
    return outdated


def _run_pip_audit(project_path: str) -> list[dict]:
    """Run pip-audit to find vulnerable Python dependencies.

    Args:
        project_path: Path to the Python project directory containing requirements.txt.

    Returns:
        A list of dicts, each describing a vulnerable package with keys:
        name, installed_version, vulnerability_id, description, fix_version.
    """
    req_file = os.path.join(project_path, "requirements.txt")
    cmd = ["pip-audit", "--format=json"]
    if os.path.isfile(req_file):
        cmd.extend(["-r", req_file])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_path,
        )
    except FileNotFoundError:
        return []

    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    vulnerabilities: list[dict] = []
    # pip-audit JSON output: {"dependencies": [{"name":..., "version":..., "vulns": [...]}]}
    deps = data if isinstance(data, list) else data.get("dependencies", [])
    for dep in deps:
        for vuln in dep.get("vulns", []):
            vulnerabilities.append({
                "name": dep.get("name", ""),
                "installed_version": dep.get("version", ""),
                "vulnerability_id": vuln.get("id", ""),
                "description": vuln.get("description", ""),
                "fix_version": vuln.get("fix_versions", [""])[0] if vuln.get("fix_versions") else "",
            })
    return vulnerabilities


def _run_npm_outdated(project_path: str) -> list[dict]:
    """Run npm outdated for a Node JS project.

    Args:
        project_path: Path to the Node JS project directory containing package.json.

    Returns:
        A list of dicts, each describing an outdated package with keys:
        name, current_version, latest_version, wanted_version, type (major/minor/patch).
    """
    try:
        result = subprocess.run(
            ["npm", "outdated", "--json"],
            capture_output=True,
            text=True,
            cwd=project_path,
        )
    except FileNotFoundError:
        return []

    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    outdated: list[dict] = []
    for pkg_name, info in data.items():
        current = info.get("current", "0.0.0")
        latest = info.get("latest", current)
        wanted = info.get("wanted", current)
        outdated.append({
            "name": pkg_name,
            "current_version": current,
            "latest_version": latest,
            "wanted_version": wanted,
            "type": _classify_version_bump(current, latest),
        })
    return outdated


def _run_mvn_versions(project_path: str) -> list[dict]:
    """Run mvn versions:display-dependency-updates for a Java Maven project.

    Args:
        project_path: Path to the Java project directory containing pom.xml.

    Returns:
        A list of dicts, each describing an outdated dependency with keys:
        group_id, artifact_id, current_version, latest_version, type (major/minor/patch).
    """
    pom_path = os.path.join(project_path, "pom.xml")
    if not os.path.isfile(pom_path):
        return []

    try:
        result = subprocess.run(
            ["mvn", "versions:display-dependency-updates", "-f", pom_path],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []

    outdated: list[dict] = []
    # Parse Maven output lines matching pattern:
    #   [INFO]   groupId:artifactId ... currentVersion -> latestVersion
    pattern = re.compile(
        r"\[INFO\]\s+(\S+):(\S+)\s+.*?(\S+)\s+->\s+(\S+)"
    )
    output = result.stdout + "\n" + result.stderr
    for line in output.splitlines():
        match = pattern.search(line)
        if match:
            group_id, artifact_id, current, latest = match.groups()
            outdated.append({
                "name": f"{group_id}:{artifact_id}",
                "group_id": group_id,
                "artifact_id": artifact_id,
                "current_version": current,
                "latest_version": latest,
                "type": _classify_version_bump(current, latest),
            })
    return outdated


def _classify_version_bump(current: str, latest: str) -> str:
    """Classify a version change as major, minor, or patch.

    Compares two semver-style version strings and returns the bump type.

    Args:
        current: The currently installed version string (e.g. "1.2.3").
        latest: The latest available version string (e.g. "2.0.0").

    Returns:
        One of "major", "minor", or "patch".
    """
    def _parse_semver(version: str) -> tuple[int, int, int]:
        """Extract major.minor.patch integers from a version string."""
        # Strip leading 'v' or 'V' if present
        cleaned = version.lstrip("vV")
        parts = cleaned.split(".")
        nums: list[int] = []
        for part in parts[:3]:
            # Extract leading digits, ignore pre-release suffixes like "-beta"
            digits = re.match(r"(\d+)", part)
            nums.append(int(digits.group(1)) if digits else 0)
        # Pad to 3 elements
        while len(nums) < 3:
            nums.append(0)
        return (nums[0], nums[1], nums[2])

    cur = _parse_semver(current)
    lat = _parse_semver(latest)

    if cur[0] != lat[0]:
        return "major"
    if cur[1] != lat[1]:
        return "minor"
    return "patch"


def _check_breaking_changes(dependency: str, from_version: str, to_version: str) -> dict:
    """Check for breaking changes between two versions of a dependency.

    Uses a heuristic approach: major version bumps are flagged as potentially
    breaking, while minor and patch bumps are considered safe.

    Args:
        dependency: The package/dependency name.
        from_version: The currently installed version.
        to_version: The target upgrade version.

    Returns:
        A dict with keys: has_breaking_changes (bool), details (str),
        migration_notes (str).
    """
    bump = _classify_version_bump(from_version, to_version)

    if bump == "major":
        return {
            "has_breaking_changes": True,
            "details": (
                f"Major version bump for {dependency} ({from_version} -> {to_version}). "
                "Major releases may contain breaking API changes."
            ),
            "migration_notes": (
                f"Review the {dependency} changelog for breaking changes between "
                f"v{from_version} and v{to_version}. Update imports, API calls, "
                "and configuration as needed."
            ),
        }

    return {
        "has_breaking_changes": False,
        "details": (
            f"{bump.capitalize()} version bump for {dependency} "
            f"({from_version} -> {to_version}). No breaking changes expected."
        ),
        "migration_notes": "",
    }


def _build_dependency_graph(project_path: str, language: str) -> dict:
    """Build a dependency graph for the project.

    Runs language-specific tools to discover direct and transitive dependencies:
    - Python: ``pip show`` for each installed package
    - Node: ``npm ls --json``
    - Java: ``mvn dependency:tree``

    Args:
        project_path: Path to the project directory.
        language: Target language — one of "python", "node", or "java".

    Returns:
        A dict representing the dependency graph with keys:
        direct (list of direct dep names), transitive (dict mapping dep name
        to a list of its own dependency names).
    """
    if language == "python":
        return _build_python_dep_graph(project_path)
    if language == "node":
        return _build_node_dep_graph(project_path)
    if language == "java":
        return _build_java_dep_graph(project_path)
    return {"direct": [], "transitive": {}}


def _build_python_dep_graph(project_path: str) -> dict:
    """Build dependency graph for a Python project using pip show."""
    req_file = os.path.join(project_path, "requirements.txt")
    direct: list[str] = []
    if os.path.isfile(req_file):
        with open(req_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (before any version specifier)
                    pkg = re.split(r"[><=!~;]", line)[0].strip()
                    if pkg:
                        direct.append(pkg)

    transitive: dict[str, list[str]] = {}
    for pkg in direct:
        try:
            result = subprocess.run(
                ["pip", "show", pkg],
                capture_output=True,
                text=True,
                cwd=project_path,
            )
        except FileNotFoundError:
            continue
        for out_line in result.stdout.splitlines():
            if out_line.startswith("Requires:"):
                deps_str = out_line.split(":", 1)[1].strip()
                if deps_str:
                    transitive[pkg] = [d.strip() for d in deps_str.split(",") if d.strip()]
                else:
                    transitive[pkg] = []
                break

    return {"direct": direct, "transitive": transitive}


def _build_node_dep_graph(project_path: str) -> dict:
    """Build dependency graph for a Node project using npm ls."""
    try:
        result = subprocess.run(
            ["npm", "ls", "--json", "--depth=1"],
            capture_output=True,
            text=True,
            cwd=project_path,
        )
    except FileNotFoundError:
        return {"direct": [], "transitive": {}}

    if not result.stdout.strip():
        return {"direct": [], "transitive": {}}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"direct": [], "transitive": {}}

    direct: list[str] = []
    transitive: dict[str, list[str]] = {}
    for dep_name, dep_info in data.get("dependencies", {}).items():
        direct.append(dep_name)
        sub_deps = list(dep_info.get("dependencies", {}).keys())
        transitive[dep_name] = sub_deps

    return {"direct": direct, "transitive": transitive}


def _build_java_dep_graph(project_path: str) -> dict:
    """Build dependency graph for a Java Maven project using mvn dependency:tree."""
    pom_path = os.path.join(project_path, "pom.xml")
    if not os.path.isfile(pom_path):
        return {"direct": [], "transitive": {}}

    try:
        result = subprocess.run(
            ["mvn", "dependency:tree", "-f", pom_path],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return {"direct": [], "transitive": {}}

    direct: list[str] = []
    transitive: dict[str, list[str]] = {}
    # Parse mvn dependency:tree output lines like:
    #   [INFO] +- groupId:artifactId:type:version:scope
    #   [INFO] |  \- groupId:artifactId:type:version:scope
    current_direct: str | None = None
    dep_pattern = re.compile(r"\[INFO\]\s+([|\\+\- ]+)(\S+:\S+):\S+:(\S+):\S+")
    for line in result.stdout.splitlines():
        match = dep_pattern.search(line)
        if not match:
            continue
        indent, ga, _version = match.groups()
        depth = indent.count("+") + indent.count("\\")
        if depth <= 1:
            # Direct dependency
            current_direct = ga
            direct.append(ga)
            if ga not in transitive:
                transitive[ga] = []
        elif current_direct:
            # Transitive dependency of current_direct
            transitive[current_direct].append(ga)

    return {"direct": direct, "transitive": transitive}


def _compute_upgrade_order(outdated: list[dict], dep_graph: dict) -> list[dict]:
    """Compute a safe upgrade order considering the dependency graph.

    Performs a topological sort on the dependency graph to determine the
    order in which packages should be upgraded to minimise breakage.
    Leaf dependencies (those with no transitive deps) are upgraded first.

    Args:
        outdated: List of outdated dependency dicts from a scan.
        dep_graph: Dependency graph dict from _build_dependency_graph.

    Returns:
        An ordered list of dicts, each with keys: name, current_version,
        target_version, order (int), reason (str).
    """
    if not outdated:
        return []

    # Build a lookup of outdated packages by name
    outdated_map: dict[str, dict] = {}
    for dep in outdated:
        # Normalise name for lookup (handle groupId:artifactId or plain name)
        outdated_map[dep.get("name", "")] = dep

    transitive = dep_graph.get("transitive", {})

    # Topological sort using Kahn's algorithm on the outdated subset
    outdated_names = set(outdated_map.keys())

    # In-degree: how many outdated packages depend on this outdated package
    in_degree: dict[str, int] = {name: 0 for name in outdated_names}
    for name in outdated_names:
        for child in transitive.get(name, []):
            if child in outdated_names:
                in_degree[child] = in_degree.get(child, 0) + 1

    # Start with leaf nodes (in-degree 0)
    queue = sorted([n for n in outdated_names if in_degree.get(n, 0) == 0])
    ordered_names: list[str] = []

    while queue:
        node = queue.pop(0)
        ordered_names.append(node)
        for child in transitive.get(node, []):
            if child in in_degree:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        queue.sort()

    # Add any remaining (cycle or disconnected) packages
    for name in sorted(outdated_names - set(ordered_names)):
        ordered_names.append(name)

    plan: list[dict] = []
    for idx, name in enumerate(ordered_names):
        dep = outdated_map[name]
        latest = dep.get("latest_version", dep.get("target_version", ""))
        current = dep.get("current_version", "")
        bump = _classify_version_bump(current, latest) if current and latest else "patch"
        reason = "leaf dependency" if not transitive.get(name) else "has transitive deps"
        plan.append({
            "name": name,
            "current_version": current,
            "target_version": latest,
            "order": idx + 1,
            "reason": f"Upgrade order {idx + 1}: {reason} ({bump} bump)",
        })

    return plan


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def scan_outdated(
    project_path: str,
    language: str,
    scope: Optional[str] = None,
) -> dict:
    """Identify outdated dependencies in a project.

    Scans the project's dependency manifest and reports packages that have
    newer versions available. Wraps pip list --outdated / pip-audit (Python),
    npm outdated (Node), mvn versions:display-dependency-updates (Java).

    Args:
        project_path: Path to the project directory containing the dependency
                      manifest (requirements.txt, package.json, or pom.xml).
        language: Target language — one of "python", "node", or "java".
        scope: Optional filter scope — one of "all" (default), "security"
               (only deps with known CVEs), "major", or "minor".

    Returns:
        A dict containing:
        - project_path: The scanned project path.
        - language: The language that was scanned.
        - scope: The filter scope applied.
        - total_outdated: Number of outdated dependencies found.
        - outdated_dependencies: List of outdated dependency details, each with
          name, current_version, latest_version, and type (major/minor/patch).

    **Validates: Requirements 10.1, 10.2**
    """
    lang = language.lower().strip()
    if lang not in SUPPORTED_LANGUAGES:
        return {
            "error": f"Unsupported language: {language}. Supported: {', '.join(SUPPORTED_LANGUAGES)}"
        }

    effective_scope = (scope or "all").lower().strip()

    # Dispatch to the appropriate scanner
    if lang == "python":
        outdated = _run_pip_outdated(project_path)
        if effective_scope == "security":
            outdated = _run_pip_audit(project_path)
    elif lang == "node":
        outdated = _run_npm_outdated(project_path)
    elif lang == "java":
        outdated = _run_mvn_versions(project_path)
    else:
        outdated = []

    # Apply scope filter
    if effective_scope in ("major", "minor", "patch"):
        outdated = [d for d in outdated if d.get("type") == effective_scope]

    return {
        "project_path": project_path,
        "language": lang,
        "scope": effective_scope,
        "total_outdated": len(outdated),
        "outdated_dependencies": outdated,
    }


@mcp.tool()
def check_compatibility(
    dependency: str,
    from_version: str,
    to_version: str,
) -> dict:
    """Check breaking changes between two versions of a dependency.

    Analyses whether upgrading a dependency from one version to another
    introduces breaking changes, and provides migration notes if applicable.

    Args:
        dependency: The package or dependency name (e.g. "requests", "express").
        from_version: The currently installed version (e.g. "2.28.0").
        to_version: The target upgrade version (e.g. "2.31.0").

    Returns:
        A dict containing:
        - dependency: The dependency name.
        - from_version: The source version.
        - to_version: The target version.
        - version_bump: The bump type — "major", "minor", or "patch".
        - has_breaking_changes: Whether breaking changes were detected.
        - details: Description of breaking changes (empty if none).
        - migration_notes: Suggested migration steps (empty if none).

    **Validates: Requirements 10.2**
    """
    bump_type = _classify_version_bump(from_version, to_version)
    compat = _check_breaking_changes(dependency, from_version, to_version)

    return {
        "dependency": dependency,
        "from_version": from_version,
        "to_version": to_version,
        "version_bump": bump_type,
        "has_breaking_changes": compat["has_breaking_changes"],
        "details": compat["details"],
        "migration_notes": compat["migration_notes"],
    }


@mcp.tool()
def get_upgrade_plan(
    project_path: str,
    language: str,
) -> dict:
    """Generate an ordered upgrade plan for outdated dependencies.

    Scans for outdated dependencies, analyses the dependency graph, and
    produces a safe upgrade order that minimises breakage by respecting
    transitive dependency relationships.

    Args:
        project_path: Path to the project directory containing the dependency
                      manifest (requirements.txt, package.json, or pom.xml).
        language: Target language — one of "python", "node", or "java".

    Returns:
        A dict containing:
        - project_path: The scanned project path.
        - language: The language that was scanned.
        - total_upgrades: Number of dependencies to upgrade.
        - upgrade_plan: Ordered list of upgrades, each with name,
          current_version, target_version, order, and reason.

    **Validates: Requirements 10.2, 10.3**
    """
    lang = language.lower().strip()
    if lang not in SUPPORTED_LANGUAGES:
        return {
            "error": f"Unsupported language: {language}. Supported: {', '.join(SUPPORTED_LANGUAGES)}"
        }

    # Scan for outdated dependencies
    if lang == "python":
        outdated = _run_pip_outdated(project_path)
    elif lang == "node":
        outdated = _run_npm_outdated(project_path)
    elif lang == "java":
        outdated = _run_mvn_versions(project_path)
    else:
        outdated = []

    # Build dependency graph and compute safe upgrade order
    dep_graph = _build_dependency_graph(project_path, lang)
    plan = _compute_upgrade_order(outdated, dep_graph)

    return {
        "project_path": project_path,
        "language": lang,
        "total_upgrades": len(plan),
        "upgrade_plan": plan,
    }


if __name__ == "__main__":
    mcp.run()
