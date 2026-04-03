"""Branch naming module for the Jira-GitLab-Kiro integration pipeline.

Generates feature branch names in the ``workflow/{workflow}/{issue_key_lower}``
format, ensuring the issue key is validated before use.
"""

from __future__ import annotations

from scripts.validation.issue_key_validator import validate_issue_key

# Valid workflow identifiers
VALID_WORKFLOWS = (
    "wf1-requirement-to-software",
    "wf2-autonomous-refactoring",
    "wf3-dependency-upgrades",
    "wf4-bug-fix",
    "wf5-documentation",
)


def generate_branch_name(
    issue_key: str,
    workflow: str = "wf1-requirement-to-software",
) -> str:
    """Generate a Git branch name for the given Jira issue key and workflow.

    The branch name follows the pattern ``workflow/{workflow}/{issue_key_lower}``
    (e.g. ``workflow/wf1-requirement-to-software/san-123``).

    Args:
        issue_key: A valid Jira issue key (e.g. ``"SAN-123"``).
        workflow: The workflow identifier (e.g. ``"wf1-requirement-to-software"``).

    Returns:
        The generated branch name string.

    Raises:
        ValueError: If *issue_key* does not match the required pattern
            or *workflow* is not a valid workflow identifier.
    """
    is_valid, message = validate_issue_key(issue_key)
    if not is_valid:
        raise ValueError(f"Cannot generate branch name: {message}")

    if workflow not in VALID_WORKFLOWS:
        raise ValueError(
            f"Cannot generate branch name: invalid workflow '{workflow}'. "
            f"Valid: {', '.join(VALID_WORKFLOWS)}"
        )

    return f"workflow/{workflow}/{issue_key.lower()}"
