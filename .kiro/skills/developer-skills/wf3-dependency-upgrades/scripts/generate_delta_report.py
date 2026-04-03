"""Delta report generator for WF3 Dependency Upgrades workflow.

Compares before/after dependency versions, test results, and breaking changes
to produce a structured JSON report summarizing all upgrade activity.
"""

import json
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class DependencyChange:
    """A single dependency version change."""

    name: str
    old_version: str
    new_version: str
    change_type: str  # "patch", "minor", "major"
    breaking_changes: list[str] = field(default_factory=list)
    code_modifications: list[str] = field(default_factory=list)
    cve_resolved: list[str] = field(default_factory=list)


@dataclass
class TestResults:
    """Test suite results before and after upgrades."""

    tests_run_before: int = 0
    tests_passed_before: int = 0
    tests_failed_before: int = 0
    coverage_before: float = 0.0
    tests_run_after: int = 0
    tests_passed_after: int = 0
    tests_failed_after: int = 0
    coverage_after: float = 0.0


@dataclass
class DeltaReport:
    """Full delta report for a dependency upgrade run."""

    report_id: str
    workflow_id: str
    workflow_run_id: str
    timestamp: str
    project_path: str
    language: str
    scope: str
    summary: str
    restore_point_id: str
    dependency_changes: list[DependencyChange] = field(default_factory=list)
    test_results: TestResults = field(default_factory=TestResults)
    security_issues_before: int = 0
    security_issues_after: int = 0
    overall_passed: bool = True
    failure_reason: str = ""


def classify_version_change(old_version: str, new_version: str) -> str:
    """Classify a version change as patch, minor, or major.

    Uses semantic versioning rules. Falls back to "unknown" if versions
    cannot be parsed.

    Args:
        old_version: The previous version string (e.g., "1.2.3").
        new_version: The new version string (e.g., "2.0.0").

    Returns:
        One of "major", "minor", "patch", or "unknown".
    """
    try:
        old_parts = [int(p) for p in old_version.split(".")[:3]]
        new_parts = [int(p) for p in new_version.split(".")[:3]]
    except (ValueError, AttributeError):
        return "unknown"

    # Pad to 3 parts
    while len(old_parts) < 3:
        old_parts.append(0)
    while len(new_parts) < 3:
        new_parts.append(0)

    if new_parts[0] != old_parts[0]:
        return "major"
    if new_parts[1] != old_parts[1]:
        return "minor"
    if new_parts[2] != old_parts[2]:
        return "patch"
    return "unknown"


def parse_dependency_file(file_path: str) -> dict[str, str]:
    """Parse a dependency file and return a mapping of package name to version.

    Supports requirements.txt (Python), package.json (Node JS), and pom.xml (Java).

    Args:
        file_path: Path to the dependency file.

    Returns:
        Dictionary mapping dependency names to version strings.
    """
    path = Path(file_path)
    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8")
    deps: dict[str, str] = {}

    if path.name == "requirements.txt":
        deps = _parse_requirements_txt(content)
    elif path.name == "package.json":
        deps = _parse_package_json(content)
    elif path.name == "pom.xml":
        deps = _parse_pom_xml(content)

    return deps


def _parse_requirements_txt(content: str) -> dict[str, str]:
    """Parse Python requirements.txt format.

    Args:
        content: File content as string.

    Returns:
        Dictionary mapping package names to version strings.
    """
    deps: dict[str, str] = {}
    for line in content.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        for sep in ["==", ">=", "<=", "~=", "!="]:
            if sep in line:
                name, version = line.split(sep, 1)
                deps[name.strip().lower()] = version.strip()
                break
    return deps


def _parse_package_json(content: str) -> dict[str, str]:
    """Parse Node JS package.json format.

    Args:
        content: File content as string.

    Returns:
        Dictionary mapping package names to version strings.
    """
    deps: dict[str, str] = {}
    try:
        data = json.loads(content)
        for section in ["dependencies", "devDependencies"]:
            if section in data and isinstance(data[section], dict):
                for name, version in data[section].items():
                    # Strip semver prefixes like ^ and ~
                    clean_version = version.lstrip("^~>=<")
                    deps[name] = clean_version
    except (json.JSONDecodeError, KeyError):
        pass
    return deps


def _parse_pom_xml(content: str) -> dict[str, str]:
    """Parse Java pom.xml format (simple regex-based extraction).

    Args:
        content: File content as string.

    Returns:
        Dictionary mapping artifactId to version strings.
    """
    import re

    deps: dict[str, str] = {}
    # Match <dependency> blocks with groupId, artifactId, version
    pattern = re.compile(
        r"<dependency>\s*"
        r"<groupId>([^<]+)</groupId>\s*"
        r"<artifactId>([^<]+)</artifactId>\s*"
        r"<version>([^<]+)</version>",
        re.DOTALL,
    )
    for match in pattern.finditer(content):
        artifact_id = match.group(2).strip()
        version = match.group(3).strip()
        deps[artifact_id] = version
    return deps


def compare_dependencies(
    before_deps: dict[str, str],
    after_deps: dict[str, str],
) -> list[DependencyChange]:
    """Compare before and after dependency maps to identify changes.

    Args:
        before_deps: Dependency versions before upgrade.
        after_deps: Dependency versions after upgrade.

    Returns:
        List of DependencyChange objects for each changed dependency.
    """
    changes: list[DependencyChange] = []

    all_names = sorted(set(before_deps.keys()) | set(after_deps.keys()))
    for name in all_names:
        old_ver = before_deps.get(name, "")
        new_ver = after_deps.get(name, "")

        if old_ver == new_ver:
            continue

        if not old_ver:
            changes.append(DependencyChange(
                name=name,
                old_version="(not present)",
                new_version=new_ver,
                change_type="added",
            ))
        elif not new_ver:
            changes.append(DependencyChange(
                name=name,
                old_version=old_ver,
                new_version="(removed)",
                change_type="removed",
            ))
        else:
            changes.append(DependencyChange(
                name=name,
                old_version=old_ver,
                new_version=new_ver,
                change_type=classify_version_change(old_ver, new_ver),
            ))

    return changes


