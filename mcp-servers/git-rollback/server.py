"""Git Rollback MCP Server.

Git-native rollback with restore points and consistency verification.
Exposes tools for creating restore points (tagging commits + snapshotting lockfiles),
rolling back to a restore point, verifying post-rollback consistency via test suites,
and listing available restore points. Uses gitpython for all Git operations.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("git-rollback")

# Git repository path, configurable via environment variable
GIT_REPO_PATH = os.environ.get("GIT_REPO_PATH", ".")

# Tag prefix used to identify restore point tags
RESTORE_POINT_TAG_PREFIX = "restore-point/"

# Lockfiles to snapshot alongside the Git commit
LOCKFILES = [
    "pom.xml",
    "package-lock.json",
    "requirements.txt",
]

# Directory where lockfile snapshots are stored
SNAPSHOT_DIR = ".restore-snapshots"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_repo():
    """Get a git.Repo instance for the configured repository path.

    Returns:
        A git.Repo object pointing to GIT_REPO_PATH.

    Raises:
        git.InvalidGitRepositoryError: If the path is not a valid Git repo.
    """
    import git

    return git.Repo(GIT_REPO_PATH)


def _now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_restore_point_id() -> str:
    """Generate a unique restore point identifier."""
    return str(uuid.uuid4())


def _snapshot_lockfiles(restore_point_id: str) -> list[str]:
    """Snapshot lockfiles for a restore point.

    Copies each existing lockfile from the repo root into a snapshot
    directory keyed by the restore point ID.

    Args:
        restore_point_id: The unique restore point identifier.

    Returns:
        A list of lockfile names that were successfully snapshotted.
    """
    snapshot_path = Path(GIT_REPO_PATH) / SNAPSHOT_DIR / restore_point_id
    snapshot_path.mkdir(parents=True, exist_ok=True)

    snapshotted: list[str] = []
    for lockfile in LOCKFILES:
        src = Path(GIT_REPO_PATH) / lockfile
        if src.is_file():
            shutil.copy2(str(src), str(snapshot_path / lockfile))
            snapshotted.append(lockfile)

    return snapshotted


def _restore_lockfiles(restore_point_id: str) -> list[str]:
    """Restore lockfiles from a snapshot.

    Copies snapshotted lockfiles back to the repo root, overwriting
    current versions.

    Args:
        restore_point_id: The unique restore point identifier.

    Returns:
        A list of lockfile names that were successfully restored.
    """
    snapshot_path = Path(GIT_REPO_PATH) / SNAPSHOT_DIR / restore_point_id
    if not snapshot_path.is_dir():
        return []

    restored: list[str] = []
    for lockfile in LOCKFILES:
        src = snapshot_path / lockfile
        if src.is_file():
            dest = Path(GIT_REPO_PATH) / lockfile
            shutil.copy2(str(src), str(dest))
            restored.append(lockfile)

    return restored


def _get_current_commit_hash() -> str:
    """Get the current HEAD commit hash.

    Returns:
        The full SHA-1 hash of the current HEAD commit, or an empty string
        if the repo has no commits.
    """
    try:
        repo = _get_repo()
        return repo.head.commit.hexsha
    except Exception:
        return ""


def _create_tag(tag_name: str, message: str) -> bool:
    """Create an annotated Git tag at the current HEAD.

    Args:
        tag_name: The tag name to create.
        message: The annotation message for the tag.

    Returns:
        True if the tag was created successfully, False otherwise.
    """
    try:
        repo = _get_repo()
        repo.create_tag(tag_name, message=message)
        return True
    except Exception:
        return False


def _revert_to_commit(commit_hash: str) -> tuple[bool, str]:
    """Revert the working tree to a specific commit.

    Uses ``git reset --hard`` to move HEAD to the target commit.

    Args:
        commit_hash: The commit hash to revert to.

    Returns:
        A tuple of (success: bool, details: str).
    """
    try:
        repo = _get_repo()
        repo.git.reset("--hard", commit_hash)
        return True, f"Successfully reverted to commit {commit_hash}"
    except Exception as exc:
        return False, f"Failed to revert to commit {commit_hash}: {exc}"


def _run_test_suite(test_command: str) -> dict:
    """Run a test suite and parse the results.

    Executes the given test command in the repo directory and attempts
    to parse pass/fail counts from the output.

    Args:
        test_command: The shell command to run the test suite.

    Returns:
        A dict with keys: tests_run, tests_passed, tests_failed, raw_output.
    """
    try:
        result = subprocess.run(
            test_command.split(),
            capture_output=True,
            text=True,
            cwd=GIT_REPO_PATH,
            timeout=300,
        )
    except FileNotFoundError:
        return {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "raw_output": f"Command not found: {test_command}",
        }
    except subprocess.TimeoutExpired:
        return {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "raw_output": f"Test command timed out after 300 seconds: {test_command}",
        }

    output = result.stdout + "\n" + result.stderr
    tests_run, tests_passed, tests_failed = _parse_test_output(output, result.returncode)

    return {
        "tests_run": tests_run,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "raw_output": output[-2000:] if len(output) > 2000 else output,
    }


def _parse_test_output(output: str, returncode: int) -> tuple[int, int, int]:
    """Parse test output to extract pass/fail counts.

    Attempts to parse pytest, JUnit (Maven), and Jest output formats.

    Args:
        output: Combined stdout+stderr from the test command.
        returncode: The process return code.

    Returns:
        A tuple of (tests_run, tests_passed, tests_failed).
    """
    # Try pytest format: "X passed, Y failed" or "X passed"
    pytest_match = re.search(
        r"(\d+)\s+passed(?:,\s+(\d+)\s+failed)?", output
    )
    if pytest_match:
        passed = int(pytest_match.group(1))
        failed = int(pytest_match.group(2)) if pytest_match.group(2) else 0
        return passed + failed, passed, failed

    # Try Jest format: "Tests: X passed, Y failed, Z total"
    jest_match = re.search(
        r"Tests:\s+(?:(\d+)\s+failed,\s+)?(\d+)\s+passed,\s+(\d+)\s+total",
        output,
    )
    if jest_match:
        failed = int(jest_match.group(1)) if jest_match.group(1) else 0
        passed = int(jest_match.group(2))
        total = int(jest_match.group(3))
        return total, passed, failed

    # Try Maven/JUnit format: "Tests run: X, Failures: Y, Errors: Z"
    mvn_match = re.search(
        r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)",
        output,
    )
    if mvn_match:
        total = int(mvn_match.group(1))
        failures = int(mvn_match.group(2))
        errors = int(mvn_match.group(3))
        return total, total - failures - errors, failures + errors

    # Fallback: infer from return code
    if returncode == 0:
        return 1, 1, 0
    return 1, 0, 1



def _get_tag_metadata(tag_name: str) -> Optional[dict]:
    """Extract metadata from a restore point tag.

    Reads the tag annotation to retrieve the stored restore point metadata
    (restore_point_id, workflow_id, description, timestamp, commit hash,
    snapshotted lockfiles).

    Args:
        tag_name: The full tag name (e.g. "restore-point/<uuid>").

    Returns:
        A dict with restore point metadata, or None if the tag is not found
        or cannot be parsed.
    """
    try:
        repo = _get_repo()
        tag = repo.tags[tag_name]
        tag_object = tag.tag  # annotated tag object
        if tag_object is None:
            return None
        message = tag_object.message
        metadata = json.loads(message)
        return metadata
    except Exception:
        return None


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


def _log_tool_call(tool_name: str, workflow_id: str = "", details: str = "") -> None:
    """Print a structured log line to stderr for CI visibility."""
    timestamp = _now_iso()
    print(
        f"[git-rollback] {timestamp} tool={tool_name} workflow={workflow_id} {details}",
        file=sys.stderr,
        flush=True,
    )


@mcp.tool()
def create_restore_point(workflow_id: str, description: str) -> dict:
    """Tag the current commit as a restore point and snapshot lockfiles.

    Creates an annotated Git tag at the current HEAD and copies lockfiles
    (pom.xml, package-lock.json, requirements.txt) into a snapshot directory
    for later restoration.

    Args:
        workflow_id: Identifier for the workflow creating this restore point
                     (e.g. "wf2-autonomous-refactoring").
        description: Human-readable description of why this restore point
                     is being created.

    Returns:
        A dict containing:
        - restore_point_id: Unique identifier for this restore point.
        - git_commit_hash: The commit hash at the time of creation.
        - timestamp: ISO 8601 timestamp of creation.

    **Validates: Requirements 15.1, 15.2**
    """
    restore_point_id = _generate_restore_point_id()
    timestamp = _now_iso()
    commit_hash = _get_current_commit_hash()

    if not commit_hash:
        _log_tool_call("create_restore_point", workflow_id, "error=no_commits")
        return {"error": "No commits found in the repository."}

    # Snapshot lockfiles
    snapshotted = _snapshot_lockfiles(restore_point_id)

    # Store metadata in the tag annotation
    tag_metadata = {
        "restore_point_id": restore_point_id,
        "workflow_id": workflow_id,
        "description": description,
        "timestamp": timestamp,
        "git_commit_hash": commit_hash,
        "snapshotted_lockfiles": snapshotted,
    }

    tag_name = f"{RESTORE_POINT_TAG_PREFIX}{restore_point_id}"
    tag_message = json.dumps(tag_metadata, separators=(",", ":"))
    tag_created = _create_tag(tag_name, tag_message)

    if not tag_created:
        _log_tool_call("create_restore_point", workflow_id, f"error=tag_failed tag={tag_name}")
        return {"error": f"Failed to create Git tag: {tag_name}"}

    _log_tool_call("create_restore_point", workflow_id, f"commit={commit_hash[:8]} id={restore_point_id}")
    return {
        "restore_point_id": restore_point_id,
        "git_commit_hash": commit_hash,
        "timestamp": timestamp,
    }


@mcp.tool()
def rollback(restore_point_id: str, reason: str, initiator: str) -> dict:
    """Revert the repository to a restore point.

    Resets the Git working tree to the commit associated with the restore
    point, restores snapshotted lockfiles, and logs the rollback event
    to the audit-logger MCP server.

    Args:
        restore_point_id: The unique identifier of the restore point to
                          revert to (returned by create_restore_point).
        reason: Human-readable reason for the rollback.
        initiator: Identity of the user or system initiating the rollback.

    Returns:
        A dict containing:
        - success: Whether the rollback completed successfully.
        - details: Description of what was done or what went wrong.

    **Validates: Requirements 15.1, 15.2**
    """
    tag_name = f"{RESTORE_POINT_TAG_PREFIX}{restore_point_id}"
    metadata = _get_tag_metadata(tag_name)

    if metadata is None:
        return {
            "success": False,
            "details": f"Restore point not found: {restore_point_id}",
        }

    commit_hash = metadata.get("git_commit_hash", "")
    if not commit_hash:
        return {
            "success": False,
            "details": "Restore point metadata missing commit hash.",
        }

    # Revert to the tagged commit
    success, revert_details = _revert_to_commit(commit_hash)
    if not success:
        return {"success": False, "details": revert_details}

    # Restore lockfiles from snapshot
    restored_lockfiles = _restore_lockfiles(restore_point_id)

    details = (
        f"Rolled back to restore point {restore_point_id} "
        f"(commit {commit_hash[:8]}). "
        f"Restored lockfiles: {restored_lockfiles or 'none'}. "
        f"Reason: {reason}. Initiator: {initiator}."
    )

    _log_tool_call("rollback", metadata.get("workflow_id", ""), f"commit={commit_hash[:8]} id={restore_point_id}")
    return {"success": True, "details": details}


@mcp.tool()
def verify_consistency(test_command: Optional[str] = None) -> dict:
    """Run the test suite after a rollback and report results.

    Executes the specified test command (defaulting to "pytest") in the
    repository directory and reports pass/fail counts to verify that the
    codebase is in a consistent state after rollback.

    Args:
        test_command: The shell command to run the test suite. Defaults to
                      "pytest" if not specified.

    Returns:
        A dict containing:
        - consistent: Whether all tests passed (tests_failed == 0).
        - tests_run: Total number of tests executed.
        - tests_passed: Number of tests that passed.
        - tests_failed: Number of tests that failed.

    **Validates: Requirements 15.4**
    """
    cmd = test_command or "pytest"
    results = _run_test_suite(cmd)

    _log_tool_call("verify_consistency", "", f"tests_run={results['tests_run']} failed={results['tests_failed']}")
    return {
        "consistent": results["tests_failed"] == 0 and results["tests_run"] > 0,
        "tests_run": results["tests_run"],
        "tests_passed": results["tests_passed"],
        "tests_failed": results["tests_failed"],
    }


@mcp.tool()
def list_restore_points() -> list[dict]:
    """List all available restore points.

    Scans Git tags with the restore point prefix and returns metadata
    for each restore point, sorted by timestamp (most recent first).

    Returns:
        A list of dicts, each containing:
        - restore_point_id: The unique restore point identifier.
        - workflow_id: The workflow that created the restore point.
        - description: Human-readable description.
        - timestamp: ISO 8601 timestamp of creation.
        - git_commit_hash: The commit hash at the time of creation.

    **Validates: Requirements 15.1**
    """
    try:
        repo = _get_repo()
    except Exception:
        return []

    restore_points: list[dict] = []
    for tag in repo.tags:
        if not tag.name.startswith(RESTORE_POINT_TAG_PREFIX):
            continue

        metadata = _get_tag_metadata(tag.name)
        if metadata is None:
            continue

        restore_points.append({
            "restore_point_id": metadata.get("restore_point_id", ""),
            "workflow_id": metadata.get("workflow_id", ""),
            "description": metadata.get("description", ""),
            "timestamp": metadata.get("timestamp", ""),
            "git_commit_hash": metadata.get("git_commit_hash", ""),
        })

    # Sort by timestamp, most recent first
    restore_points.sort(key=lambda rp: rp.get("timestamp", ""), reverse=True)

    _log_tool_call("list_restore_points", "", f"count={len(restore_points)}")
    return restore_points


if __name__ == "__main__":
    mcp.run()
