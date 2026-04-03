"""Checkpoint gate evaluators for the Jira-GitLab-Kiro integration pipeline.

Provides gate evaluation functions for coverage, security, and code
review checkpoints used in the ``checkpoint-gates`` pipeline stage.
"""

from __future__ import annotations

from typing import Any, Optional


def evaluate_coverage_gate(
    coverage_percent: float,
    threshold: Optional[int],
) -> dict[str, Any]:
    """Evaluate the test coverage checkpoint gate.

    Args:
        coverage_percent: Measured line coverage percentage (0–100).
        threshold: Required minimum coverage percentage, or ``None``
            to skip the check (e.g. for WF5 documentation workflows).

    Returns:
        A dictionary with ``passed`` (bool), ``skipped`` (bool), and
        ``details`` (str) describing the evaluation result.
    """
    if threshold is None:
        return {
            "passed": True,
            "skipped": True,
            "details": "Coverage check skipped (no threshold configured).",
        }

    passed = coverage_percent >= threshold
    details = (
        f"Coverage {coverage_percent}% >= {threshold}% threshold."
        if passed
        else f"Coverage {coverage_percent}% < {threshold}% threshold."
    )

    return {
        "passed": passed,
        "skipped": False,
        "details": details,
    }


def evaluate_security_gate(
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate the security scan checkpoint gate.

    Args:
        findings: List of security scan finding dictionaries, each
            expected to have a ``severity`` key.

    Returns:
        A dictionary with ``passed`` (bool) and ``details`` (str).
        The gate fails if any finding has severity ``"HIGH"`` or
        ``"CRITICAL"``.
    """
    blocking_severities = {"HIGH", "CRITICAL"}
    blocking = [
        f for f in findings
        if f.get("severity", "").upper() in blocking_severities
    ]

    if blocking:
        return {
            "passed": False,
            "details": (
                f"Security gate failed: {len(blocking)} HIGH/CRITICAL "
                f"finding(s) detected."
            ),
        }

    return {
        "passed": True,
        "details": f"Security gate passed ({len(findings)} finding(s), none HIGH/CRITICAL).",
    }


def evaluate_code_review_gate(
    review_result: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate the code review checkpoint gate.

    Args:
        review_result: Code review result dictionary expected to have
            a ``blocking_issues`` key with an integer count.

    Returns:
        A dictionary with ``passed`` (bool) and ``details`` (str).
        The gate fails if ``blocking_issues`` is greater than zero.
    """
    blocking_issues = review_result.get("blocking_issues", 0)

    if blocking_issues > 0:
        return {
            "passed": False,
            "details": (
                f"Code review gate failed: {blocking_issues} blocking "
                f"issue(s) found."
            ),
        }

    return {
        "passed": True,
        "details": "Code review gate passed (no blocking issues).",
    }