def generate_delta_report(
    project_path: str,
    language: str,
    scope: str,
    before_deps: dict[str, str],
    after_deps: dict[str, str],
    test_results: TestResults,
    restore_point_id: str,
    workflow_id: str = "wf3-dependency-upgrades",
    workflow_run_id: str = "",
    security_issues_before: int = 0,
    security_issues_after: int = 0,
    breaking_changes_map: dict[str, list[str]] | None = None,
    code_modifications_map: dict[str, list[str]] | None = None,
    cve_map: dict[str, list[str]] | None = None,
) -> DeltaReport:
    """Generate a complete delta report for a dependency upgrade run.

    Args:
        project_path: Path to the project that was upgraded.
        language: Programming language (python, java, nodejs).
        scope: Upgrade scope filter used (all, security, major, minor).
        before_deps: Dependency versions before upgrade.
        after_deps: Dependency versions after upgrade.
        test_results: Test suite results before and after.
        restore_point_id: Git restore point ID for rollback.
        workflow_id: Workflow identifier.
        workflow_run_id: Unique run identifier (generated if empty).
        security_issues_before: Security issues count before upgrade.
        security_issues_after: Security issues count after upgrade.
        breaking_changes_map: Map of dependency name to list of breaking changes.
        code_modifications_map: Map of dependency name to list of code modifications.
        cve_map: Map of dependency name to list of resolved CVE IDs.

    Returns:
        DeltaReport with all upgrade details.
    """
    if not workflow_run_id:
        workflow_run_id = f"run-{uuid.uuid4().hex[:12]}"

    breaking_changes_map = breaking_changes_map or {}
    code_modifications_map = code_modifications_map or {}
    cve_map = cve_map or {}

    changes = compare_dependencies(before_deps, after_deps)

    # Enrich changes with breaking changes, code mods, and CVEs
    for change in changes:
        change.breaking_changes = breaking_changes_map.get(change.name, [])
        change.code_modifications = code_modifications_map.get(change.name, [])
        change.cve_resolved = cve_map.get(change.name, [])

    # Determine overall pass/fail
    tests_passed = test_results.tests_failed_after == 0
    coverage_met = test_results.coverage_after >= 70.0
    no_new_security = security_issues_after <= security_issues_before
    overall_passed = tests_passed and coverage_met and no_new_security

    failure_reasons = []
    if not tests_passed:
        failure_reasons.append(
            f"{test_results.tests_failed_after} test(s) failed after upgrade"
        )
    if not coverage_met:
        failure_reasons.append(
            f"Coverage {test_results.coverage_after:.1f}% below 70% threshold"
        )
    if not no_new_security:
        failure_reasons.append(
            f"New security issues: {security_issues_after - security_issues_before}"
        )

    upgraded_count = sum(
        1 for c in changes if c.change_type in ("patch", "minor", "major")
    )
    summary = (
        f"Upgraded {upgraded_count} dependencies in {project_path} "
        f"(scope: {scope}, language: {language}). "
        f"Tests: {test_results.tests_passed_after}/{test_results.tests_run_after} passed. "
        f"Coverage: {test_results.coverage_before:.1f}% → {test_results.coverage_after:.1f}%. "
        f"Security issues: {security_issues_before} → {security_issues_after}."
    )

    return DeltaReport(
        report_id=f"delta-{uuid.uuid4().hex[:12]}",
        workflow_id=workflow_id,
        workflow_run_id=workflow_run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        project_path=project_path,
        language=language,
        scope=scope,
        summary=summary,
        restore_point_id=restore_point_id,
        dependency_changes=changes,
        test_results=test_results,
        security_issues_before=security_issues_before,
        security_issues_after=security_issues_after,
        overall_passed=overall_passed,
        failure_reason="; ".join(failure_reasons),
    )


def report_to_json(report: DeltaReport) -> str:
    """Serialize a DeltaReport to JSON.

    Args:
        report: The delta report to serialize.

    Returns:
        JSON string representation of the report.
    """
    return json.dumps(asdict(report), indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(
            "Usage: python generate_delta_report.py <project_path> <language> "
            "<before_deps_file> <after_deps_file> [scope] [restore_point_id]"
        )
        print()
        print("Arguments:")
        print("  project_path       Path to the project that was upgraded")
        print("  language           Language: python, java, nodejs")
        print("  before_deps_file   Path to dependency file before upgrade")
        print("  after_deps_file    Path to dependency file after upgrade")
        print("  scope              Upgrade scope: all, security, major, minor (default: all)")
        print("  restore_point_id   Git restore point ID (default: generated)")
        sys.exit(1)

    proj_path = sys.argv[1]
    lang = sys.argv[2]
    before_file = sys.argv[3]
    after_file = sys.argv[4]
    scope_arg = sys.argv[5] if len(sys.argv) > 5 else "all"
    rp_id = sys.argv[6] if len(sys.argv) > 6 else f"rp-{uuid.uuid4().hex[:8]}"

    before = parse_dependency_file(before_file)
    after = parse_dependency_file(after_file)

    results = TestResults()
    report = generate_delta_report(
        project_path=proj_path,
        language=lang,
        scope=scope_arg,
        before_deps=before,
        after_deps=after,
        test_results=results,
        restore_point_id=rp_id,
    )

    print(report_to_json(report))
    sys.exit(0 if report.overall_passed else 1)
