"""Issue key validator for the Jira-GitLab-Kiro integration pipeline.

Validates that Jira issue keys conform to the expected pattern
``^[A-Z][A-Z0-9]+-[0-9]+$`` before they are used in downstream pipeline
stages.
"""

from __future__ import annotations

import re

_ISSUE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9]+-[0-9]+$")


def validate_issue_key(key: str) -> tuple[bool, str]:
    """Validate a Jira issue key against the expected pattern.

    The key must start with an uppercase letter, followed by one or more
    uppercase letters or digits, a hyphen, and one or more digits
    (e.g. ``PROJ-123``, ``AB-1``, ``XY99-42``).

    Args:
        key: The Jira issue key string to validate.

    Returns:
        A tuple of ``(is_valid, message)`` where *is_valid* is ``True``
        when the key matches the pattern, and *message* is either a
        success confirmation or a descriptive rejection reason.
    """
    if not isinstance(key, str) or not key:
        return False, "Issue key must be a non-empty string."

    if _ISSUE_KEY_PATTERN.match(key):
        return True, f"Issue key '{key}' is valid."

    return (
        False,
        f"Issue key '{key}' does not match the required pattern "
        f"'^[A-Z][A-Z0-9]+-[0-9]+$'. "
        f"Expected format: uppercase project prefix, hyphen, numeric ID "
        f"(e.g. 'PROJ-123').",
    )
