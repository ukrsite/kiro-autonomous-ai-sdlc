"""Unit tests for the security-scanner MCP server."""

import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load the server module from its non-standard path
_SERVER_PATH = (
    Path(__file__).resolve().parent.parent / "mcp-servers" / "security-scanner" / "server.py"
)
_spec = importlib.util.spec_from_file_location("security_scanner_server", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["security_scanner_server"] = _mod
_spec.loader.exec_module(_mod)


# ---------------------------------------------------------------------------
# Severity mapping helpers
# ---------------------------------------------------------------------------

class TestBanditSeverityMapping:
    def test_high_maps_to_high(self):
        assert _mod._map_bandit_severity("HIGH") == "HIGH"

    def test_medium_maps_to_medium(self):
        assert _mod._map_bandit_severity("MEDIUM") == "MEDIUM"

    def test_low_maps_to_low(self):
        assert _mod._map_bandit_severity("LOW") == "LOW"

    def test_unknown_defaults_to_low(self):
        assert _mod._map_bandit_severity("UNKNOWN") == "LOW"

    def test_case_insensitive(self):
        assert _mod._map_bandit_severity("high") == "HIGH"


class TestBanditConfidenceToSeverity:
    def test_high_severity_high_confidence_is_critical(self):
        assert _mod._map_bandit_confidence_to_severity("HIGH", "HIGH") == "CRITICAL"

    def test_high_severity_low_confidence_stays_high(self):
        assert _mod._map_bandit_confidence_to_severity("HIGH", "LOW") == "HIGH"

    def test_medium_severity_high_confidence_stays_medium(self):
        assert _mod._map_bandit_confidence_to_severity("MEDIUM", "HIGH") == "MEDIUM"


class TestNpmSeverityMapping:
    def test_critical(self):
        assert _mod._map_npm_severity("critical") == "CRITICAL"

    def test_high(self):
        assert _mod._map_npm_severity("high") == "HIGH"

    def test_moderate_maps_to_medium(self):
        assert _mod._map_npm_severity("moderate") == "MEDIUM"

    def test_low(self):
        assert _mod._map_npm_severity("low") == "LOW"

    def test_info_maps_to_low(self):
        assert _mod._map_npm_severity("info") == "LOW"

    def test_unknown_defaults_to_low(self):
        assert _mod._map_npm_severity("weird") == "LOW"


class TestSpotbugsPriorityMapping:
    def test_priority_1_is_high(self):
        assert _mod._map_spotbugs_priority("1") == "HIGH"

    def test_priority_2_is_medium(self):
        assert _mod._map_spotbugs_priority("2") == "MEDIUM"

    def test_priority_3_is_low(self):
        assert _mod._map_spotbugs_priority("3") == "LOW"


# ---------------------------------------------------------------------------
# _run_bandit
# ---------------------------------------------------------------------------

class TestRunBandit:
    def test_tool_not_installed(self):
        with patch("security_scanner_server.subprocess.run", side_effect=FileNotFoundError):
            result = _mod._run_bandit("/some/path")
        assert result["status"] == "error"
        assert "not installed" in result["error"]
        assert result["findings"] == []

    def test_parses_bandit_json_output(self):
        bandit_output = json.dumps({
            "results": [
                {
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "Possible hardcoded password",
                    "filename": "app.py",
                    "line_number": 42,
                    "test_id": "B105",
                },
                {
                    "issue_severity": "MEDIUM",
                    "issue_confidence": "LOW",
                    "issue_text": "Use of assert",
                    "filename": "utils.py",
                    "line_number": 10,
                    "test_id": "B101",
                },
            ]
        })
        mock_result = MagicMock(stdout=bandit_output, stderr="", returncode=1)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_bandit("/some/path")

        assert result["status"] == "completed"
        assert len(result["findings"]) == 2
        assert result["findings"][0]["severity"] == "CRITICAL"  # HIGH+HIGH -> CRITICAL
        assert result["findings"][0]["rule_id"] == "B105"
        assert result["findings"][0]["line"] == 42
        assert result["findings"][1]["severity"] == "MEDIUM"

    def test_empty_output(self):
        mock_result = MagicMock(stdout="", stderr="", returncode=0)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_bandit("/some/path")
        assert result["status"] == "completed"
        assert result["findings"] == []

    def test_invalid_json_output(self):
        mock_result = MagicMock(stdout="not json", stderr="error info", returncode=1)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_bandit("/some/path")
        assert result["status"] == "error"
        assert "Failed to parse" in result["error"]


# ---------------------------------------------------------------------------
# _run_npm_audit_code / _run_npm_audit_deps
# ---------------------------------------------------------------------------

class TestRunNpmAudit:
    def test_npm_not_installed(self):
        with patch("security_scanner_server.subprocess.run", side_effect=FileNotFoundError):
            result = _mod._run_npm_audit_code("/some/path")
        assert result["status"] == "error"
        assert "not installed" in result["error"]

    def test_parses_npm_audit_vulnerabilities(self):
        npm_output = json.dumps({
            "vulnerabilities": {
                "lodash": {
                    "name": "lodash",
                    "severity": "high",
                    "title": "Prototype Pollution",
                    "via": [{"url": "https://example.com/advisory/1"}],
                },
                "express": {
                    "name": "express",
                    "severity": "moderate",
                    "title": "Open Redirect",
                    "via": ["lodash"],
                },
            }
        })
        mock_result = MagicMock(stdout=npm_output, stderr="", returncode=1)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_npm_audit_code("/project")

        assert result["status"] == "completed"
        assert len(result["findings"]) == 2
        severities = {f["severity"] for f in result["findings"]}
        assert "HIGH" in severities
        assert "MEDIUM" in severities

    def test_npm_audit_deps_not_installed(self):
        with patch("security_scanner_server.subprocess.run", side_effect=FileNotFoundError):
            result = _mod._run_npm_audit_deps("/some/path")
        assert result["status"] == "error"

    def test_empty_npm_output(self):
        mock_result = MagicMock(stdout="{}", stderr="", returncode=0)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_npm_audit_code("/project")
        assert result["findings"] == []


# ---------------------------------------------------------------------------
# _run_spotbugs
# ---------------------------------------------------------------------------

class TestRunSpotbugs:
    def test_no_pom_xml(self, tmp_path):
        result = _mod._run_spotbugs(str(tmp_path))
        assert result["status"] == "error"
        assert "No pom.xml" in result["error"]

    def test_maven_not_installed(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        with patch("security_scanner_server.subprocess.run", side_effect=FileNotFoundError):
            result = _mod._run_spotbugs(str(tmp_path))
        assert result["status"] == "error"
        assert "Maven" in result["error"]

    def test_parses_spotbugs_text_output(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        stdout = "High: Null pointer dereference At App.java:[line 15]\nMedium: Unused field At Util.java:[line 30]\n"
        mock_result = MagicMock(stdout=stdout, stderr="", returncode=1)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_spotbugs(str(tmp_path))

        assert len(result["findings"]) == 2
        assert result["findings"][0]["severity"] == "HIGH"
        assert result["findings"][0]["file"] == "App.java"
        assert result["findings"][0]["line"] == 15
        assert result["findings"][1]["severity"] == "MEDIUM"

    def test_clean_run_no_findings(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        mock_result = MagicMock(stdout="BUILD SUCCESS\n", stderr="", returncode=0)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_spotbugs(str(tmp_path))
        assert result["findings"] == []
        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# _run_safety
# ---------------------------------------------------------------------------

class TestRunSafety:
    def test_no_requirements_txt(self, tmp_path):
        result = _mod._run_safety(str(tmp_path))
        assert result["status"] == "error"
        assert "No requirements.txt" in result["error"]

    def test_safety_not_installed(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask==2.0.0\n")
        with patch("security_scanner_server.subprocess.run", side_effect=FileNotFoundError):
            result = _mod._run_safety(str(tmp_path))
        assert result["status"] == "error"
        assert "not installed" in result["error"]

    def test_parses_legacy_list_format(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask==2.0.0\n")
        safety_output = json.dumps([
            ["flask", "<2.3.0", "2.0.0", "XSS vulnerability in flask", "12345"],
        ])
        mock_result = MagicMock(stdout=safety_output, stderr="", returncode=1)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_safety(str(tmp_path))

        assert result["status"] == "completed"
        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "HIGH"
        assert "flask" in result["findings"][0]["description"]
        assert result["findings"][0]["rule_id"] == "12345"

    def test_parses_dict_format_with_vulnerabilities_key(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.25.0\n")
        safety_output = json.dumps({
            "vulnerabilities": [
                {
                    "severity": "MEDIUM",
                    "advisory": "CRLF injection in requests",
                    "vulnerability_id": "CVE-2023-1234",
                },
            ]
        })
        mock_result = MagicMock(stdout=safety_output, stderr="", returncode=1)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_safety(str(tmp_path))

        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "MEDIUM"
        assert result["findings"][0]["rule_id"] == "CVE-2023-1234"

    def test_empty_output(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask==3.0.0\n")
        mock_result = MagicMock(stdout="[]", stderr="", returncode=0)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_safety(str(tmp_path))
        assert result["findings"] == []

    def test_invalid_json_output(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask==2.0.0\n")
        mock_result = MagicMock(stdout="not json", stderr="err", returncode=1)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_safety(str(tmp_path))
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# _run_owasp_dependency_check
# ---------------------------------------------------------------------------

class TestRunOwaspDependencyCheck:
    def test_no_pom_xml(self, tmp_path):
        result = _mod._run_owasp_dependency_check(str(tmp_path))
        assert result["status"] == "error"
        assert "No pom.xml" in result["error"]

    def test_maven_not_installed(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        with patch("security_scanner_server.subprocess.run", side_effect=FileNotFoundError):
            result = _mod._run_owasp_dependency_check(str(tmp_path))
        assert result["status"] == "error"
        assert "Maven" in result["error"]

    def test_parses_json_report_file(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        report = {
            "dependencies": [
                {
                    "fileName": "commons-io-2.6.jar",
                    "vulnerabilities": [
                        {
                            "name": "CVE-2021-29425",
                            "severity": "MEDIUM",
                            "description": "Path traversal in commons-io",
                        }
                    ],
                }
            ]
        }
        (target_dir / "dependency-check-report.json").write_text(json.dumps(report))
        mock_result = MagicMock(stdout="BUILD SUCCESS\n", stderr="", returncode=0)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_owasp_dependency_check(str(tmp_path))

        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "MEDIUM"
        assert result["findings"][0]["rule_id"] == "CVE-2021-29425"

    def test_fallback_to_text_parsing_for_cves(self, tmp_path):
        (tmp_path / "pom.xml").write_text("<project/>")
        stdout = "[WARNING] CVE-2021-29425 found in commons-io\n"
        mock_result = MagicMock(stdout=stdout, stderr="", returncode=1)
        with patch("security_scanner_server.subprocess.run", return_value=mock_result):
            result = _mod._run_owasp_dependency_check(str(tmp_path))

        assert len(result["findings"]) == 1
        assert "CVE-2021-29425" in result["findings"][0]["description"]


# ---------------------------------------------------------------------------
# MCP tool functions: scan_code, scan_dependencies, get_scan_report
# ---------------------------------------------------------------------------

class TestScanCodeTool:
    def test_unsupported_language(self):
        result = _mod.scan_code("/path", "rust")
        assert "error" in result

    def test_returns_structured_result_for_python(self):
        mock_bandit = {"tool": "bandit", "status": "completed", "findings": [
            {"severity": "HIGH", "description": "test", "file": "a.py", "line": 1, "rule_id": "B1"},
        ]}
        with patch.object(_mod, "_run_bandit", return_value=mock_bandit):
            result = _mod.scan_code("/path", "python")

        assert "scan_id" in result
        assert result["language"] == "python"
        assert result["summary"]["total_findings"] == 1
        assert result["summary"]["severity_counts"]["HIGH"] == 1
        assert len(result["findings"]) == 1

    def test_stores_report_for_retrieval(self):
        mock_bandit = {"tool": "bandit", "status": "completed", "findings": []}
        with patch.object(_mod, "_run_bandit", return_value=mock_bandit):
            result = _mod.scan_code("/path", "python")
        report = _mod.get_scan_report(result["scan_id"])
        assert report["scan_type"] == "code"
        assert report["language"] == "python"

    def test_dispatches_to_node(self):
        mock_npm = {"tool": "npm-audit", "status": "completed", "findings": []}
        with patch.object(_mod, "_run_npm_audit_code", return_value=mock_npm):
            result = _mod.scan_code("/path", "node")
        assert result["language"] == "node"

    def test_dispatches_to_java(self):
        mock_sb = {"tool": "spotbugs", "status": "completed", "findings": []}
        with patch.object(_mod, "_run_spotbugs", return_value=mock_sb):
            result = _mod.scan_code("/path", "java")
        assert result["language"] == "java"

    def test_language_is_case_insensitive(self):
        mock_bandit = {"tool": "bandit", "status": "completed", "findings": []}
        with patch.object(_mod, "_run_bandit", return_value=mock_bandit):
            result = _mod.scan_code("/path", "  Python  ")
        assert result["language"] == "python"


class TestScanDependenciesTool:
    def test_unsupported_language(self):
        result = _mod.scan_dependencies("/path", "go")
        assert "error" in result

    def test_returns_structured_result_for_python(self):
        mock_safety = {"tool": "safety", "status": "completed", "findings": [
            {"severity": "HIGH", "description": "vuln", "file": "req.txt", "line": 0, "rule_id": "1"},
        ]}
        with patch.object(_mod, "_run_safety", return_value=mock_safety):
            result = _mod.scan_dependencies("/path", "python")

        assert "scan_id" in result
        assert result["summary"]["total_vulnerabilities"] == 1
        assert len(result["vulnerabilities"]) == 1

    def test_stores_report_for_retrieval(self):
        mock_safety = {"tool": "safety", "status": "completed", "findings": []}
        with patch.object(_mod, "_run_safety", return_value=mock_safety):
            result = _mod.scan_dependencies("/path", "python")
        report = _mod.get_scan_report(result["scan_id"])
        assert report["scan_type"] == "dependencies"


class TestGetScanReport:
    def test_unknown_scan_id(self):
        result = _mod.get_scan_report("nonexistent-id")
        assert "error" in result

    def test_returns_stored_report(self):
        mock_bandit = {"tool": "bandit", "status": "completed", "findings": []}
        with patch.object(_mod, "_run_bandit", return_value=mock_bandit):
            scan_result = _mod.scan_code("/path", "python")
        report = _mod.get_scan_report(scan_result["scan_id"])
        assert report["scan_id"] == scan_result["scan_id"]
        assert "findings" in report
