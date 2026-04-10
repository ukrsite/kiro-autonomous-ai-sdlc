"""Unit tests for the FinOps baseline manager."""

import json
import sys
import importlib.util
from pathlib import Path

import pytest

_SERVER_PATH = Path(__file__).resolve().parent.parent.parent / "mcp-servers" / "finops-cost-estimator" / "server.py"
_spec = importlib.util.spec_from_file_location("finops_server", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["finops_server"] = _mod
_spec.loader.exec_module(_mod)


def _make_actuals(dim_values: dict) -> dict:
    """Build a minimal PostRunActuals dict from {dim_name: quantity} mapping."""
    return {
        "dimensions": {
            dim: {"actual_quantity": qty, "unit_price_usd": 0.001, "actual_cost_usd": qty * 0.001}
            for dim, qty in dim_values.items()
        }
    }


class TestLoadBaseline:
    def test_missing_file_returns_empty_structure(self, tmp_path):
        result = _mod._load_baseline(str(tmp_path / "nonexistent.json"))
        assert result == {"wf1": {}, "wf2": {}}

    def test_corrupt_json_falls_back_to_empty_structure(self, tmp_path):
        p = tmp_path / "baselines.json"
        p.write_text("not valid json {{{{")
        result = _mod._load_baseline(str(p))
        assert result == {"wf1": {}, "wf2": {}}

    def test_valid_file_loads_correctly(self, tmp_path):
        data = {"wf1": {"llm_tokens_input": {"count": 1, "mean": 100.0, "p50": 100.0, "p95": 100.0}}, "wf2": {}}
        p = tmp_path / "baselines.json"
        p.write_text(json.dumps(data))
        result = _mod._load_baseline(str(p))
        assert result["wf1"]["llm_tokens_input"]["count"] == 1


class TestSaveBaseline:
    def test_save_and_reload_round_trip(self, tmp_path):
        p = tmp_path / "baselines.json"
        data = {"wf1": {"llm_tokens_input": {"count": 2, "mean": 50.0, "p50": 50.0, "p95": 90.0}}, "wf2": {}}
        _mod._save_baseline(data, str(p))
        loaded = json.loads(p.read_text())
        assert loaded["wf1"]["llm_tokens_input"]["count"] == 2


class TestUpdateBaseline:
    def test_increments_count_and_recomputes_stats(self):
        baseline = {"wf1": {}, "wf2": {}}
        actuals = _make_actuals({"llm_tokens_input": 100.0})
        _mod._update_baseline(baseline, "wf1", actuals)
        assert baseline["wf1"]["llm_tokens_input"]["count"] == 1
        assert baseline["wf1"]["llm_tokens_input"]["mean"] == 100.0

        actuals2 = _make_actuals({"llm_tokens_input": 200.0})
        _mod._update_baseline(baseline, "wf1", actuals2)
        assert baseline["wf1"]["llm_tokens_input"]["count"] == 2
        assert baseline["wf1"]["llm_tokens_input"]["mean"] == 150.0

    def test_wf2_baseline_unaffected_by_wf1_updates(self):
        baseline = {"wf1": {}, "wf2": {}}
        actuals = _make_actuals({"llm_tokens_input": 500.0})
        _mod._update_baseline(baseline, "wf1", actuals)
        assert baseline["wf2"] == {}

    def test_p50_is_median(self):
        baseline = {"wf1": {}, "wf2": {}}
        for v in [10.0, 20.0, 30.0]:
            _mod._update_baseline(baseline, "wf1", _make_actuals({"compute_time_seconds": v}))
        assert baseline["wf1"]["compute_time_seconds"]["p50"] == 20.0
