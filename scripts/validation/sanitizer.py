"""Input sanitizer for the Jira-GitLab-Kiro integration pipeline.

Escapes shell metacharacters, strips HTML tags, and truncates oversized
inputs to prevent injection attacks when Jira issue content is used as
prompt input for Kiro CLI.
"""

from __future__ import annotations

import re

_MAX_INPUT_LENGTH = 10_000

_SHELL_METACHARACTERS = r'$`\"!|;&()'

_HTML_TAG_PATTERN = re.compile(r"<[^>]*>")


def sanitize_input(text: str) -> str:
    """Sanitize an input string for safe use in shell and prompt contexts.

    Processing steps (in order):

    1. Escape shell metacharacters (``$ ` \\ " ! | ; & ( )``) by
       prepending a backslash.
    2. Strip all HTML tags.
    3. Truncate the result to a maximum of 10,000 characters.

    Args:
        text: The raw input string to sanitize.

    Returns:
        The sanitized string with dangerous characters escaped, HTML
        tags removed, and length capped at 10,000 characters.
    """
    if not isinstance(text, str):
        return ""

    # Step 1: Escape shell metacharacters.
    # We must escape backslash first to avoid double-escaping.
    result = text.replace("\\", "\\\\")
    for char in '$`"!|;&()':
        result = result.replace(char, f"\\{char}")

    # Step 2: Strip HTML tags.
    result = _HTML_TAG_PATTERN.sub("", result)

    # Step 3: Truncate to maximum length.
    if len(result) > _MAX_INPUT_LENGTH:
        result = result[:_MAX_INPUT_LENGTH]

    return result
