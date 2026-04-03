"""CI Auto-Approval Controller for AI-DLC Workflow Integration.

Active only when the ``--no-interactive`` flag is detected on the
``kiro-cli`` invocation.  Intercepts INCEPTION approval gates and
auto-selects the most secure/compliant option.

Auto-approved gates (CI mode only):
    Requirements Analysis, User Stories, Workflow Planning,
    Application Design, Units Generation.

Never auto-approved (always execute regardless of mode):
    Checkpoint gates — test coverage, security scan, code review.

Blocks auto-approval when gate output contains:
    unresolved security findings, missing input validation,
    hardcoded credentials, or violations of security-rules.md /
    coding-standards.md.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9
"""

from __future__ import annotations

# INCEPTION gates eligible for auto-approval in CI mode.
_INCEPTION_GATES: frozenset[str] = frozenset({
    "Requirements Analysis",
    "User Stories",
    "Workflow Planning",
    "Application Design",
    "Units Generation",
})

# Checkpoint gates that must always execute — never auto-approved.
_CHECKPOINT_GATES: frozenset[str] = frozenset({
    "test coverage",
    "security scan",
    "code review",
})

# Keywords in gate output that block auto-approval (Requirement 13.5).
_BLOCKING_KEYWORDS: tuple[str, ...] = (
    "unresolved security findings",
    "missing input validation",
    "hardcoded credentials",
    "security-rules.md violation",
    "coding-standards.md violation",
)


def is_ci_mode(args: list[str]) -> bool:
    """Detect whether the CLI was invoked in non-interactive CI mode.

    Args:
        args: The command-line argument list (e.g. ``sys.argv[1:]``).

    Returns:
        ``True`` if ``--no-interactive`` is present in *args*.
    """
    return "--no-interactive" in args


def should_auto_approve(
    gate_name: str,
    gate_output: dict,
    ci_mode: bool,
) -> tuple[bool, str]:
    """Decide whether a gate should be auto-approved.

    Decision logic (evaluated in order):

    1. If not in CI mode -> never auto-approve.
    2. If the gate is a checkpoint gate -> never auto-approve.
    3. If the gate output contains blocking security/compliance
       keywords -> block auto-approval.
    4. If the gate is an INCEPTION gate -> auto-approve.
    5. Otherwise -> do not auto-approve (unknown gate).

    Args:
        gate_name: Name of the approval gate (e.g.
            ``"Requirements Analysis"``).
        gate_output: Dict representing the gate's output.  The function
            inspects string values (recursively) for blocking keywords.
        ci_mode: Whether the CLI is running in ``--no-interactive`` mode.

    Returns:
        A ``(approved, rationale)`` tuple.  *approved* is ``True`` when
        the gate should be auto-approved; *rationale* explains the
        decision.
    """
    # Rule 1: interactive mode — require human approval.
    if not ci_mode:
        return (False, "Interactive mode — explicit human approval required")

    # Rule 2: checkpoint gates are never auto-approved.
    gate_lower = gate_name.lower()
    for checkpoint in _CHECKPOINT_GATES:
        if checkpoint in gate_lower:
            return (
                False,
                f"Checkpoint gate '{gate_name}' always executes regardless of mode",
            )

    # Rule 3: check for blocking compliance issues in gate output.
    blocking_issue = _find_blocking_issue(gate_output)
    if blocking_issue:
        return (
            False,
            f"Blocked — gate output contains: {blocking_issue}",
        )

    # Rule 4: INCEPTION gates are auto-approved in CI mode.
    if gate_name in _INCEPTION_GATES:
        return (
            True,
            f"CI auto-approval — INCEPTION gate '{gate_name}' approved, "
            "no blocking compliance issues detected",
        )

    # Rule 5: unknown gate — do not auto-approve.
    return (False, f"Gate '{gate_name}' is not an auto-approvable INCEPTION gate")


def format_auto_approval_record(
    gate_name: str,
    selected_option: str,
    rationale: str,
    compliance_checks: list[str],
    timestamp: str,
) -> dict:
    """Format an audit-compatible record for an auto-approval decision.

    The returned dict is suitable for writing to the Unified Audit Trail
    via the audit-logger MCP ``log_event`` tool.

    Args:
        gate_name: Name of the gate that was auto-approved.
        selected_option: The option selected (e.g. ``"approve"``).
        rationale: Explanation of why this option was selected.
        compliance_checks: List of compliance checks performed
            (e.g. ``["security-rules.md", "coding-standards.md"]``).
        timestamp: ISO 8601 formatted timestamp string.

    Returns:
        A dict with keys ``workflow_id``, ``event_type``, ``initiator``,
        and ``details`` containing the auto-approval metadata.
    """
    return {
        "workflow_id": "aidlc-ci-auto",
        "event_type": "auto_approval",
        "initiator": "kiro-cli-ci",
        "details": {
            "phase": "INCEPTION",
            "gate_name": gate_name,
            "selected_option": selected_option,
            "rationale": rationale,
            "compliance_checks": compliance_checks,
            "timestamp": timestamp,
        },
    }


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _find_blocking_issue(gate_output: dict) -> str | None:
    """Scan gate output values for blocking compliance keywords.

    Performs a case-insensitive search across all string values in the
    dict (one level deep, plus list items).

    Args:
        gate_output: The gate output dict to inspect.

    Returns:
        The first blocking keyword found, or ``None`` if clean.
    """
    for value in gate_output.values():
        texts: list[str] = []
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, list):
            texts.extend(str(item) for item in value)
        elif isinstance(value, dict):
            texts.extend(str(v) for v in value.values())

        for text in texts:
            text_lower = text.lower()
            for keyword in _BLOCKING_KEYWORDS:
                if keyword in text_lower:
                    return keyword

    return None
