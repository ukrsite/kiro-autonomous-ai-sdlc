"""Shared delta report generator for WF2, WF3, and WF5 workflows.

Compares git snapshots (before/after commit hashes), calculates metrics
(files modified, lines added/removed, test counts, coverage), and outputs
a structured JSON delta report matching the DeltaReport schema.

Uses gitpython for git operations.
"""

import argparse
import json
import re
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError


@dataclass
class DeltaChange:
    """A single file change between two git snapshots."""

    file_path: str
    change_type: str  # "added", "modified", "deleted"
    description: str


@dataclass
class DeltaMetrics:
    """Aggregated metrics for the delta report."""

    files_modified: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    tests_added: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    coverage_before: float = 0.0
    coverage_after: float = 0.0


@dataclass
class DeltaReport:
    """Full delta report comparing two git snapshots."""

    report_id: str
    workflow_id: str
    workflow_run_id: str
    timestamp: str
    summary: str
    changes: list[DeltaChange]
    metrics: DeltaMetrics
    before_snapshot: str
    after_snapshot: str



# Pattern matching test function definitions across Python, Java, and JS/TS
_TEST_PATTERNS = [
    re.compile(r"^\+\s*def test_"),           # Python: def test_xxx
    re.compile(r"^\+\s*@Test"),               # Java: @Test annotation
    re.compile(r"^\+\s*(it|test|describe)\("), # JS/TS: it(...), test(...), describe(...)
]


def _count_tests_in_diff(diff_text: str) -> int:
    """Count new test functions/methods added in a unified diff.

    Scans added lines (starting with '+') for common test patterns
    across Python, Java, and JavaScript/TypeScript.

    Args:
        diff_text: Unified diff output as a string.

    Returns:
        Number of new test definitions detected.
    """
    count = 0
    for line in diff_text.splitlines():
        for pattern in _TEST_PATTERNS:
            if pattern.search(line):
                count += 1
                break
    return count


def _parse_test_output(output: str) -> tuple[int, int]:
    """Parse test command output to extract passed/failed counts.

    Supports common output formats from pytest, JUnit (Maven), and Jest.

    Args:
        output: Combined stdout/stderr from the test command.

    Returns:
        Tuple of (tests_passed, tests_failed).
    """
    passed = 0
    failed = 0

    # pytest format: "X passed, Y failed" or "X passed"
    pytest_match = re.search(r"(\d+)\s+passed", output)
    if pytest_match:
        passed = int(pytest_match.group(1))
    pytest_fail = re.search(r"(\d+)\s+failed", output)
    if pytest_fail:
        failed = int(pytest_fail.group(1))
    if pytest_match or pytest_fail:
        return passed, failed

    # Maven/JUnit format: "Tests run: X, Failures: Y, Errors: Z"
    maven_match = re.search(
        r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)", output
    )
    if maven_match:
        total = int(maven_match.group(1))
        failures = int(maven_match.group(2))
        errors = int(maven_match.group(3))
        failed = failures + errors
        passed = total - failed
        return passed, failed

    # Jest format: "Tests: X failed, Y passed, Z total"
    jest_fail = re.search(r"(\d+)\s+failed", output)
    jest_pass = re.search(r"(\d+)\s+passed", output)
    if jest_pass:
        passed = int(jest_pass.group(1))
    if jest_fail:
        failed = int(jest_fail.group(1))

    return passed, failed


def _run_test_command(test_command: str, repo_path: str) -> tuple[int, int]:
    """Execute a test command and parse the results.

    Args:
        test_command: Shell command to run tests (e.g., "pytest --tb=short -q").
        repo_path: Working directory for the command.

    Returns:
        Tuple of (tests_passed, tests_failed).
    """
    try:
        result = subprocess.run(
            test_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=300,
        )
        combined = result.stdout + "\n" + result.stderr
        return _parse_test_output(combined)
    except (subprocess.TimeoutExpired, OSError):
        return 0, 0


def compute_diff_metrics(
    repo: Repo,
    before_commit: str,
    after_commit: str,
) -> tuple[list[DeltaChange], int, int, int]:
    """Compare two commits and compute file-level change metrics.

    Uses gitpython to diff the two commits and extract per-file changes
    including lines added and removed.

    Args:
        repo: A gitpython Repo instance.
        before_commit: The commit hash for the before snapshot.
        after_commit: The commit hash for the after snapshot.

    Returns:
        Tuple of (changes, total_lines_added, total_lines_removed, tests_added).
    """
    commit_before = repo.commit(before_commit)
    commit_after = repo.commit(after_commit)

    diffs = commit_before.diff(commit_after, create_patch=True)

    changes: list[DeltaChange] = []
    total_added = 0
    total_removed = 0
    total_tests_added = 0

    for diff_item in diffs:
        # Determine change type and file path
        if diff_item.new_file:
            change_type = "added"
            file_path = diff_item.b_path or ""
        elif diff_item.deleted_file:
            change_type = "deleted"
            file_path = diff_item.a_path or ""
        else:
            change_type = "modified"
            file_path = diff_item.b_path or diff_item.a_path or ""

        # Parse the patch to count lines added/removed
        lines_added = 0
        lines_removed = 0
        patch_text = ""
        try:
            if diff_item.diff:
                patch_text = (
                    diff_item.diff.decode("utf-8", errors="replace")
                    if isinstance(diff_item.diff, bytes)
                    else diff_item.diff
                )
                for line in patch_text.splitlines():
                    if line.startswith("+") and not line.startswith("+++"):
                        lines_added += 1
                    elif line.startswith("-") and not line.startswith("---"):
                        lines_removed += 1
        except (UnicodeDecodeError, AttributeError):
            pass

        total_added += lines_added
        total_removed += lines_removed

        # Count new test definitions in added lines
        if patch_text:
            total_tests_added += _count_tests_in_diff(patch_text)

        description = f"+{lines_added} -{lines_removed}"
        changes.append(DeltaChange(
            file_path=file_path,
            change_type=change_type,
            description=description,
        ))

    return changes, total_added, total_removed, total_tests_added


