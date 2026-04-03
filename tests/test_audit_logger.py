"""Unit tests for the audit-logger MCP server NDJSON storage and SHA-256 hash chain."""

import hashlib
import importlib.util
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Load the server module from its non-standard path
_SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp-servers" / "audit-logger" / "server.py"
_spec = importlib.util.spec_from_file_location("audit_logger_server", _SERVER_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["audit_logger_server"] = _mod
_spec.loader.exec_module(_mod)


@pytest.fixture(autouse=True)
def tmp_audit_log(tmp_path):
    """Point AUDIT_LOG_PATH to a temp file for each test."""
    log_file = str(tmp_path / "audit.ndjson")
    _mod.AUDIT_LOG_PATH = log_file
    yield log_file


def _read_records(log_path: str) -> list[dict]:
    p = Path(log_path)
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class TestLogInteraction:
    def test_creates_record_with_correct_type(self, tmp_audit_log):
        result = _mod.log_interaction(
            workflow_id="wf1-test",
            initiator="dev-1",
            input_prompt="hello",
            ai_output="world",
            agent_role="developer",
        )
        records = _read_records(tmp_audit_log)
        assert len(records) == 1
        assert records[0]["type"] == "interaction"

    def test_returns_id_and_content_hash(self, tmp_audit_log):
        result = _mod.log_interaction(
            workflow_id="wf1-test",
            initiator="dev-1",
            input_prompt="hello",
            ai_output="world",
            agent_role="developer",
        )
        assert "id" in result
        assert "content_hash" in result
        assert len(result["content_hash"]) == 64  # SHA-256 hex length

    def test_payload_contains_interaction_fields(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1-test",
            initiator="dev-1",
            input_prompt="prompt-text",
            ai_output="output-text",
            agent_role="developer",
        )
        records = _read_records(tmp_audit_log)
        payload = records[0]["payload"]
        assert payload["input_prompt"] == "prompt-text"
        assert payload["ai_output"] == "output-text"
        assert payload["agent_role"] == "developer"

    def test_first_record_has_empty_previous_hash(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1-test",
            initiator="dev-1",
            input_prompt="hello",
            ai_output="world",
            agent_role="developer",
        )
        records = _read_records(tmp_audit_log)
        assert records[0]["previous_hash"] == ""


class TestLogCheckpoint:
    def test_creates_checkpoint_record(self, tmp_audit_log):
        result = _mod.log_checkpoint(
            workflow_id="wf1-test",
            checkpoint_id="cp-1",
            passed=True,
            validation_details="All tests passed",
        )
        records = _read_records(tmp_audit_log)
        assert len(records) == 1
        assert records[0]["type"] == "checkpoint"
        assert records[0]["payload"]["passed"] is True
        assert records[0]["payload"]["validation_details"] == "All tests passed"

    def test_includes_metrics_when_provided(self, tmp_audit_log):
        _mod.log_checkpoint(
            workflow_id="wf1-test",
            checkpoint_id="cp-1",
            passed=True,
            validation_details="Coverage check",
            metrics={"coverage_percent": 85},
        )
        records = _read_records(tmp_audit_log)
        assert records[0]["payload"]["metrics"] == {"coverage_percent": 85}

    def test_omits_metrics_when_none(self, tmp_audit_log):
        _mod.log_checkpoint(
            workflow_id="wf1-test",
            checkpoint_id="cp-1",
            passed=False,
            validation_details="Failed",
        )
        records = _read_records(tmp_audit_log)
        assert "metrics" not in records[0]["payload"]


class TestLogEvent:
    def test_creates_event_record(self, tmp_audit_log):
        result = _mod.log_event(
            workflow_id="wf1-test",
            event_type="workflow_start",
            initiator="dev-1",
        )
        records = _read_records(tmp_audit_log)
        assert len(records) == 1
        assert records[0]["type"] == "event"
        assert records[0]["payload"]["event_type"] == "workflow_start"

    def test_includes_details_when_provided(self, tmp_audit_log):
        _mod.log_event(
            workflow_id="wf1-test",
            event_type="rollback",
            initiator="dev-1",
            details={"reason": "test failure"},
        )
        records = _read_records(tmp_audit_log)
        assert records[0]["payload"]["details"] == {"reason": "test failure"}

    def test_omits_details_when_none(self, tmp_audit_log):
        _mod.log_event(
            workflow_id="wf1-test",
            event_type="workflow_end",
            initiator="dev-1",
        )
        records = _read_records(tmp_audit_log)
        assert "details" not in records[0]["payload"]


class TestHashChain:
    def test_content_hash_matches_sha256_of_payload(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1-test",
            initiator="dev-1",
            input_prompt="hello",
            ai_output="world",
            agent_role="developer",
        )
        records = _read_records(tmp_audit_log)
        payload = records[0]["payload"]
        expected = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        assert records[0]["content_hash"] == expected

    def test_second_record_previous_hash_equals_first_content_hash(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1-test",
            initiator="dev-1",
            input_prompt="first",
            ai_output="one",
            agent_role="developer",
        )
        _mod.log_event(
            workflow_id="wf1-test",
            event_type="workflow_end",
            initiator="dev-1",
        )
        records = _read_records(tmp_audit_log)
        assert len(records) == 2
        assert records[1]["previous_hash"] == records[0]["content_hash"]

    def test_chain_integrity_across_multiple_records(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="a", input_prompt="p1",
            ai_output="o1", agent_role="dev",
        )
        _mod.log_checkpoint(
            workflow_id="wf1", checkpoint_id="cp1", passed=True,
            validation_details="ok",
        )
        _mod.log_event(
            workflow_id="wf1", event_type="end", initiator="a",
        )
        records = _read_records(tmp_audit_log)
        assert len(records) == 3
        assert records[0]["previous_hash"] == ""
        for i in range(1, len(records)):
            assert records[i]["previous_hash"] == records[i - 1]["content_hash"]


class TestRecordFormat:
    def test_record_has_all_required_fields(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1-test",
            initiator="dev-1",
            input_prompt="hello",
            ai_output="world",
            agent_role="developer",
        )
        records = _read_records(tmp_audit_log)
        record = records[0]
        required_fields = {
            "id", "timestamp", "type", "workflow_id",
            "initiator", "content_hash", "previous_hash", "payload",
        }
        assert required_fields.issubset(record.keys())

    def test_timestamp_is_iso8601(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1-test",
            initiator="dev-1",
            input_prompt="hello",
            ai_output="world",
            agent_role="developer",
        )
        records = _read_records(tmp_audit_log)
        ts = records[0]["timestamp"]
        assert ts.endswith("Z")
        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")

    def test_ndjson_one_record_per_line(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="a", input_prompt="p",
            ai_output="o", agent_role="dev",
        )
        _mod.log_event(
            workflow_id="wf1", event_type="end", initiator="a",
        )
        with open(tmp_audit_log, "r") as f:
            lines = [line for line in f if line.strip()]
        assert len(lines) == 2
        for line in lines:
            json.loads(line)

    def test_creates_directory_if_not_exists(self, tmp_path):
        nested = str(tmp_path / "deep" / "nested" / "audit.ndjson")
        _mod.AUDIT_LOG_PATH = nested
        _mod.log_event(
            workflow_id="wf1", event_type="start", initiator="a",
        )
        assert Path(nested).exists()


class TestQueryAudit:
    """Tests for the query_audit tool."""

    def test_returns_empty_list_when_no_file(self, tmp_audit_log):
        result = _mod.query_audit()
        assert result == []

    def test_returns_all_records_when_no_filters(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-1",
            input_prompt="p1", ai_output="o1", agent_role="developer",
        )
        _mod.log_event(
            workflow_id="wf2", event_type="start", initiator="dev-2",
        )
        result = _mod.query_audit()
        assert len(result) == 2

    def test_filter_by_workflow_type(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-1",
            input_prompt="p1", ai_output="o1", agent_role="developer",
        )
        _mod.log_event(
            workflow_id="wf2", event_type="start", initiator="dev-1",
        )
        result = _mod.query_audit(workflow_type="wf1")
        assert len(result) == 1
        assert result[0]["workflow_id"] == "wf1"

    def test_filter_by_initiator(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-1",
            input_prompt="p1", ai_output="o1", agent_role="developer",
        )
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-2",
            input_prompt="p2", ai_output="o2", agent_role="developer",
        )
        result = _mod.query_audit(initiator="dev-2")
        assert len(result) == 1
        assert result[0]["initiator"] == "dev-2"

    def test_filter_by_type(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-1",
            input_prompt="p1", ai_output="o1", agent_role="developer",
        )
        _mod.log_checkpoint(
            workflow_id="wf1", checkpoint_id="cp1",
            passed=True, validation_details="ok",
        )
        _mod.log_event(
            workflow_id="wf1", event_type="end", initiator="dev-1",
        )
        result = _mod.query_audit(record_type="checkpoint")
        assert len(result) == 1
        assert result[0]["type"] == "checkpoint"

    def test_filter_by_outcome_success(self, tmp_audit_log):
        _mod.log_checkpoint(
            workflow_id="wf1", checkpoint_id="cp1",
            passed=True, validation_details="all good",
        )
        _mod.log_checkpoint(
            workflow_id="wf1", checkpoint_id="cp2",
            passed=False, validation_details="failed",
        )
        result = _mod.query_audit(outcome="success")
        assert len(result) == 1
        assert result[0]["payload"]["passed"] is True

    def test_filter_by_outcome_failed(self, tmp_audit_log):
        _mod.log_checkpoint(
            workflow_id="wf1", checkpoint_id="cp1",
            passed=True, validation_details="all good",
        )
        _mod.log_checkpoint(
            workflow_id="wf1", checkpoint_id="cp2",
            passed=False, validation_details="failed",
        )
        result = _mod.query_audit(outcome="failed")
        assert len(result) == 1
        assert result[0]["payload"]["passed"] is False

    def test_outcome_filter_excludes_non_checkpoint_records(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-1",
            input_prompt="p1", ai_output="o1", agent_role="developer",
        )
        _mod.log_checkpoint(
            workflow_id="wf1", checkpoint_id="cp1",
            passed=True, validation_details="ok",
        )
        result = _mod.query_audit(outcome="success")
        assert len(result) == 1
        assert result[0]["type"] == "checkpoint"

    def test_filter_by_date_from(self, tmp_audit_log):
        # Write records with known timestamps directly
        _write_record_with_timestamp(tmp_audit_log, "2026-03-01T10:00:00Z", "wf1", "dev-1")
        _write_record_with_timestamp(tmp_audit_log, "2026-03-05T10:00:00Z", "wf1", "dev-1")
        result = _mod.query_audit(date_from="2026-03-03T00:00:00Z")
        assert len(result) == 1
        assert result[0]["timestamp"] == "2026-03-05T10:00:00Z"

    def test_filter_by_date_to(self, tmp_audit_log):
        _write_record_with_timestamp(tmp_audit_log, "2026-03-01T10:00:00Z", "wf1", "dev-1")
        _write_record_with_timestamp(tmp_audit_log, "2026-03-05T10:00:00Z", "wf1", "dev-1")
        result = _mod.query_audit(date_to="2026-03-03T00:00:00Z")
        assert len(result) == 1
        assert result[0]["timestamp"] == "2026-03-01T10:00:00Z"

    def test_filter_by_date_range(self, tmp_audit_log):
        _write_record_with_timestamp(tmp_audit_log, "2026-03-01T10:00:00Z", "wf1", "dev-1")
        _write_record_with_timestamp(tmp_audit_log, "2026-03-05T10:00:00Z", "wf1", "dev-1")
        _write_record_with_timestamp(tmp_audit_log, "2026-03-10T10:00:00Z", "wf1", "dev-1")
        result = _mod.query_audit(
            date_from="2026-03-03T00:00:00Z",
            date_to="2026-03-07T00:00:00Z",
        )
        assert len(result) == 1
        assert result[0]["timestamp"] == "2026-03-05T10:00:00Z"

    def test_multiple_filters_combined(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-1",
            input_prompt="p1", ai_output="o1", agent_role="developer",
        )
        _mod.log_interaction(
            workflow_id="wf2", initiator="dev-1",
            input_prompt="p2", ai_output="o2", agent_role="developer",
        )
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-2",
            input_prompt="p3", ai_output="o3", agent_role="developer",
        )
        result = _mod.query_audit(workflow_type="wf1", initiator="dev-1")
        assert len(result) == 1
        assert result[0]["workflow_id"] == "wf1"
        assert result[0]["initiator"] == "dev-1"

    def test_no_matching_records_returns_empty(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-1",
            input_prompt="p1", ai_output="o1", agent_role="developer",
        )
        result = _mod.query_audit(workflow_type="nonexistent")
        assert result == []

    def test_filter_by_type_interaction(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-1",
            input_prompt="p1", ai_output="o1", agent_role="developer",
        )
        _mod.log_event(
            workflow_id="wf1", event_type="end", initiator="dev-1",
        )
        result = _mod.query_audit(record_type="interaction")
        assert len(result) == 1
        assert result[0]["type"] == "interaction"

    def test_filter_by_type_event(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-1",
            input_prompt="p1", ai_output="o1", agent_role="developer",
        )
        _mod.log_event(
            workflow_id="wf1", event_type="end", initiator="dev-1",
        )
        result = _mod.query_audit(record_type="event")
        assert len(result) == 1
        assert result[0]["type"] == "event"

    def test_combined_type_and_workflow_filter(self, tmp_audit_log):
        _mod.log_interaction(
            workflow_id="wf1", initiator="dev-1",
            input_prompt="p1", ai_output="o1", agent_role="developer",
        )
        _mod.log_event(
            workflow_id="wf1", event_type="start", initiator="dev-1",
        )
        _mod.log_event(
            workflow_id="wf2", event_type="start", initiator="dev-1",
        )
        result = _mod.query_audit(record_type="event", workflow_type="wf1")
        assert len(result) == 1
        assert result[0]["type"] == "event"
        assert result[0]["workflow_id"] == "wf1"

    def test_combined_outcome_and_initiator_filter(self, tmp_audit_log):
        _mod.log_checkpoint(
            workflow_id="wf1", checkpoint_id="cp1",
            passed=True, validation_details="ok",
        )
        _mod.log_checkpoint(
            workflow_id="wf1", checkpoint_id="cp2",
            passed=False, validation_details="fail",
        )
        # log_checkpoint uses workflow_id as initiator, so add one with a known initiator
        _mod._append_record("checkpoint", "wf1", "dev-1", {
            "checkpoint_id": "cp3", "passed": True, "validation_details": "ok",
        })
        result = _mod.query_audit(outcome="success", initiator="dev-1")
        assert len(result) == 1
        assert result[0]["payload"]["passed"] is True
        assert result[0]["initiator"] == "dev-1"


def _write_record_with_timestamp(
    log_path: str, timestamp: str, workflow_id: str, initiator: str
) -> None:
    """Write a minimal audit record with a specific timestamp for date filter tests."""
    record = {
        "id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "type": "event",
        "workflow_id": workflow_id,
        "initiator": initiator,
        "content_hash": "test",
        "previous_hash": "",
        "payload": {"event_type": "test"},
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")
