"""Audit Logger MCP Server.

Append-only NDJSON logging with SHA-256 hash chain for tamper evidence.
Exposes tools for logging AI interactions, checkpoints, events, and querying audit records.
"""

import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

AUDIT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "audit/audit.ndjson")

mcp = FastMCP("audit-logger")

# Lock for thread-safe file access
_file_lock = threading.Lock()


def _get_last_content_hash() -> str:
    """Read the last record's content_hash from the NDJSON file.

    Returns the content_hash of the last record, or an empty string if the
    file is empty or does not exist (genesis record).
    """
    log_path = Path(AUDIT_LOG_PATH)
    if not log_path.exists() or log_path.stat().st_size == 0:
        return ""
    last_line = ""
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                last_line = stripped
    if not last_line:
        return ""
    record = json.loads(last_line)
    return record.get("content_hash", "")


def _compute_content_hash(payload: dict) -> str:
    """Compute SHA-256 hash of the JSON-serialized payload."""
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload_bytes).hexdigest()


def _append_record(record_type: str, workflow_id: str, initiator: str, payload: dict) -> dict:
    """Create and append an audit record to the NDJSON log file.

    Args:
        record_type: One of "interaction", "checkpoint", "event".
        workflow_id: The workflow identifier.
        initiator: Identity of the initiator.
        payload: The record payload dict.

    Returns:
        A dict with the created record's id and content_hash.
    """
    log_path = Path(AUDIT_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with _file_lock:
        previous_hash = _get_last_content_hash()
        content_hash = _compute_content_hash(payload)
        record_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        record = {
            "id": record_id,
            "timestamp": timestamp,
            "type": record_type,
            "workflow_id": workflow_id,
            "initiator": initiator,
            "content_hash": content_hash,
            "previous_hash": previous_hash,
            "payload": payload,
        }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

    return {"id": record_id, "content_hash": content_hash}


@mcp.tool()
def log_interaction(
    workflow_id: str,
    initiator: str,
    input_prompt: str,
    ai_output: str,
    agent_role: str,
) -> dict:
    """Log an AI interaction.

    Records an AI interaction including the input prompt, generated output,
    and the agent role, with a SHA-256 hash chain for tamper evidence.

    Args:
        workflow_id: Identifier for the workflow (e.g. "wf1-requirement-to-software").
        initiator: Identity of the user or system that initiated the interaction.
        input_prompt: The input prompt sent to the AI.
        ai_output: The AI-generated output.
        agent_role: The role of the agent (e.g. "developer", "devops").

    Returns:
        A dict with the created audit record's id and content_hash.
    """
    payload = {
        "input_prompt": input_prompt,
        "ai_output": ai_output,
        "agent_role": agent_role,
    }
    return _append_record("interaction", workflow_id, initiator, payload)


@mcp.tool()
def log_checkpoint(
    workflow_id: str,
    checkpoint_id: str,
    passed: bool,
    validation_details: str,
    metrics: Optional[dict] = None,
) -> dict:
    """Log a checkpoint result.

    Records the result of a validation checkpoint including pass/fail status,
    details, and optional metrics, with a SHA-256 hash chain for tamper evidence.

    Args:
        workflow_id: Identifier for the workflow.
        checkpoint_id: Identifier for the specific checkpoint.
        passed: Whether the checkpoint passed.
        validation_details: Details about the validation result.
        metrics: Optional dict of numeric metrics (e.g. {"coverage_percent": 85}).

    Returns:
        A dict with the created audit record's id and content_hash.
    """
    payload: dict = {
        "checkpoint_id": checkpoint_id,
        "passed": passed,
        "validation_details": validation_details,
    }
    if metrics is not None:
        payload["metrics"] = metrics
    return _append_record("checkpoint", workflow_id, workflow_id, payload)


@mcp.tool()
def log_event(
    workflow_id: str,
    event_type: str,
    initiator: str,
    details: Optional[dict] = None,
) -> dict:
    """Log a workflow lifecycle event.

    Records workflow lifecycle events such as start, end, rollback, or trigger fired,
    with a SHA-256 hash chain for tamper evidence.

    Args:
        workflow_id: Identifier for the workflow.
        event_type: Type of event (e.g. "workflow_start", "workflow_end", "rollback").
        initiator: Identity of the user or system that initiated the event.
        details: Optional dict of additional event details.

    Returns:
        A dict with the created audit record's id and content_hash.
    """
    payload: dict = {
        "event_type": event_type,
    }
    if details is not None:
        payload["details"] = details
    return _append_record("event", workflow_id, initiator, payload)


@mcp.tool()
def query_audit(
    workflow_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    initiator: Optional[str] = None,
    outcome: Optional[str] = None,
    record_type: Optional[str] = None,
) -> list:
    """Query audit records with filters.

    Searches the audit log and returns records matching all specified filter criteria.
    All specified filters are combined with AND logic — only records matching every
    filter are returned. If no filters are specified, all records are returned.

    Args:
        workflow_type: Filter by workflow ID (e.g. "wf1-requirement-to-software").
        date_from: Filter records from this ISO 8601 datetime (inclusive).
        date_to: Filter records up to this ISO 8601 datetime (inclusive).
        initiator: Filter by initiator identity.
        outcome: Filter by outcome ("success" means checkpoint passed,
            "failed" means checkpoint failed). Only checkpoint records can match.
        record_type: Filter by record type ("interaction", "checkpoint", or "event").

    Returns:
        A list of matching audit records.
    """
    log_path = Path(AUDIT_LOG_PATH)
    if not log_path.exists() or log_path.stat().st_size == 0:
        return []

    # Read all records from the NDJSON file
    records = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))

    # Apply filters with AND logic — skip records that fail any filter
    results = []
    for record in records:
        if workflow_type is not None and record.get("workflow_id") != workflow_type:
            continue
        if date_from is not None and record.get("timestamp", "") < date_from:
            continue
        if date_to is not None and record.get("timestamp", "") > date_to:
            continue
        if initiator is not None and record.get("initiator") != initiator:
            continue
        if outcome is not None:
            # outcome filter only applies to checkpoint records
            if record.get("type") != "checkpoint":
                continue
            passed = record.get("payload", {}).get("passed")
            if outcome == "success" and passed is not True:
                continue
            if outcome == "failed" and passed is not False:
                continue
        if record_type is not None and record.get("type") != record_type:
            continue
        results.append(record)

    return results


if __name__ == "__main__":
    mcp.run()
