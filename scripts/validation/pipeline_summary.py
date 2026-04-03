"""Pipeline summary builder for the Jira-GitLab-Kiro integration pipeline.

Constructs the pipeline summary artifact dictionary written to
``finalize-output/pipeline-summary.json`` at the end of a pipeline run.
"""

from __future__ import annotations

from typing import Any, Optional


def build_pipeline_summary(
    pipeline_id: str,
    jira_issue_key: str,
    project_key: str,
    workflow_id: str,
    checkpoints: dict[str, Any],
    outcome: str,
    branch_name: Optional[str] = None,
    mr_url: Optional[str] = None,
) -> dict[str, Any]:
    """Build a pipeline summary artifact dictionary.

    Args:
        pipeline_id: The GitLab CI pipeline ID.
        jira_issue_key: The Jira issue key (e.g. ``"PROJ-123"``).
        project_key: The Jira project key (e.g. ``"PROJ"``).
        workflow_id: The workflow identifier that was executed.
        checkpoints: Dictionary of per-checkpoint outcomes.
        outcome: Overall pipeline outcome (``"success"`` or
            ``"failure"``).
        branch_name: The feature branch name. Included on success.
        mr_url: The merge request URL. Included on success.

    Returns:
        A dictionary containing all required pipeline summary fields.
        On success, ``branch_name`` and ``mr_url`` are included.
    """
    summary: dict[str, Any] = {
        "pipeline_id": pipeline_id,
        "jira_issue_key": jira_issue_key,
        "jira_project_key": project_key,
        "workflow_id": workflow_id,
        "checkpoints": checkpoints,
        "outcome": outcome,
    }

    if outcome == "success":
        if branch_name is not None:
            summary["branch_name"] = branch_name
        if mr_url is not None:
            summary["mr_url"] = mr_url

    return summary
