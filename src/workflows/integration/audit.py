"""Unified Audit Writer for AI-DLC Workflow Integration.

Provides dual-write audit functionality: human-readable markdown entries
appended to ``aidlc-docs/audit.md`` and machine-readable MCP-compatible
dicts suitable for the audit-logger MCP ``log_event`` tool.

Every audit-worthy event (INCEPTION stage completion, handoff, CONSTRUCTION
checkpoint, delegation) is written to both destinations so the complete
lifecycle of every development request is traceable.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
"""

from __future__ import annotations

from pathlib import Path

VALID_PHASES = ("INCEPTION", "CONSTRUCTION")

DEFAULT_AUDIT_MD_PATH = "aidlc-docs/audit.md"
DEFAULT_INITIATOR = "ai-dlc"


def format_audit_md_entry(
    stage_name: str,
    phase: str,
    user_input: str,
    ai_response: str,
    context: str,
    timestamp: str,
) -> str:
    """Return a markdown-formatted audit entry for ``aidlc-docs/audit.md``.

    The format matches the Unified Audit Trail entry format defined in the
    design document and the existing ``aidlc-docs/audit.md`` convention.

    Args:
        stage_name: Name of the stage or event type (used as the heading).
        phase: Workflow phase — must be ``"INCEPTION"`` or ``"CONSTRUCTION"``.
        user_input: The raw user input associated with this event.
        ai_response: The AI response or action taken.
        context: Additional context such as stage, action, or decision.
        timestamp: ISO 8601 formatted timestamp string.

    Returns:
        A markdown string ready to be appended to the audit file, including
        a trailing separator line (``---``).

    Raises:
        ValueError: If *phase* is not one of the valid phases.
    """
    if phase not in VALID_PHASES:
        raise ValueError(
            f"Invalid phase '{phase}'. Must be one of {VALID_PHASES}."
        )

    return (
        f"## {stage_name}\n"
        f"**Timestamp**: {timestamp}\n"
        f"**Phase**: {phase}\n"
        f'**User Input**: "{user_input}"\n'
        f'**AI Response**: "{ai_response}"\n'
        f"**Context**: {context}\n"
        f"\n---\n"
    )


def format_audit_mcp_record(
    workflow_id: str,
    event_type: str,
    phase: str,
    details: dict,
) -> dict:
    """Return an MCP-compatible dict for the audit-logger ``log_event`` tool.

    The returned dict contains the keys expected by the audit-logger MCP
    server's ``log_event`` tool.  The *phase* value is injected into the
    *details* dict so that every MCP record distinguishes INCEPTION from
    CONSTRUCTION entries (Requirement 6.7).

    Args:
        workflow_id: Identifier for the workflow
            (e.g. ``"aidlc-wf1-integration"``).
        event_type: Type of event (e.g. ``"handoff"``, ``"stage_completion"``).
        phase: Workflow phase — must be ``"INCEPTION"`` or ``"CONSTRUCTION"``.
        details: Additional event details.  A ``phase`` key will be added
            (or overwritten) with the supplied *phase* value.

    Returns:
        A dict with keys ``workflow_id``, ``event_type``, ``initiator``,
        and ``details`` (which always includes the ``phase`` field).

    Raises:
        ValueError: If *phase* is not one of the valid phases.
    """
    if phase not in VALID_PHASES:
        raise ValueError(
            f"Invalid phase '{phase}'. Must be one of {VALID_PHASES}."
        )

    merged_details = {**details, "phase": phase}

    return {
        "workflow_id": workflow_id,
        "event_type": event_type,
        "initiator": DEFAULT_INITIATOR,
        "details": merged_details,
    }


def append_audit_md(entry: str, path: str = DEFAULT_AUDIT_MD_PATH) -> None:
    """Append a markdown audit entry to the audit file.

    Creates parent directories if they do not exist, then appends the
    *entry* text to the file at *path*.  A leading newline is added when
    the file already has content so that entries are visually separated.

    Args:
        entry: The markdown-formatted audit entry to append (typically
            produced by :func:`format_audit_md_entry`).
        path: File path for the audit markdown file.  Defaults to
            ``aidlc-docs/audit.md``.
    """
    audit_path = Path(path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    prefix = ""
    if audit_path.exists() and audit_path.stat().st_size > 0:
        prefix = "\n"

    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(prefix + entry)


def validate_audit_entry(entry: dict) -> bool:
    """Check whether an audit entry dict contains all required fields.

    A valid entry must have the keys ``workflow_id``, ``event_type``,
    ``initiator``, and ``details``.  The ``details`` dict must contain a
    ``phase`` key whose value is ``"INCEPTION"`` or ``"CONSTRUCTION"``.

    Args:
        entry: The audit entry dict to validate (e.g. the output of
            :func:`format_audit_mcp_record`).

    Returns:
        ``True`` if the entry is valid, ``False`` otherwise.
    """
    required_keys = ("workflow_id", "event_type", "initiator", "details")
    for key in required_keys:
        if key not in entry:
            return False

    details = entry.get("details")
    if not isinstance(details, dict):
        return False

    phase = details.get("phase")
    if phase not in VALID_PHASES:
        return False

    return True


def validate_chronological_order(entries: list[dict]) -> bool:
    """Check that a list of audit entries has non-decreasing ISO 8601 timestamps.

    Each entry is expected to have a ``"timestamp"`` key with an ISO 8601
    string value.  The function returns ``True`` when every consecutive
    pair of timestamps satisfies ``t[i] <= t[i+1]`` using lexicographic
    comparison (which is correct for ISO 8601 strings in the same format).

    Args:
        entries: A list of dicts, each containing a ``"timestamp"`` key.

    Returns:
        ``True`` if timestamps are in non-decreasing order (or the list
        has fewer than two entries), ``False`` otherwise.
    """
    if len(entries) < 2:
        return True

    for i in range(len(entries) - 1):
        current = entries[i].get("timestamp", "")
        next_ts = entries[i + 1].get("timestamp", "")
        if current > next_ts:
            return False

    return True
