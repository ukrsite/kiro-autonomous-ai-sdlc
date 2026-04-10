"""Unit tests for the FinOps variance calculator."""

import importlib.util
import sys
from pathlib import Path

import pytest

_SERVER_PATH = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "finops-cost-estimator" / "server.py"
_spec = importlib.util.spec_from_file_location("finops_server", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["finops_server"] = _mod
_spec.loader.exec_module(_mod)

DIMS = _mod.DIMENSIONS


def _make_estimate(costs: dict) -> dict:
    return {
        "workflow_id": "wf-test",
        "dimensions": {
            dim: {"estimated_quantity": costs.get(dim, 10.0), "unit_price_usd": 0.001,
                  "estimated_cost_usd": costs.get(dim, 10.0)}
            for dim in DIMS
        },
        "total_estimated_cost_usd": sum(costs.get(d, 10.0) for d in DIMS),
    }


def _make_actuals(costs: dict) -> dict:
    return {
        "workflow_id": "wf-test",
        "dimensions": {
            dim: {"actual_quantity": costs.get(dim, 10.0), "unit_price_usd": 0.001,
                  "actual_cost_usd": costs.get(dim, 10.0)}
            for dim in DIMS
        },
        "total_actual_cost_usd": sum(costs.get(d, 10.0) for d in DIMS),
    }


class TestCalculateVariance:
    def test_equal_estimate_and_actuals_produces_zero_variance(self):
        est = _make_estimate({d: 10.0 for d in DIMS})
        act = _make_actuals({d: 10.0 for d in DIMS})
        result = _mod._calculate_variance(est, act)
        for dim in DIMS:
            assert result["dimensions"][dim]["variance_usd"] == 0.0
            assert result["dimensions"][dim]["overrun"] is False
        assert result["total_variance_usd"] == 0.0

    def test_25_percent_over_flags_overrun_true(self):
        est = _make_estimate({"llm_tokens_input": 100.0, **{d: 10.0 for d in DIMS if d != "llm_tokens_input"}})
        act = _make_actuals({"llm_tokens_input": 125.0, **{d: 10.0 for d in DIMS if d != "llm_tokens_input"}})
        result = _mod._calculate_variance(est, act)
        assert result["dimensions"]["llm_tokens_input"]["overrun"] is True

    def test_exactly_20_percent_over_is_not_overrun(self):
        est = _make_estimate({"llm_tokens_input": 100.0, **{d: 10.0 for d in DIMS if d != "llm_tokens_input"}})
        act = _make_actuals({"llm_tokens_input": 120.0, **{d: 10.0 for d in DIMS if d != "llm_tokens_input"}})
        result = _mod._calculate_variance(est, act)
        assert result["dimensions"]["llm_tokens_input"]["overrun"] is False

    def test_20_01_percent_over_is_overrun(self):
        est = _make_estimate({"llm_tokens_input": 100.0, **{d: 10.0 for d in DIMS if d != "llm_tokens_input"}})
        act = _make_actuals({"llm_tokens_input": 120.01, **{d: 10.0 for d in DIMS if d != "llm_tokens_input"}})
        result = _mod._calculate_variance(est, act)
        assert result["dimensions"]["llm_tokens_input"]["overrun"] is True

    def test_total_variance_equals_sum_of_dimension_variances(self):
        est = _make_estimate({d: float(i * 10) for i, d in enumerate(DIMS, 1)})
        act = _make_actuals({d: float(i * 12) for i, d in enumerate(DIMS, 1)})
        result = _mod._calculate_variance(est, act)
        expected_total = sum(result["dimensions"][d]["variance_usd"] for d in DIMS)
        assert abs(result["total_variance_usd"] - expected_total) < 1e-9
