"""Unit tests for the FinOps cost estimator."""

import importlib.util
import sys
from pathlib import Path

import pytest

_SERVER_PATH = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "finops-cost-estimator" / "server.py"
_spec = importlib.util.spec_from_file_location("finops_server", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["finops_server"] = _mod
_spec.loader.exec_module(_mod)

COST_MODEL = {
    "version": "1.0.0",
    "unit_prices": {
        "llm_tokens_input_per_1k_usd": 0.003,
        "llm_tokens_output_per_1k_usd": 0.015,
        "compute_time_per_second_usd": 0.00005,
        "mcp_tool_invocation_usd": 0.0001,
        "checkpoint_execution_usd": 0.001,
    },
    "defaults": {
        "wf1": {
            "llm_tokens_input": 50000,
            "llm_tokens_output": 20000,
            "compute_time_seconds": 300,
            "mcp_tool_invocations": 40,
            "checkpoint_executions": 4,
        },
        "wf2": {
            "llm_tokens_input": 80000,
            "llm_tokens_output": 30000,
            "compute_time_seconds": 600,
            "mcp_tool_invocations": 60,
            "checkpoint_executions": 3,
            "behavior_equivalence_overhead_usd": 0.05,
        },
        "wf3": {
            "llm_tokens_input": 40000,
            "llm_tokens_output": 15000,
            "compute_time_seconds": 240,
            "mcp_tool_invocations": 50,
            "checkpoint_executions": 4,
        },
        "wf4": {
            "llm_tokens_input": 60000,
            "llm_tokens_output": 25000,
            "compute_time_seconds": 400,
            "mcp_tool_invocations": 45,
            "checkpoint_executions": 5,
        },
        "wf5": {
            "llm_tokens_input": 30000,
            "llm_tokens_output": 20000,
            "compute_time_seconds": 180,
            "mcp_tool_invocations": 20,
            "checkpoint_executions": 2,
        },
    },
    "scaling": {
        "wf1_per_file": {"llm_tokens_input": 5000, "llm_tokens_output": 2000, "compute_time_seconds": 30},
        "wf2_per_file": {"llm_tokens_input": 8000, "llm_tokens_output": 3000, "compute_time_seconds": 60},
        "wf3_per_file": {"llm_tokens_input": 3000, "llm_tokens_output": 1000, "compute_time_seconds": 20},
        "wf4_per_file": {"llm_tokens_input": 6000, "llm_tokens_output": 2500, "compute_time_seconds": 40},
        "wf5_per_file": {"llm_tokens_input": 4000, "llm_tokens_output": 3000, "compute_time_seconds": 25},
    },
}

EMPTY_BASELINE = {"wf1": {}, "wf2": {}, "wf3": {}, "wf4": {}, "wf5": {}}


class TestEstimateCostWF1:
    def test_wf1_with_3_files_produces_expected_total(self):
        result = _mod._estimate_cost("wf1", {"files_to_modify": 3}, COST_MODEL, EMPTY_BASELINE)
        # tokens_input = 50000 + 3*5000 = 65000; cost = 65000 * 0.003/1000 = 0.195
        # tokens_output = 20000 + 3*2000 = 26000; cost = 26000 * 0.015/1000 = 0.39
        # compute = 300 + 3*30 = 390; cost = 390 * 0.00005 = 0.0195
        # mcp = 40; cost = 40 * 0.0001 = 0.004
        # checkpoints = 4; cost = 4 * 0.001 = 0.004
        expected_total = 0.195 + 0.39 + 0.0195 + 0.004 + 0.004
        assert abs(result["total_estimated_cost_usd"] - expected_total) < 1e-9

    def test_zero_historical_runs_uses_default_baseline_source(self):
        result = _mod._estimate_cost("wf1", {}, COST_MODEL, EMPTY_BASELINE)
        assert result["baseline_source"] == "default"
        assert result["confidence_level"] == "low"

    def test_10_historical_runs_uses_historical_baseline_source(self):
        baseline = {"wf1": {}, "wf2": {}}
        actuals = {"dimensions": {dim: {"actual_quantity": 100.0, "unit_price_usd": 0.001, "actual_cost_usd": 0.1} for dim in _mod.DIMENSIONS}}
        for _ in range(10):
            _mod._update_baseline(baseline, "wf1", actuals)
        result = _mod._estimate_cost("wf1", {}, COST_MODEL, baseline)
        assert result["baseline_source"] == "historical"
        assert result["confidence_level"] == "high"

    def test_unknown_workflow_type_raises_error(self):
        with pytest.raises(ValueError, match="Unknown workflow_type"):
            _mod._estimate_cost("wf99", {}, COST_MODEL, EMPTY_BASELINE)


class TestEstimateCostWF2:
    def test_wf2_includes_behavior_equivalence_overhead(self):
        result = _mod._estimate_cost("wf2", {}, COST_MODEL, EMPTY_BASELINE)
        assert "behavior_equivalence_overhead_usd" in result
        assert result["behavior_equivalence_overhead_usd"] == 0.05

    def test_confidence_medium_for_3_to_9_runs(self):
        baseline = {"wf1": {}, "wf2": {}}
        actuals = {"dimensions": {dim: {"actual_quantity": 100.0, "unit_price_usd": 0.001, "actual_cost_usd": 0.1} for dim in _mod.DIMENSIONS}}
        for _ in range(5):
            _mod._update_baseline(baseline, "wf2", actuals)
        result = _mod._estimate_cost("wf2", {}, COST_MODEL, baseline)
        assert result["confidence_level"] == "medium"

    def test_all_five_dimensions_present(self):
        result = _mod._estimate_cost("wf2", {}, COST_MODEL, EMPTY_BASELINE)
        for dim in _mod.DIMENSIONS:
            assert dim in result["dimensions"]
