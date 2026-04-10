"""Unit and integration tests for the FinOps MCP server tools and audit logger client."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_SERVER_PATH = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "finops-cost-estimator" / "server.py"
_spec = importlib.util.spec_from_file_location("finops_server", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["finops_server"] = _mod
_spec.loader.exec_module(_mod)

COST_MODEL_CONTENT = {
    "version": "1.0.0",
    "unit_prices": {
        "llm_tokens_input_per_1k_usd": 0.003,
        "llm_tokens_output_per_1k_usd": 0.015,
        "compute_time_per_second_usd": 0.00005,
        "mcp_tool_invocation_usd": 0.0001,
        "checkpoint_execution_usd": 0.001,
    },
    "defaults": {
        "wf1": {"llm_tokens_input": 50000, "llm_tokens_output": 20000, "compute_time_seconds": 300, "mcp_tool_invocations": 40, "checkpoint_executions": 4},
        "wf2": {"llm_tokens_input": 80000, "llm_tokens_output": 30000, "compute_time_seconds": 600, "mcp_tool_invocations": 60, "checkpoint_executions": 3, "behavior_equivalence_overhead_usd": 0.05},
        "wf3": {"llm_tokens_input": 40000, "llm_tokens_output": 15000, "compute_time_seconds": 240, "mcp_tool_invocations": 50, "checkpoint_executions": 4},
        "wf4": {"llm_tokens_input": 60000, "llm_tokens_output": 25000, "compute_time_seconds": 400, "mcp_tool_invocations": 45, "checkpoint_executions": 5},
        "wf5": {"llm_tokens_input": 30000, "llm_tokens_output": 20000, "compute_time_seconds": 180, "mcp_tool_invocations": 20, "checkpoint_executions": 2},
    },
    "scaling": {
        "wf1_per_file": {"llm_tokens_input": 5000, "llm_tokens_output": 2000, "compute_time_seconds": 30},
        "wf2_per_file": {"llm_tokens_input": 8000, "llm_tokens_output": 3000, "compute_time_seconds": 60},
        "wf3_per_file": {"llm_tokens_input": 3000, "llm_tokens_output": 1000, "compute_time_seconds": 20},
        "wf4_per_file": {"llm_tokens_input": 6000, "llm_tokens_output": 2500, "compute_time_seconds": 40},
        "wf5_per_file": {"llm_tokens_input": 4000, "llm_tokens_output": 3000, "compute_time_seconds": 25},
    },
}


@pytest.fixture(autouse=True)
def reset_cost_model():
    """Reset the module-level cost model cache before each test."""
    _mod._COST_MODEL = None
    yield
    _mod._COST_MODEL = None


@pytest.fixture()
def tmp_env(tmp_path, monkeypatch):
    """Set up isolated file paths for each test."""
    import yaml
    cost_model_path = tmp_path / "finops-cost-model.yml"
    cost_model_path.write_text(__import__("yaml").dump(COST_MODEL_CONTENT))
    baselines_path = tmp_path / "baselines.json"
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    audit_path = tmp_path / "audit.ndjson"

    monkeypatch.setattr(_mod, "COST_MODEL_PATH", str(cost_model_path))
    monkeypatch.setattr(_mod, "BASELINES_PATH", str(baselines_path))
    monkeypatch.setattr(_mod, "REPORTS_DIR", str(reports_dir))
    monkeypatch.setattr(_mod, "AUDIT_LOG_PATH", str(audit_path))

    return {
        "cost_model_path": cost_model_path,
        "baselines_path": baselines_path,
        "reports_dir": reports_dir,
        "audit_path": audit_path,
    }


def _write_audit(audit_path, workflow_id="wf-test"):
    records = [
        {"workflow_id": workflow_id, "type": "event", "timestamp": "2026-01-01T10:00:00Z", "payload": {"event_type": "workflow_start"}},
        {"workflow_id": workflow_id, "type": "event", "timestamp": "2026-01-01T10:05:00Z", "payload": {"event_type": "tool_invocation"}},
        {"workflow_id": workflow_id, "type": "checkpoint", "timestamp": "2026-01-01T10:06:00Z", "payload": {"checkpoint_id": "cp1", "passed": True}},
        {"workflow_id": workflow_id, "type": "interaction", "timestamp": "2026-01-01T10:07:00Z", "payload": {"input_tokens": 1000, "output_tokens": 500, "input_prompt": "x", "ai_output": "y"}},
        {"workflow_id": workflow_id, "type": "event", "timestamp": "2026-01-01T10:10:00Z", "payload": {"event_type": "workflow_end"}},
    ]
    with open(audit_path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


class TestLogFinopsEvent:
    def test_subprocess_called_with_correct_arguments(self, tmp_env):
        with patch("finops_server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            _mod._log_finops_event("cost_estimate_produced", {"workflow_id": "wf-test"})
            assert mock_run.called

    def test_subprocess_failure_does_not_raise(self, tmp_env):
        with patch("finops_server.subprocess.run", side_effect=Exception("connection refused")):
            # Should not raise — best-effort logging
            _mod._log_finops_event("cost_estimate_produced", {"workflow_id": "wf-test"})


class TestEstimateWorkflowCostTool:
    def test_unknown_workflow_type_returns_descriptive_error(self, tmp_env):
        with patch("finops_server._log_finops_event"):
            result = _mod.estimate_workflow_cost("wf99", {})
        assert "error" in result
        assert "wf99" in result["error"]

    def test_valid_wf1_returns_estimate(self, tmp_env):
        with patch("finops_server._log_finops_event"):
            result = _mod.estimate_workflow_cost("wf1", {"files_to_modify": 2})
        assert "error" not in result
        assert "total_estimated_cost_usd" in result

    def test_with_workflow_id_persists_estimate_file(self, tmp_env):
        with patch("finops_server._log_finops_event"):
            _mod.estimate_workflow_cost("wf1", {}, workflow_id="my-run-001")
        est_file = tmp_env["reports_dir"] / "my-run-001_estimate.json"
        assert est_file.exists()


class TestCalculateWorkflowCostTool:
    def test_unknown_workflow_id_returns_descriptive_error(self, tmp_env):
        with patch("finops_server._log_finops_event"):
            result = _mod.calculate_workflow_cost("nonexistent-wf")
        assert "error" in result

    def test_known_workflow_id_returns_actuals(self, tmp_env):
        _write_audit(tmp_env["audit_path"], "wf-test")
        with patch("finops_server._log_finops_event"):
            result = _mod.calculate_workflow_cost("wf-test")
        assert "actuals" in result
        assert "error" not in result


class TestGetCostReportTool:
    def test_unknown_workflow_id_returns_error(self, tmp_env):
        result = _mod.get_cost_report("nonexistent-wf")
        assert "error" in result

    def test_markdown_format_returns_markdown_string(self, tmp_env):
        # Write a report file manually
        report = {
            "workflow_id": "wf-test", "workflow_type": "wf1",
            "generated_at": "2026-01-01T10:00:00Z",
            "estimate": {"dimensions": {d: {"estimated_quantity": 10.0, "unit_price_usd": 0.001, "estimated_cost_usd": 0.01} for d in _mod.DIMENSIONS}, "total_estimated_cost_usd": 0.05, "confidence_level": "low"},
            "actuals": None, "variance": None, "variance_available": False,
            "cost_model_version": "1.0.0",
        }
        report_file = tmp_env["reports_dir"] / "wf-test_20260101T100000Z.json"
        report_file.write_text(json.dumps(report))
        result = _mod.get_cost_report("wf-test", format="markdown")
        assert "content" in result
        assert "Pre-Run Estimate" in result["content"]


class TestGetHistoricalBaselineTool:
    def test_wf1_returns_dict_with_dimension_keys(self, tmp_env):
        # Seed baseline with some data
        baseline = {"wf1": {d: {"count": 1, "mean": 100.0, "p50": 100.0, "p95": 100.0} for d in _mod.DIMENSIONS}, "wf2": {}}
        tmp_env["baselines_path"].write_text(json.dumps(baseline))
        result = _mod.get_historical_baseline("wf1")
        for dim in _mod.DIMENSIONS:
            assert dim in result

    def test_unknown_workflow_type_returns_error(self, tmp_env):
        result = _mod.get_historical_baseline("wf99")
        assert "error" in result
