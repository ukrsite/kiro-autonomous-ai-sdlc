"""Jira status transition logic for the Jira-GitLab-Kiro integration pipeline.

Determines the correct Jira status transition based on pipeline outcome
and builds structured comments for Jira issue updates.
"""

from __future__ import annotations

from typing import Optional


def determine_transition(success: bool, mr_created: bool) -> str:
    """Determine the Jira status transition based on pipeline outcome.

    Args:
        success: Whether the pipeline completed successfully.
        mr_created: Whether a merge request was created.

    Returns:
        ``"In Review"`` when the pipeline succeeded and a merge request
        was created, ``"AI Dev Failed"`` otherwise.
    """
    if success and mr_created:
        return "In Review"
    return "AI Dev Failed"


def build_jira_comment(
    pipeline_url: str,
    outcome_details: str,
    mr_url: Optional[str] = None,
) -> str:
    """Build a Jira comment string for a pipeline execution.

    Args:
        pipeline_url: URL to the GitLab CI pipeline run.
        outcome_details: Human-readable description of the pipeline
            outcome.
        mr_url: Optional URL to the created merge request. Included
            in the comment when the pipeline succeeds.

    Returns:
        A formatted comment string containing the pipeline URL,
        outcome details, and optionally the merge request link.
    """
    lines = [
        f"**Pipeline:** {pipeline_url}",
        f"**Outcome:** {outcome_details}",
    ]

    if mr_url:
        lines.append(f"**Merge Request:** {mr_url}")

    return "\n".join(lines)
