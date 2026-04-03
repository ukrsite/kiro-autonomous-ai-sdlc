"""Unit tests for the dependency-scanner MCP server."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load the server module from its non-standard path
_SERVER_PATH = (
    Path(__file__).resolve().parent.parent / "mcp-servers" / "dependency-scanner" / "server.py"
)
_spec = importlib.util.spec_from_file_location("dependency_scanner_server", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["dependency_scanner_server"] = _mod
_spec.loader.exec_module(_mod)


# ---------------------------------------------------------------------------
# _classify_version_bump
# ---------------------------------------------------------------------------


class TestClassifyVersionBump:
    def test_major_bump(self):
        assert _mod._classify_version_bump("1.2.3", "2.0.0") == "major"

    def test_minor_bump(self):
        assert _mod._classify_version_bump("1.2.3", "1.3.0") == "minor"

    def test_patch_bump(self):
        assert _mod._classify_version_bump("1.2.3", "1.2.4") == "patch"

    def test_same_version(self):
        assert _mod._classify_version_bump("1.2.3", "1.2.3") == "patch"

    def test_handles_v_prefix(self):
        assert _mod._classify_version_bump("v1.0.0", "v2.0.0") == "major"

    def test_handles_two_part_version(self):
        assert _mod._classify_version_bump("1.2", "2.0") == "major"

    def test_handles_prerelease_suffix(self):
        assert _mod._classify_version_bump("1.2.3-beta", "2.0.0-rc1") == "major"


# ---------------------------------------------------------------------------
# _check_breaking_changes
# ---------------------------------------------------------------------------


class TestCheckBreakingChanges:
    def test_major_bump_flags_breaking(self):
        result = _mod._check_breaking_changes("requests", "1.0.0", "2.0.0")
        assert result["has_breaking_changes"] is True
        assert "requests" in result["details"]
        assert result["migration_notes"] != ""

    def test_minor_bump_no_breaking(self):
        result = _mod._check_breaking_changes("requests", "1.0.0", "1.1.0")
        assert result["has_breaking_changes"] is False
        assert result["migration_notes"] == ""

    def test_patch_bump_no_breaking(self):
        result = _mod._check_breaking_changes("flask", "2.0.0", "2.0.1")
        assert result["has_breaking_changes"] is False


# ---------------------------------------------------------------------------
# _run_pip_outdated
# ---------------------------------------------------------------------------


class TestRunPipOutdated:
    def test_pip_not_installed(self):
        with patch("dependency_scanner_server.subprocess.run", side_effect=FileNotFoundError):
            result = _mod._run_pip_outdated("/some/path")
        assert result == []

    def test_parses_json_output(self):
        pip_output = json.dumps([
            {"name": "requests", "version": "2.25.0", "latest_version": "2.31.0", "latest_filetype": "wheel"},
            {"name": "flask", "version": "2.0.0", "latest_version": "3.0.0", "latest_filetype": "wheel"},
        ])
        mock_result = MagicMock(stdout=pip_output, stderr="", returncode=0)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_pip_outdated("/project")

        assert len(result) == 2
        assert result[0]["name"] == "requests"
        assert result[0]["current_version"] == "2.25.0"
        assert result[0]["latest_version"] == "2.31.0"
        assert result[0]["type"] == "minor"
        assert result[1]["type"] == "major"

    def test_empty_output(self):
        mock_result = MagicMock(stdout="", stderr="", returncode=0)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_pip_outdated("/project")
        assert result == []

    def test_invalid_json(self):
        mock_result = MagicMock(stdout="not json", stderr="", returncode=1)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_pip_outdated("/project")
        assert result == []


# ---------------------------------------------------------------------------
# _run_pip_audit
# ---------------------------------------------------------------------------


class TestRunPipAudit:
    def test_pip_audit_not_installed(self):
        with patch("dependency_scanner_server.subprocess.run", side_effect=FileNotFoundError):
            result = _mod._run_pip_audit("/some/path")
        assert result == []

    def test_parses_dependencies_format(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask==2.0.0\n")
        audit_output = json.dumps({
            "dependencies": [
                {
                    "name": "flask",
                    "version": "2.0.0",
                    "vulns": [
                        {
                            "id": "PYSEC-2023-001",
                            "description": "XSS vulnerability",
                            "fix_versions": ["2.3.0"],
                        }
                    ],
                }
            ]
        })
        mock_result = MagicMock(stdout=audit_output, stderr="", returncode=1)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_pip_audit(str(tmp_path))

        assert len(result) == 1
        assert result[0]["name"] == "flask"
        assert result[0]["vulnerability_id"] == "PYSEC-2023-001"
        assert result[0]["fix_version"] == "2.3.0"

    def test_empty_output(self):
        mock_result = MagicMock(stdout="", stderr="", returncode=0)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_pip_audit("/project")
        assert result == []

    def test_invalid_json(self):
        mock_result = MagicMock(stdout="not json", stderr="", returncode=1)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_pip_audit("/project")
        assert result == []


# ---------------------------------------------------------------------------
# _run_npm_outdated
# ---------------------------------------------------------------------------


class TestRunNpmOutdated:
    def test_npm_not_installed(self):
        with patch("dependency_scanner_server.subprocess.run", side_effect=FileNotFoundError):
            result = _mod._run_npm_outdated("/some/path")
        assert result == []

    def test_parses_json_output(self):
        npm_output = json.dumps({
            "express": {"current": "4.17.0", "wanted": "4.18.2", "latest": "5.0.0"},
            "lodash": {"current": "4.17.20", "wanted": "4.17.21", "latest": "4.17.21"},
        })
        mock_result = MagicMock(stdout=npm_output, stderr="", returncode=1)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_npm_outdated("/project")

        assert len(result) == 2
        names = {r["name"] for r in result}
        assert "express" in names
        assert "lodash" in names
        express = next(r for r in result if r["name"] == "express")
        assert express["current_version"] == "4.17.0"
        assert express["latest_version"] == "5.0.0"
        assert express["wanted_version"] == "4.18.2"
        assert express["type"] == "major"

    def test_empty_output(self):
        mock_result = MagicMock(stdout="", stderr="", returncode=0)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_npm_outdated("/project")
        assert result == []

    def test_invalid_json(self):
        mock_result = MagicMock(stdout="not json", stderr="", returncode=1)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_npm_outdated("/project")
        assert result == []


# ---------------------------------------------------------------------------
# _run_mvn_versions
# ---------------------------------------------------------------------------


class TestRunMvnVersions:
    def test_no_pom_xml(self, tmp_path):
        result = _mod._run_mvn_versions(str(tmp_path))
        assert result == []

    def test_maven_not_installed(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        with patch("dependency_scanner_server.subprocess.run", side_effect=FileNotFoundError):
            result = _mod._run_mvn_versions(str(tmp_path))
        assert result == []

    def test_parses_maven_output(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        mvn_output = (
            "[INFO] The following dependencies have newer versions:\n"
            "[INFO]   org.apache.commons:commons-lang3 ... 3.12.0 -> 3.14.0\n"
            "[INFO]   com.google.guava:guava .............. 31.0-jre -> 33.0.0-jre\n"
        )
        mock_result = MagicMock(stdout=mvn_output, stderr="", returncode=0)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_mvn_versions(str(tmp_path))

        assert len(result) == 2
        assert result[0]["group_id"] == "org.apache.commons"
        assert result[0]["artifact_id"] == "commons-lang3"
        assert result[0]["current_version"] == "3.12.0"
        assert result[0]["latest_version"] == "3.14.0"
        assert result[0]["type"] == "minor"

    def test_empty_output(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        mock_result = MagicMock(stdout="[INFO] BUILD SUCCESS\n", stderr="", returncode=0)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_mvn_versions(str(tmp_path))
        assert result == []


# ---------------------------------------------------------------------------
# _build_dependency_graph
# ---------------------------------------------------------------------------


class TestBuildDependencyGraph:
    def test_python_reads_requirements_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests>=2.25\nflask\n")
        pip_show_requests = "Name: requests\nVersion: 2.25.0\nRequires: urllib3, certifi\n"
        pip_show_flask = "Name: flask\nVersion: 2.0.0\nRequires: werkzeug, jinja2\n"

        def mock_run(cmd, **kwargs):
            pkg = cmd[-1]
            if pkg == "requests":
                return MagicMock(stdout=pip_show_requests, stderr="", returncode=0)
            if pkg == "flask":
                return MagicMock(stdout=pip_show_flask, stderr="", returncode=0)
            return MagicMock(stdout="", stderr="", returncode=1)

        with patch("dependency_scanner_server.subprocess.run", side_effect=mock_run):
            result = _mod._build_dependency_graph(str(tmp_path), "python")

        assert "requests" in result["direct"]
        assert "flask" in result["direct"]
        assert "urllib3" in result["transitive"]["requests"]
        assert "certifi" in result["transitive"]["requests"]

    def test_python_no_requirements_file(self, tmp_path):
        result = _mod._build_dependency_graph(str(tmp_path), "python")
        assert result["direct"] == []

    def test_node_parses_npm_ls(self):
        npm_ls_output = json.dumps({
            "dependencies": {
                "express": {
                    "version": "4.18.2",
                    "dependencies": {
                        "body-parser": {"version": "1.20.0"},
                    },
                },
                "lodash": {"version": "4.17.21"},
            }
        })
        mock_result = MagicMock(stdout=npm_ls_output, stderr="", returncode=0)
        with patch("dependency_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._build_dependency_graph("/project", "node")

        assert "express" in result["direct"]
        assert "lodash" in result["direct"]
        assert "body-parser" in result["transitive"]["express"]
        assert result["transitive"]["lodash"] == []

    def test_node_npm_not_installed(self):
        with patch("dependency_scanner_server.subprocess.run", side_effect=FileNotFoundError):
            result = _mod._build_dependency_graph("/project", "node")
        assert result == {"direct": [], "transitive": {}}

    def test_java_no_pom(self, tmp_path):
        result = _mod._build_dependency_graph(str(tmp_path), "java")
        assert result == {"direct": [], "transitive": {}}

    def test_unsupported_language(self):
        result = _mod._build_dependency_graph("/project", "rust")
        assert result == {"direct": [], "transitive": {}}


# ---------------------------------------------------------------------------
# _compute_upgrade_order
# ---------------------------------------------------------------------------


class TestComputeUpgradeOrder:
    def test_empty_outdated(self):
        result = _mod._compute_upgrade_order([], {"direct": [], "transitive": {}})
        assert result == []

    def test_single_dependency(self):
        outdated = [{"name": "requests", "current_version": "2.25.0", "latest_version": "2.31.0"}]
        dep_graph = {"direct": ["requests"], "transitive": {"requests": []}}
        result = _mod._compute_upgrade_order(outdated, dep_graph)
        assert len(result) == 1
        assert result[0]["name"] == "requests"
        assert result[0]["order"] == 1

    def test_leaf_deps_upgraded_first(self):
        outdated = [
            {"name": "flask", "current_version": "2.0.0", "latest_version": "3.0.0"},
            {"name": "werkzeug", "current_version": "2.0.0", "latest_version": "3.0.0"},
        ]
        dep_graph = {
            "direct": ["flask", "werkzeug"],
            "transitive": {"flask": ["werkzeug"], "werkzeug": []},
        }
        result = _mod._compute_upgrade_order(outdated, dep_graph)
        assert len(result) == 2
        names_in_order = [r["name"] for r in result]
        # flask depends on werkzeug, but werkzeug is a leaf so it should come first
        # in topological order (flask has in-degree 0, werkzeug has in-degree 1 from flask)
        # Actually: flask -> werkzeug means werkzeug is a child of flask.
        # In Kahn's: in_degree of werkzeug = 1 (flask depends on it), flask = 0
        # So flask is processed first, then werkzeug
        assert names_in_order[0] == "flask"
        assert names_in_order[1] == "werkzeug"

    def test_all_entries_have_required_keys(self):
        outdated = [
            {"name": "pkg-a", "current_version": "1.0.0", "latest_version": "2.0.0"},
            {"name": "pkg-b", "current_version": "1.0.0", "latest_version": "1.1.0"},
        ]
        dep_graph = {"direct": ["pkg-a", "pkg-b"], "transitive": {}}
        result = _mod._compute_upgrade_order(outdated, dep_graph)
        for entry in result:
            assert "name" in entry
            assert "current_version" in entry
            assert "target_version" in entry
            assert "order" in entry
            assert "reason" in entry


# ---------------------------------------------------------------------------
# MCP tool: scan_outdated
# ---------------------------------------------------------------------------


class TestScanOutdatedTool:
    def test_unsupported_language(self):
        result = _mod.scan_outdated("/path", "rust")
        assert "error" in result

    def test_python_dispatches_to_pip_outdated(self):
        mock_outdated = [
            {"name": "requests", "current_version": "2.25.0", "latest_version": "2.31.0", "type": "minor"},
        ]
        with patch.object(_mod, "_run_pip_outdated", return_value=mock_outdated):
            result = _mod.scan_outdated("/path", "python")

        assert result["language"] == "python"
        assert result["total_outdated"] == 1
        assert result["outdated_dependencies"][0]["name"] == "requests"

    def test_python_security_scope_uses_pip_audit(self):
        mock_audit = [
            {"name": "flask", "installed_version": "2.0.0", "vulnerability_id": "CVE-1", "type": "major"},
        ]
        with patch.object(_mod, "_run_pip_outdated", return_value=[]):
            with patch.object(_mod, "_run_pip_audit", return_value=mock_audit):
                result = _mod.scan_outdated("/path", "python", scope="security")

        assert result["scope"] == "security"
        assert result["total_outdated"] == 1

    def test_scope_filter_major(self):
        mock_outdated = [
            {"name": "a", "current_version": "1.0.0", "latest_version": "2.0.0", "type": "major"},
            {"name": "b", "current_version": "1.0.0", "latest_version": "1.1.0", "type": "minor"},
        ]
        with patch.object(_mod, "_run_pip_outdated", return_value=mock_outdated):
            result = _mod.scan_outdated("/path", "python", scope="major")

        assert result["total_outdated"] == 1
        assert result["outdated_dependencies"][0]["name"] == "a"

    def test_node_dispatches_to_npm_outdated(self):
        mock_outdated = [
            {"name": "express", "current_version": "4.17.0", "latest_version": "5.0.0", "type": "major"},
        ]
        with patch.object(_mod, "_run_npm_outdated", return_value=mock_outdated):
            result = _mod.scan_outdated("/path", "node")

        assert result["language"] == "node"
        assert result["total_outdated"] == 1

    def test_java_dispatches_to_mvn_versions(self):
        mock_outdated = [
            {"name": "g:a", "current_version": "1.0", "latest_version": "2.0", "type": "major"},
        ]
        with patch.object(_mod, "_run_mvn_versions", return_value=mock_outdated):
            result = _mod.scan_outdated("/path", "java")

        assert result["language"] == "java"
        assert result["total_outdated"] == 1

    def test_language_is_case_insensitive(self):
        with patch.object(_mod, "_run_pip_outdated", return_value=[]):
            result = _mod.scan_outdated("/path", "  Python  ")
        assert result["language"] == "python"


# ---------------------------------------------------------------------------
# MCP tool: check_compatibility
# ---------------------------------------------------------------------------


class TestCheckCompatibilityTool:
    def test_returns_structured_result(self):
        result = _mod.check_compatibility("requests", "1.0.0", "2.0.0")
        assert result["dependency"] == "requests"
        assert result["from_version"] == "1.0.0"
        assert result["to_version"] == "2.0.0"
        assert result["version_bump"] == "major"
        assert result["has_breaking_changes"] is True
        assert "details" in result
        assert "migration_notes" in result

    def test_minor_bump_no_breaking(self):
        result = _mod.check_compatibility("flask", "2.0.0", "2.1.0")
        assert result["version_bump"] == "minor"
        assert result["has_breaking_changes"] is False

    def test_patch_bump_no_breaking(self):
        result = _mod.check_compatibility("lodash", "4.17.20", "4.17.21")
        assert result["version_bump"] == "patch"
        assert result["has_breaking_changes"] is False


# ---------------------------------------------------------------------------
# MCP tool: get_upgrade_plan
# ---------------------------------------------------------------------------


class TestGetUpgradePlanTool:
    def test_unsupported_language(self):
        result = _mod.get_upgrade_plan("/path", "go")
        assert "error" in result

    def test_returns_structured_plan(self):
        mock_outdated = [
            {"name": "requests", "current_version": "2.25.0", "latest_version": "2.31.0"},
        ]
        mock_graph = {"direct": ["requests"], "transitive": {"requests": []}}
        with patch.object(_mod, "_run_pip_outdated", return_value=mock_outdated):
            with patch.object(_mod, "_build_dependency_graph", return_value=mock_graph):
                result = _mod.get_upgrade_plan("/path", "python")

        assert result["language"] == "python"
        assert result["total_upgrades"] == 1
        assert result["upgrade_plan"][0]["name"] == "requests"
        assert result["upgrade_plan"][0]["order"] == 1

    def test_empty_when_no_outdated(self):
        with patch.object(_mod, "_run_pip_outdated", return_value=[]):
            with patch.object(_mod, "_build_dependency_graph", return_value={"direct": [], "transitive": {}}):
                result = _mod.get_upgrade_plan("/path", "python")

        assert result["total_upgrades"] == 0
        assert result["upgrade_plan"] == []

    def test_language_is_case_insensitive(self):
        with patch.object(_mod, "_run_npm_outdated", return_value=[]):
            with patch.object(_mod, "_build_dependency_graph", return_value={"direct": [], "transitive": {}}):
                result = _mod.get_upgrade_plan("/path", "  Node  ")
        assert result["language"] == "node"
