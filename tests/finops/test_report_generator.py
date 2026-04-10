"""Unit tests for the FinOps report generator."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SERVER_PATH = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "finops-cost-estimator" / "server.py"
_spec = importlib.util.spec_from_file_location("finops_server", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["finops_server"] = _mod
_spec.loader.exec_module(_mod)

DIMS = _mod.DIMENSIONS


def _make_cost_report(with_actuals=False, with_variance=False):
    estimate = {
        "dimensions": {d: {"estimated_quantity": 10.0, "unit_price_usd": 0.001, "estimated_cost_usd": 0.01} for d in DIMS},
        "total_estimated_cost_usd": 0.05,
        "confidence_level": "low",
        "baseline_source": "default",
        "baseline_run_count": 0,
    }
    actuals = {
        "dimensions": {d: {"actual_quantity": 12.0, "unit_price_usd": 0.001, "actual_cost_usd": 0.012} for d in DIMS},
        "total_actual_cost_usd": 0.06,
        "token_count_method": "recorded",
    } if with_actuals else None
    variance = {
        "dimensions": {d: {"estimated_quantity": 10.0, "actual_quantity": 12.0,
                           "estimated_cost_usd": 0.01, "actual_cost_usd": 0.012,
                           "variance_usd": 0.002, "variance_pct": 20.0, "overrun": False} for d in DIMS},
        "total_variance_usd": 0.01,
    } if with_variance else None
    return {
        "workflow_id": "wf-test-123",
        "workflow_type": "wf1",
        "generated_at": "2026-01-01T10:00:00Z",
        "estimate": estimate,
        "actuals": actuals,
        "variance": variance,
        "variance_available": with_actuals and with_variance,
        "cost_model_version": "1.0.0",
    }


class TestPrettyPrintReport:
    def test_pre_run_report_omits_actual_and_variance_columns(self):
        report = _make_cost_report(with_actuals=False)
        md = _mod._pretty_print_report(report)
        assert "Pre-Run Estimate" in md
        assert "Actual Quantity" not in md
        assert "Variance (USD)" not in md

    def test_post_run_report_includes_all_columns(self):
        report = _make_cost_report(with_actuals=True, with_variance=True)
        md = _mod._pretty_print_report(report)
        assert "Post-Run Cost Report" in md
        assert "Estimated Quantity" in md
        assert "Actual Quantity" in md
        assert "Estimated Cost (USD)" in md
        assert "Actual Cost (USD)" in md
        assert "Variance (USD)" in md
        assert "Variance (%)" in md

    def test_returns_valid_markdown_string(self):
        report = _make_cost_report()
        md = _mod._pretty_print_report(report)
        assert isinstance(md, str)
        assert len(md) > 0


class TestGenerateReport:
    def test_files_written_to_correct_paths(self, tmp_path):
        report = _make_cost_report()
        result = _mod._generate_report(report, str(tmp_path))
        assert "error" not in result
        assert Path(result["json_path"]).exists()
        assert Path(result["md_path"]).exists()
        assert "wf-test-123" in result["json_path"]

    def test_json_contains_cost_model_version(self, tmp_path):
        report = _make_cost_report()
        result = _mod._generate_report(report, str(tmp_path))
        data = json.loads(Path(result["json_path"]).read_text())
        assert data["cost_model_version"] == "1.0.0"

    def test_variance_available_false_when_no_actuals(self, tmp_path):
        report = _make_cost_report(with_actuals=False)
        result = _mod._generate_report(report, str(tmp_path))
        data = json.loads(Path(result["json_path"]).read_text())
        assert data["variance_available"] is False

    def test_json_contains_all_required_top_level_fields(self, tmp_path):
        report = _make_cost_report(with_actuals=True, with_variance=True)
        result = _mod._generate_report(report, str(tmp_path))
        data = json.loads(Path(result["json_path"]).read_text())
        for field in ("workflow_id", "workflow_type", "generated_at", "estimate",
                      "actuals", "variance", "variance_available", "cost_model_version"):
            assert field in data
