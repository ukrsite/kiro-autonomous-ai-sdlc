"""Exit code handler for the Jira-GitLab-Kiro integration pipeline.

Classifies process exit codes into human-readable outcome strings
used by downstream pipeline stages and audit logging.
"""

from __future__ import annotations


def classify_exit_code(code: int) -> str:
    """Classify a process exit code as success or failure.

    Args:
        code: The integer exit code from a process invocation.

    Returns:
        ``"success"`` when *code* is ``0``, ``"failure"`` for all
        non-zero values.
    """
    return "success" if code == 0 else "failure"
