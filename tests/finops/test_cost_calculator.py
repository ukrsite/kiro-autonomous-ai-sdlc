"""Unit tests for the FinOps cost calculator."""

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


def _make_records(workflow_id="wf-test"):
    """Build a minimal set of audit records for testing."""
    return [
        {"workflow_id": workflow_id, "type": "event", "timestamp": "2026-01-01T10:00:00Z",
         "payload": {"event_type": "workflow_start"}},
        {"workflow_id": workflow_id, "type": "event", "timestamp": "2026-01-01T10:05:00Z",
         "payload": {"event_type": "tool_invocation"}},
        {"workflow_id": workflow_id, "type": "event", "timestamp": "2026-01-01T10:05:10Z",
         "payload": {"event_type": "tool_invocation"}},
        {"workflow_id": workflow_id, "type": "checkpoint", "timestamp": "2026-01-01T10:06:00Z",
         "payload": {"checkpoint_id": "cp1", "passed": True}},
        {"workflow_id": workflow_id, "type": "interaction", "timestamp": "2026-01-01T10:07:00Z",
         "payload": {"input_tokens": 1000, "output_tokens": 500, "input_prompt": "x", "ai_output": "y"}},
        {"workflow_id": workflow_id, "type": "event", "timestamp": "2026-01-01T10:10:00Z",
         "payload": {"event_type": "workflow_end"}},
    ]


class TestReadAuditRecords:
    def test_returns_empty_list_for_missing_file(self, tmp_path):
        result = _mod._read_audit_records("wf-test", str(tmp_path / "missing.ndjson"))
        assert result == []

    def test_filters_by_workflow_id(self, tmp_path):
        p = tmp_path / "audit.ndjson"
        records = _make_records("wf-test") + [
            {"workflow_id": "other-wf", "type": "event", "timestamp": "2026-01-01T10:00:00Z",
             "payload": {"event_type": "workflow_start"}}
        ]
        with open(p, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        result = _mod._read_audit_records("wf-test", str(p))
        assert all(r["workflow_id"] == "wf-test" for r in result)
        assert len(result) == len(_make_records("wf-test"))


class TestCalculateActuals:
    def test_known_records_produce_expected_values(self):
        records = _make_records()
        result = _mod._calculate_actuals("wf-test", records, COST_MODEL)
        assert "error" not in result
        assert result["dimensions"]["mcp_tool_invocations"]["actual_quantity"] == 2.0
        assert result["dimensions"]["checkpoint_executions"]["actual_quantity"] == 1.0
        assert result["dimensions"]["llm_tokens_input"]["actual_quantity"] == 1000.0
        assert result["dimensions"]["llm_tokens_output"]["actual_quantity"] == 500.0
        # compute_time = 10 minutes = 600 seconds
        assert result["dimensions"]["compute_time_seconds"]["actual_quantity"] == 600.0

    def test_missing_workflow_start_returns_error(self):
        records = [r for r in _make_records() if r.get("payload", {}).get("event_type") != "workflow_start"]
        result = _mod._calculate_actuals("wf-test", records, COST_MODEL)
        assert "error" in result
        assert "workflow_start" in result["error"]

    def test_missing_workflow_end_returns_error(self):
        records = [r for r in _make_records() if r.get("payload", {}).get("event_type") != "workflow_end"]
        result = _mod._calculate_actuals("wf-test", records, COST_MODEL)
        assert "error" in result
        assert "workflow_end" in result["error"]

    def test_interaction_without_token_fields_uses_compute_time_estimate(self):
        records = [
            {"workflow_id": "wf-test", "type": "event", "timestamp": "2026-01-01T10:00:00Z",
             "payload": {"event_type": "workflow_start"}},
            {"workflow_id": "wf-test", "type": "interaction", "timestamp": "2026-01-01T10:01:00Z",
             "payload": {"input_prompt": "abcd", "ai_output": "efgh"}},
            {"workflow_id": "wf-test", "type": "event", "timestamp": "2026-01-01T10:02:00Z",
             "payload": {"event_type": "workflow_end"}},
        ]
        result = _mod._calculate_actuals("wf-test", records, COST_MODEL)
        # Without explicit tokens, falls back to compute-time estimation
        # 120 seconds × 40 tok/s = 4800 output, × 2.5 = 12000 input
        assert result["token_count_method"] == "estimated-from-compute-time"
        assert result["dimensions"]["llm_tokens_output"]["actual_quantity"] == 120.0 * 40.0
        assert result["dimensions"]["llm_tokens_input"]["actual_quantity"] == 120.0 * 40.0 * 2.5

    def test_interaction_with_token_fields_uses_recorded(self):
        result = _mod._calculate_actuals("wf-test", _make_records(), COST_MODEL)
        assert result["token_count_method"] == "recorded"

    def test_empty_audit_log_returns_error(self):
        result = _mod._calculate_actuals("unknown-wf", [], COST_MODEL)
        assert "error" in result
