"""Audit record builders for the Jira-GitLab-Kiro integration pipeline.

Constructs structured audit record dictionaries for workflow start,
workflow end, and checkpoint events. These records are logged to the
audit-logger MCP server for traceability.
"""

from __future__ import annotations

from typing import Any, Optional


def build_workflow_start_record(
    jira_issue_key: str,
    project_key: str,
    workflow_id: str,
    pipeline_id: str,
    trigger_timestamp: str,
    initiator: str,
) -> dict[str, Any]:
    """Build an audit record for a workflow start event.

    Args:
        jira_issue_key: The Jira issue key (e.g. ``"PROJ-123"``).
        project_key: The Jira project key (e.g. ``"PROJ"``).
        workflow_id: The workflow identifier being executed.
        pipeline_id: The GitLab CI pipeline ID.
        trigger_timestamp: ISO 8601 timestamp of the trigger event.
        initiator: Identity of the user or system that initiated the
            workflow.

    Returns:
        A dictionary containing all required audit fields, with
        ``workflow_run_id`` containing the Jira issue key.
    """
    return {
        "event_type": "workflow_start",
        "workflow_run_id": f"{jira_issue_key}-{pipeline_id}",
        "jira_issue_key": jira_issue_key,
        "jira_project_key": project_key,
        "workflow_id": workflow_id,
        "pipeline_id": pipeline_id,
        "trigger_timestamp": trigger_timestamp,
        "initiator": initiator,
    }


def build_workflow_end_record(
    jira_issue_key: str,
    pipeline_id: str,
    workflow_id: str,
    outcome: str,
    duration: float,
    branch_name: Optional[str],
    mr_url: Optional[str],
) -> dict[str, Any]:
    """Build an audit record for a workflow end event.

    Args:
        jira_issue_key: The Jira issue key (e.g. ``"PROJ-123"``).
        pipeline_id: The GitLab CI pipeline ID.
        workflow_id: The workflow identifier that was executed.
        outcome: The workflow outcome (``"success"`` or ``"failure"``).
        duration: Execution duration in seconds.
        branch_name: The feature branch name, or ``None`` on failure.
        mr_url: The merge request URL, or ``None`` on failure.

    Returns:
        A dictionary containing all required audit fields including
        outcome and artifact references.
    """
    record: dict[str, Any] = {
        "event_type": "workflow_end",
        "workflow_run_id": f"{jira_issue_key}-{pipeline_id}",
        "jira_issue_key": jira_issue_key,
        "pipeline_id": pipeline_id,
        "workflow_id": workflow_id,
        "outcome": outcome,
        "duration": duration,
    }

    if branch_name is not None:
        record["branch_name"] = branch_name
    if mr_url is not None:
        record["mr_url"] = mr_url

    return record


def build_checkpoint_record(
    jira_issue_key: str,
    pipeline_id: str,
    checkpoint_name: str,
    passed: bool,
    details: str,
    threshold: Optional[Any] = None,
) -> dict[str, Any]:
    """Build an audit record for a checkpoint evaluation.

    Args:
        jira_issue_key: The Jira issue key (e.g. ``"PROJ-123"``).
        pipeline_id: The GitLab CI pipeline ID.
        checkpoint_name: Name of the checkpoint (e.g.
            ``"test-coverage"``, ``"security-scan"``).
        passed: Whether the checkpoint passed.
        details: Human-readable details about the checkpoint result.
        threshold: The threshold value applied, or ``None`` if not
            applicable.

    Returns:
        A dictionary containing all required checkpoint audit fields.
    """
    return {
        "event_type": "checkpoint",
        "workflow_run_id": f"{jira_issue_key}-{pipeline_id}",
        "jira_issue_key": jira_issue_key,
        "pipeline_id": pipeline_id,
        "checkpoint_name": checkpoint_name,
        "passed": passed,
        "details": details,
        "threshold": threshold,
    }
