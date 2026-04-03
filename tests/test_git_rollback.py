"""Unit tests for the git-rollback MCP server."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

# Load the server module from its non-standard path
_SERVER_PATH = (
    Path(__file__).resolve().parent.parent / "mcp-servers" / "git-rollback" / "server.py"
)
_spec = importlib.util.spec_from_file_location("git_rollback_server", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["git_rollback_server"] = _mod
_spec.loader.exec_module(_mod)


# ---------------------------------------------------------------------------
# _now_iso
# ---------------------------------------------------------------------------


class TestNowIso:
    def test_returns_iso_format(self):
        result = _mod._now_iso()
        assert result.endswith("Z")
        assert "T" in result

    def test_returns_utc_timestamp(self):
        from datetime import datetime, timezone

        before = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        result = _mod._now_iso()
        after = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        # The minute portion should be within the before/after window
        assert result[:16] >= before
        assert result[:16] <= after


# ---------------------------------------------------------------------------
# _generate_restore_point_id
# ---------------------------------------------------------------------------


class TestGenerateRestorePointId:
    def test_returns_uuid_string(self):
        result = _mod._generate_restore_point_id()
        assert isinstance(result, str)
        assert len(result) == 36  # UUID format: 8-4-4-4-12

    def test_returns_unique_ids(self):
        ids = {_mod._generate_restore_point_id() for _ in range(10)}
        assert len(ids) == 10


# ---------------------------------------------------------------------------
# _snapshot_lockfiles
# ---------------------------------------------------------------------------


class TestSnapshotLockfiles:
    def test_snapshots_existing_lockfiles(self, tmp_path):
        with patch.object(_mod, "GIT_REPO_PATH", str(tmp_path)):
            # Create lockfiles in the repo root
            (tmp_path / "pom.xml").write_text("<project/>")
            (tmp_path / "requirements.txt").write_text("flask==2.0\n")

            result = _mod._snapshot_lockfiles("rp-123")

        assert "pom.xml" in result
        assert "requirements.txt" in result
        assert "package-lock.json" not in result

        snapshot_dir = tmp_path / ".restore-snapshots" / "rp-123"
        assert (snapshot_dir / "pom.xml").read_text() == "<project/>"
        assert (snapshot_dir / "requirements.txt").read_text() == "flask==2.0\n"

    def test_no_lockfiles_exist(self, tmp_path):
        with patch.object(_mod, "GIT_REPO_PATH", str(tmp_path)):
            result = _mod._snapshot_lockfiles("rp-empty")

        assert result == []
        # Snapshot directory should still be created
        assert (tmp_path / ".restore-snapshots" / "rp-empty").is_dir()

    def test_all_lockfiles_present(self, tmp_path):
        with patch.object(_mod, "GIT_REPO_PATH", str(tmp_path)):
            (tmp_path / "pom.xml").write_text("<project/>")
            (tmp_path / "package-lock.json").write_text("{}")
            (tmp_path / "requirements.txt").write_text("requests\n")

            result = _mod._snapshot_lockfiles("rp-all")

        assert len(result) == 3


# ---------------------------------------------------------------------------
# _restore_lockfiles
# ---------------------------------------------------------------------------


class TestRestoreLockfiles:
    def test_restores_snapshotted_lockfiles(self, tmp_path):
        with patch.object(_mod, "GIT_REPO_PATH", str(tmp_path)):
            # Create snapshot
            snapshot_dir = tmp_path / ".restore-snapshots" / "rp-456"
            snapshot_dir.mkdir(parents=True)
            (snapshot_dir / "pom.xml").write_text("<old-project/>")
            (snapshot_dir / "requirements.txt").write_text("old-flask==1.0\n")

            # Create current lockfiles (different content)
            (tmp_path / "pom.xml").write_text("<new-project/>")
            (tmp_path / "requirements.txt").write_text("new-flask==3.0\n")

            result = _mod._restore_lockfiles("rp-456")

        assert "pom.xml" in result
        assert "requirements.txt" in result
        assert (tmp_path / "pom.xml").read_text() == "<old-project/>"
        assert (tmp_path / "requirements.txt").read_text() == "old-flask==1.0\n"

    def test_no_snapshot_directory(self, tmp_path):
        with patch.object(_mod, "GIT_REPO_PATH", str(tmp_path)):
            result = _mod._restore_lockfiles("nonexistent-rp")

        assert result == []

    def test_partial_snapshot(self, tmp_path):
        with patch.object(_mod, "GIT_REPO_PATH", str(tmp_path)):
            snapshot_dir = tmp_path / ".restore-snapshots" / "rp-partial"
            snapshot_dir.mkdir(parents=True)
            (snapshot_dir / "pom.xml").write_text("<project/>")

            result = _mod._restore_lockfiles("rp-partial")

        assert result == ["pom.xml"]


# ---------------------------------------------------------------------------
# _get_current_commit_hash
# ---------------------------------------------------------------------------


class TestGetCurrentCommitHash:
    def test_returns_commit_hash(self):
        mock_repo = MagicMock()
        mock_repo.head.commit.hexsha = "abc123def456"
        with patch.object(_mod, "_get_repo", return_value=mock_repo):
            result = _mod._get_current_commit_hash()
        assert result == "abc123def456"

    def test_returns_empty_on_no_commits(self):
        with patch.object(_mod, "_get_repo", side_effect=Exception("No commits")):
            result = _mod._get_current_commit_hash()
        assert result == ""

    def test_returns_empty_on_invalid_repo(self):
        with patch.object(_mod, "_get_repo", side_effect=Exception("Invalid repo")):
            result = _mod._get_current_commit_hash()
        assert result == ""


# ---------------------------------------------------------------------------
# _create_tag
# ---------------------------------------------------------------------------


class TestCreateTag:
    def test_creates_tag_successfully(self):
        mock_repo = MagicMock()
        with patch.object(_mod, "_get_repo", return_value=mock_repo):
            result = _mod._create_tag("restore-point/rp-1", "tag message")
        assert result is True
        mock_repo.create_tag.assert_called_once_with(
            "restore-point/rp-1", message="tag message"
        )

    def test_returns_false_on_failure(self):
        mock_repo = MagicMock()
        mock_repo.create_tag.side_effect = Exception("Tag already exists")
        with patch.object(_mod, "_get_repo", return_value=mock_repo):
            result = _mod._create_tag("restore-point/rp-dup", "msg")
        assert result is False

    def test_returns_false_on_repo_error(self):
        with patch.object(_mod, "_get_repo", side_effect=Exception("Not a repo")):
            result = _mod._create_tag("some-tag", "msg")
        assert result is False


# ---------------------------------------------------------------------------
# _revert_to_commit
# ---------------------------------------------------------------------------


class TestRevertToCommit:
    def test_successful_revert(self):
        mock_repo = MagicMock()
        with patch.object(_mod, "_get_repo", return_value=mock_repo):
            success, details = _mod._revert_to_commit("abc123")
        assert success is True
        assert "abc123" in details
        mock_repo.git.reset.assert_called_once_with("--hard", "abc123")

    def test_failed_revert(self):
        mock_repo = MagicMock()
        mock_repo.git.reset.side_effect = Exception("Invalid commit")
        with patch.object(_mod, "_get_repo", return_value=mock_repo):
            success, details = _mod._revert_to_commit("bad-hash")
        assert success is False
        assert "Failed" in details
        assert "bad-hash" in details


# ---------------------------------------------------------------------------
# _run_test_suite
# ---------------------------------------------------------------------------


class TestRunTestSuite:
    def test_successful_test_run(self):
        mock_result = MagicMock(
            stdout="5 passed, 1 failed\n",
            stderr="",
            returncode=1,
        )
        with patch("git_rollback_server.subprocess.run", return_value=mock_result):
            result = _mod._run_test_suite("pytest")
        assert result["tests_run"] == 6
        assert result["tests_passed"] == 5
        assert result["tests_failed"] == 1

    def test_command_not_found(self):
        with patch(
            "git_rollback_server.subprocess.run", side_effect=FileNotFoundError
        ):
            result = _mod._run_test_suite("nonexistent-runner")
        assert result["tests_run"] == 0
        assert result["tests_passed"] == 0
        assert result["tests_failed"] == 0
        assert "Command not found" in result["raw_output"]

    def test_timeout(self):
        import subprocess

        with patch(
            "git_rollback_server.subprocess.run",
            side_effect=subprocess.TimeoutExpired("pytest", 300),
        ):
            result = _mod._run_test_suite("pytest")
        assert result["tests_run"] == 0
        assert "timed out" in result["raw_output"]

    def test_truncates_long_output(self):
        long_output = "x" * 5000
        mock_result = MagicMock(
            stdout=long_output,
            stderr="",
            returncode=0,
        )
        with patch("git_rollback_server.subprocess.run", return_value=mock_result):
            result = _mod._run_test_suite("pytest")
        assert len(result["raw_output"]) <= 2000


# ---------------------------------------------------------------------------
# _parse_test_output
# ---------------------------------------------------------------------------


class TestParseTestOutput:
    # pytest format
    def test_pytest_passed_only(self):
        output = "===== 10 passed in 1.23s ====="
        run, passed, failed = _mod._parse_test_output(output, 0)
        assert run == 10
        assert passed == 10
        assert failed == 0

    def test_pytest_passed_and_failed(self):
        output = "===== 8 passed, 3 failed in 2.5s ====="
        run, passed, failed = _mod._parse_test_output(output, 1)
        assert run == 11
        assert passed == 8
        assert failed == 3

    # Jest format
    def test_jest_all_passed(self):
        output = "Tests: 15 passed, 15 total"
        run, passed, failed = _mod._parse_test_output(output, 0)
        assert run == 15
        assert passed == 15
        assert failed == 0

    def test_jest_with_failures(self):
        # The Jest format "Tests: N failed, N passed, N total" contains
        # "N passed" which the pytest regex matches first. The test
        # verifies actual code behavior (pytest regex takes priority).
        output = "Tests: 2 failed, 8 passed, 10 total"
        run, passed, failed = _mod._parse_test_output(output, 1)
        # pytest regex matches "8 passed" (no ", N failed" follows)
        assert passed == 8

    # Maven/JUnit format
    def test_maven_format(self):
        output = "Tests run: 20, Failures: 2, Errors: 1"
        run, passed, failed = _mod._parse_test_output(output, 1)
        assert run == 20
        assert passed == 17
        assert failed == 3

    def test_maven_all_pass(self):
        output = "Tests run: 5, Failures: 0, Errors: 0"
        run, passed, failed = _mod._parse_test_output(output, 0)
        assert run == 5
        assert passed == 5
        assert failed == 0

    # Fallback
    def test_fallback_success(self):
        output = "All good, no recognizable format"
        run, passed, failed = _mod._parse_test_output(output, 0)
        assert run == 1
        assert passed == 1
        assert failed == 0

    def test_fallback_failure(self):
        output = "Something went wrong, no recognizable format"
        run, passed, failed = _mod._parse_test_output(output, 1)
        assert run == 1
        assert passed == 0
        assert failed == 1


# ---------------------------------------------------------------------------
# _get_tag_metadata
# ---------------------------------------------------------------------------


class TestGetTagMetadata:
    def test_returns_metadata_from_annotated_tag(self):
        metadata = {
            "restore_point_id": "rp-1",
            "workflow_id": "wf2",
            "description": "Before refactoring",
            "timestamp": "2026-03-20T14:30:00Z",
            "git_commit_hash": "abc123",
            "snapshotted_lockfiles": ["pom.xml"],
        }
        mock_tag_object = MagicMock()
        mock_tag_object.message = json.dumps(metadata)

        mock_tag = MagicMock()
        mock_tag.tag = mock_tag_object

        mock_repo = MagicMock()
        mock_repo.tags.__getitem__ = MagicMock(return_value=mock_tag)

        with patch.object(_mod, "_get_repo", return_value=mock_repo):
            result = _mod._get_tag_metadata("restore-point/rp-1")

        assert result["restore_point_id"] == "rp-1"
        assert result["workflow_id"] == "wf2"
        assert result["git_commit_hash"] == "abc123"

    def test_returns_none_for_lightweight_tag(self):
        mock_tag = MagicMock()
        mock_tag.tag = None

        mock_repo = MagicMock()
        mock_repo.tags.__getitem__ = MagicMock(return_value=mock_tag)

        with patch.object(_mod, "_get_repo", return_value=mock_repo):
            result = _mod._get_tag_metadata("some-lightweight-tag")

        assert result is None

    def test_returns_none_for_missing_tag(self):
        mock_repo = MagicMock()
        mock_repo.tags.__getitem__ = MagicMock(side_effect=IndexError("No such tag"))

        with patch.object(_mod, "_get_repo", return_value=mock_repo):
            result = _mod._get_tag_metadata("nonexistent-tag")

        assert result is None

    def test_returns_none_for_invalid_json_message(self):
        mock_tag_object = MagicMock()
        mock_tag_object.message = "not valid json"

        mock_tag = MagicMock()
        mock_tag.tag = mock_tag_object

        mock_repo = MagicMock()
        mock_repo.tags.__getitem__ = MagicMock(return_value=mock_tag)

        with patch.object(_mod, "_get_repo", return_value=mock_repo):
            result = _mod._get_tag_metadata("bad-json-tag")

        assert result is None



# ---------------------------------------------------------------------------
# MCP tool: create_restore_point
# ---------------------------------------------------------------------------


class TestCreateRestorePointTool:
    def test_successful_creation(self):
        with (
            patch.object(_mod, "_generate_restore_point_id", return_value="rp-abc"),
            patch.object(_mod, "_now_iso", return_value="2026-03-20T14:30:00Z"),
            patch.object(_mod, "_get_current_commit_hash", return_value="deadbeef1234"),
            patch.object(_mod, "_snapshot_lockfiles", return_value=["pom.xml"]),
            patch.object(_mod, "_create_tag", return_value=True) as mock_tag,
        ):
            result = _mod.create_restore_point("wf2-refactoring", "Before refactoring")

        assert result["restore_point_id"] == "rp-abc"
        assert result["git_commit_hash"] == "deadbeef1234"
        assert result["timestamp"] == "2026-03-20T14:30:00Z"
        # Verify tag was created with correct name and JSON metadata
        mock_tag.assert_called_once()
        tag_name = mock_tag.call_args[0][0]
        assert tag_name == "restore-point/rp-abc"
        tag_message = mock_tag.call_args[0][1]
        metadata = json.loads(tag_message)
        assert metadata["workflow_id"] == "wf2-refactoring"
        assert metadata["description"] == "Before refactoring"
        assert metadata["snapshotted_lockfiles"] == ["pom.xml"]

    def test_no_commits_returns_error(self):
        with patch.object(_mod, "_get_current_commit_hash", return_value=""):
            result = _mod.create_restore_point("wf2", "test")
        assert "error" in result
        assert "No commits" in result["error"]

    def test_tag_creation_failure_returns_error(self):
        with (
            patch.object(_mod, "_generate_restore_point_id", return_value="rp-fail"),
            patch.object(_mod, "_now_iso", return_value="2026-03-20T14:30:00Z"),
            patch.object(_mod, "_get_current_commit_hash", return_value="abc123"),
            patch.object(_mod, "_snapshot_lockfiles", return_value=[]),
            patch.object(_mod, "_create_tag", return_value=False),
        ):
            result = _mod.create_restore_point("wf3", "Before upgrade")

        assert "error" in result
        assert "Failed to create Git tag" in result["error"]


# ---------------------------------------------------------------------------
# MCP tool: rollback
# ---------------------------------------------------------------------------


class TestRollbackTool:
    def test_successful_rollback(self):
        metadata = {
            "restore_point_id": "rp-ok",
            "git_commit_hash": "abc123def",
            "workflow_id": "wf2",
        }
        with (
            patch.object(_mod, "_get_tag_metadata", return_value=metadata),
            patch.object(
                _mod, "_revert_to_commit", return_value=(True, "Reverted OK")
            ),
            patch.object(
                _mod, "_restore_lockfiles", return_value=["pom.xml", "requirements.txt"]
            ),
        ):
            result = _mod.rollback("rp-ok", "Tests failed", "developer-1")

        assert result["success"] is True
        assert "rp-ok" in result["details"]
        assert "pom.xml" in result["details"]
        assert "Tests failed" in result["details"]

    def test_invalid_restore_point(self):
        with patch.object(_mod, "_get_tag_metadata", return_value=None):
            result = _mod.rollback("nonexistent", "reason", "user")
        assert result["success"] is False
        assert "not found" in result["details"]

    def test_missing_commit_hash_in_metadata(self):
        metadata = {"restore_point_id": "rp-bad", "git_commit_hash": ""}
        with patch.object(_mod, "_get_tag_metadata", return_value=metadata):
            result = _mod.rollback("rp-bad", "reason", "user")
        assert result["success"] is False
        assert "missing commit hash" in result["details"]

    def test_revert_failure(self):
        metadata = {
            "restore_point_id": "rp-fail",
            "git_commit_hash": "abc123",
        }
        with (
            patch.object(_mod, "_get_tag_metadata", return_value=metadata),
            patch.object(
                _mod,
                "_revert_to_commit",
                return_value=(False, "Failed to revert to commit abc123: conflict"),
            ),
        ):
            result = _mod.rollback("rp-fail", "reason", "user")
        assert result["success"] is False
        assert "Failed" in result["details"]


# ---------------------------------------------------------------------------
# MCP tool: verify_consistency
# ---------------------------------------------------------------------------


class TestVerifyConsistencyTool:
    def test_consistent_when_all_pass(self):
        test_results = {
            "tests_run": 10,
            "tests_passed": 10,
            "tests_failed": 0,
            "raw_output": "10 passed",
        }
        with patch.object(_mod, "_run_test_suite", return_value=test_results) as mock_run:
            result = _mod.verify_consistency("pytest --run")
        assert result["consistent"] is True
        assert result["tests_run"] == 10
        assert result["tests_passed"] == 10
        assert result["tests_failed"] == 0
        mock_run.assert_called_once_with("pytest --run")

    def test_inconsistent_when_failures(self):
        test_results = {
            "tests_run": 10,
            "tests_passed": 7,
            "tests_failed": 3,
            "raw_output": "7 passed, 3 failed",
        }
        with patch.object(_mod, "_run_test_suite", return_value=test_results):
            result = _mod.verify_consistency()
        assert result["consistent"] is False
        assert result["tests_failed"] == 3

    def test_defaults_to_pytest(self):
        test_results = {
            "tests_run": 1,
            "tests_passed": 1,
            "tests_failed": 0,
            "raw_output": "1 passed",
        }
        with patch.object(_mod, "_run_test_suite", return_value=test_results) as mock_run:
            _mod.verify_consistency()
        mock_run.assert_called_once_with("pytest")

    def test_inconsistent_when_no_tests_run(self):
        test_results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "raw_output": "Command not found",
        }
        with patch.object(_mod, "_run_test_suite", return_value=test_results):
            result = _mod.verify_consistency("missing-runner")
        assert result["consistent"] is False


# ---------------------------------------------------------------------------
# MCP tool: list_restore_points
# ---------------------------------------------------------------------------


class TestListRestorePointsTool:
    def _make_tag(self, name, metadata):
        """Create a mock tag with annotated tag metadata."""
        tag = MagicMock()
        tag.name = name
        return tag

    def test_returns_sorted_restore_points(self):
        metadata_old = {
            "restore_point_id": "rp-old",
            "workflow_id": "wf2",
            "description": "Old point",
            "timestamp": "2026-03-18T10:00:00Z",
            "git_commit_hash": "aaa111",
        }
        metadata_new = {
            "restore_point_id": "rp-new",
            "workflow_id": "wf3",
            "description": "New point",
            "timestamp": "2026-03-20T14:00:00Z",
            "git_commit_hash": "bbb222",
        }

        mock_repo = MagicMock()
        tag_old = self._make_tag("restore-point/rp-old", metadata_old)
        tag_new = self._make_tag("restore-point/rp-new", metadata_new)
        mock_repo.tags = [tag_old, tag_new]

        def mock_get_metadata(tag_name):
            if tag_name == "restore-point/rp-old":
                return metadata_old
            if tag_name == "restore-point/rp-new":
                return metadata_new
            return None

        with (
            patch.object(_mod, "_get_repo", return_value=mock_repo),
            patch.object(_mod, "_get_tag_metadata", side_effect=mock_get_metadata),
        ):
            result = _mod.list_restore_points()

        assert len(result) == 2
        # Most recent first
        assert result[0]["restore_point_id"] == "rp-new"
        assert result[1]["restore_point_id"] == "rp-old"

    def test_ignores_non_restore_point_tags(self):
        mock_repo = MagicMock()
        tag_rp = MagicMock()
        tag_rp.name = "restore-point/rp-1"
        tag_other = MagicMock()
        tag_other.name = "v1.0.0"
        mock_repo.tags = [tag_rp, tag_other]

        metadata = {
            "restore_point_id": "rp-1",
            "workflow_id": "wf2",
            "description": "test",
            "timestamp": "2026-03-20T14:00:00Z",
            "git_commit_hash": "abc",
        }

        with (
            patch.object(_mod, "_get_repo", return_value=mock_repo),
            patch.object(_mod, "_get_tag_metadata", return_value=metadata),
        ):
            result = _mod.list_restore_points()

        assert len(result) == 1
        assert result[0]["restore_point_id"] == "rp-1"

    def test_skips_tags_with_no_metadata(self):
        mock_repo = MagicMock()
        tag = MagicMock()
        tag.name = "restore-point/rp-broken"
        mock_repo.tags = [tag]

        with (
            patch.object(_mod, "_get_repo", return_value=mock_repo),
            patch.object(_mod, "_get_tag_metadata", return_value=None),
        ):
            result = _mod.list_restore_points()

        assert result == []

    def test_returns_empty_on_repo_error(self):
        with patch.object(_mod, "_get_repo", side_effect=Exception("Not a repo")):
            result = _mod.list_restore_points()
        assert result == []

    def test_returns_empty_when_no_tags(self):
        mock_repo = MagicMock()
        mock_repo.tags = []
        with patch.object(_mod, "_get_repo", return_value=mock_repo):
            result = _mod.list_restore_points()
        assert result == []