def generate_delta_report(
    repo_path: str,
    before_commit: str,
    after_commit: str,
    workflow_id: str,
    workflow_run_id: str = "",
    test_command: str = "",
    coverage_before: float = 0.0,
    coverage_after: float = 0.0,
) -> DeltaReport:
    """Generate a delta report comparing two git snapshots.

    This is the main entry point. It opens the git repo, computes diffs,
    optionally runs tests, and assembles the full DeltaReport.

    Args:
        repo_path: Path to the git repository root.
        before_commit: Git commit hash of the before snapshot.
        after_commit: Git commit hash of the after snapshot.
        workflow_id: Workflow identifier (e.g., "wf2-autonomous-refactoring").
        workflow_run_id: Unique run identifier (auto-generated if empty).
        test_command: Optional command to run tests and collect pass/fail counts.
        coverage_before: Code coverage percentage before changes.
        coverage_after: Code coverage percentage after changes.

    Returns:
        A DeltaReport with all computed metrics and change details.

    Raises:
        InvalidGitRepositoryError: If repo_path is not a valid git repository.
        GitCommandError: If the commit hashes are invalid.
    """
    repo = Repo(repo_path)

    if not workflow_run_id:
        workflow_run_id = f"run-{uuid.uuid4().hex[:12]}"

    changes, lines_added, lines_removed, tests_added = compute_diff_metrics(
        repo, before_commit, after_commit
    )

    # Run tests if a command is provided
    tests_passed = 0
    tests_failed = 0
    if test_command:
        tests_passed, tests_failed = _run_test_command(test_command, repo_path)

    metrics = DeltaMetrics(
        files_modified=len(changes),
        lines_added=lines_added,
        lines_removed=lines_removed,
        tests_added=tests_added,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        coverage_before=coverage_before,
        coverage_after=coverage_after,
    )

    summary = (
        f"Modified {len(changes)} files: "
        f"+{lines_added} lines, -{lines_removed} lines. "
        f"Tests: {tests_passed} passed, {tests_failed} failed."
    )

    return DeltaReport(
        report_id=f"delta-{uuid.uuid4().hex[:12]}",
        workflow_id=workflow_id,
        workflow_run_id=workflow_run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        summary=summary,
        changes=changes,
        metrics=metrics,
        before_snapshot=before_commit,
        after_snapshot=after_commit,
    )


def report_to_dict(report: DeltaReport) -> dict:
    """Convert a DeltaReport to a plain dictionary.

    Args:
        report: The delta report to convert.

    Returns:
        Dictionary representation suitable for JSON serialization.
    """
    return asdict(report)


def report_to_json(report: DeltaReport) -> str:
    """Serialize a DeltaReport to a JSON string.

    Args:
        report: The delta report to serialize.

    Returns:
        Pretty-printed JSON string.
    """
    return json.dumps(report_to_dict(report), indent=2)


def main() -> None:
    """CLI entry point for generating delta reports."""
    parser = argparse.ArgumentParser(
        description="Generate a delta report comparing two git snapshots."
    )
    parser.add_argument(
        "--repo-path",
        required=True,
        help="Path to the git repository root.",
    )
    parser.add_argument(
        "--before-commit",
        required=True,
        help="Git commit hash of the before snapshot.",
    )
    parser.add_argument(
        "--after-commit",
        required=True,
        help="Git commit hash of the after snapshot.",
    )
    parser.add_argument(
        "--workflow-id",
        required=True,
        help="Workflow identifier (e.g., wf2-autonomous-refactoring).",
    )
    parser.add_argument(
        "--workflow-run-id",
        default="",
        help="Unique run identifier (auto-generated if omitted).",
    )
    parser.add_argument(
        "--test-command",
        default="",
        help="Command to run tests and collect pass/fail counts.",
    )
    parser.add_argument(
        "--coverage-before",
        type=float,
        default=0.0,
        help="Code coverage percentage before changes.",
    )
    parser.add_argument(
        "--coverage-after",
        type=float,
        default=0.0,
        help="Code coverage percentage after changes.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output file path for the JSON report (stdout if omitted).",
    )

    args = parser.parse_args()

    try:
        report = generate_delta_report(
            repo_path=args.repo_path,
            before_commit=args.before_commit,
            after_commit=args.after_commit,
            workflow_id=args.workflow_id,
            workflow_run_id=args.workflow_run_id,
            test_command=args.test_command,
            coverage_before=args.coverage_before,
            coverage_after=args.coverage_after,
        )
    except InvalidGitRepositoryError:
        print(f"Error: '{args.repo_path}' is not a valid git repository.", file=sys.stderr)
        sys.exit(1)
    except GitCommandError as exc:
        print(f"Error: Git command failed: {exc}", file=sys.stderr)
        sys.exit(1)

    json_output = report_to_json(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)
            f.write("\n")
        print(f"Delta report written to {args.output}")
    else:
        print(json_output)

    sys.exit(0 if report.metrics.tests_failed == 0 else 1)


if __name__ == "__main__":
    main()
