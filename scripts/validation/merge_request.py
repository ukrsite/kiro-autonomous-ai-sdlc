"""Merge request builder for the Jira-GitLab-Kiro integration pipeline.

Constructs merge request metadata dictionaries used by the finalize
stage to create GitLab merge requests via the gitlab MCP server.
"""

from __future__ import annotations

from typing import Any


def build_merge_request(
    issue_key: str,
    issue_summary: str,
    jira_url: str,
    workflow_id: str,
    project_config: dict[str, Any],
) -> dict[str, Any]:
    """Build a merge request metadata dictionary.

    Args:
        issue_key: The Jira issue key (e.g. ``"PROJ-123"``).
        issue_summary: The Jira issue summary text.
        jira_url: Full URL to the Jira issue.
        workflow_id: The workflow identifier that was executed.
        project_config: Resolved project configuration containing at
            least a ``target_branch`` key.

    Returns:
        A dictionary with ``title``, ``target_branch``, and
        ``description`` fields suitable for creating a GitLab merge
        request.
    """
    title = f"{issue_key}: {issue_summary}"
    target_branch = project_config.get("target_branch", "main")

    description = (
        f"## {issue_key}: {issue_summary}\n\n"
        f"**Jira Issue:** {jira_url}\n\n"
        f"**Workflow:** {workflow_id}\n\n"
        f"This merge request was generated automatically by the "
        f"Jira-GitLab-Kiro integration pipeline."
    )

    return {
        "title": title,
        "target_branch": target_branch,
        "description": description,
    }
