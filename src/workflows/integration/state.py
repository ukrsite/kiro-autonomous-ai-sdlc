"""AIDLC State Manager for AI-DLC Workflow Integration.

Manages the Workflow Integration and Stage Progress sections in
aidlc-state.md, including formatting, parsing, validation, and
file updates for the integrated AI-DLC + WF workflow.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import re

from src.workflows.integration.models import (
    DelegationMarker,
    IntegrationStatus,
    RequestType,
    StageStatus,
    WorkflowId,
)

# Marker symbols for stage progress rendering.
_STATUS_MARKERS = {
    "Completed": "[x]",
    "Pending": "[ ]",
    "Skipped": "[-]",
}


def format_workflow_integration_section(
    wf_id: WorkflowId,
    request_type: RequestType,
    handoff_timestamp: str,
    status: IntegrationStatus,
) -> str:
    """Return the 'Workflow Integration' markdown section for aidlc-state.md.

    Formats the section that records the selected workflow, request type
    classification, handoff timestamp, and overall integration status.

    Args:
        wf_id: The selected workflow identifier.
        request_type: The classified request type.
        handoff_timestamp: ISO 8601 timestamp of the handoff.
        status: Current integration status.

    Returns:
        A markdown string containing the Workflow Integration section.
    """
    return (
        "## Workflow Integration\n"
        f"- **Selected WF**: {wf_id.value}\n"
        f"- **Request Type**: {request_type.value}\n"
        f"- **Handoff Timestamp**: {handoff_timestamp}\n"
        f"- **Integration Status**: {status.value}\n"
    )


def format_stage_progress_section(
    inception_stages: list[dict],
    construction_stages: list[DelegationMarker],
) -> str:
    """Return the 'Stage Progress' markdown section for aidlc-state.md.

    Renders INCEPTION and CONSTRUCTION phase progress using checkbox
    markers: ``[x]`` completed, ``[ ]`` pending, ``[-]`` skipped,
    ``[D]`` delegated to a WF.

    Args:
        inception_stages: List of dicts with keys ``stage_name``,
            ``status`` (one of ``'Completed'``, ``'Pending'``,
            ``'Skipped'``), and optional ``completed_at`` (ISO 8601
            timestamp string).
        construction_stages: List of :class:`DelegationMarker` objects
            representing CONSTRUCTION stage delegation state.

    Returns:
        A markdown string containing the Stage Progress section with
        INCEPTION PHASE and CONSTRUCTION PHASE subsections.
    """
    lines: list[str] = ["## Stage Progress"]

    # INCEPTION PHASE
    lines.append("### 🔵 INCEPTION PHASE")
    for stage in inception_stages:
        marker = _STATUS_MARKERS.get(stage["status"], "[ ]")
        suffix = ""
        if stage["status"] == "Completed":
            suffix = f" - COMPLETED {stage.get('completed_at', '')}"
        elif stage["status"] == "Skipped":
            suffix = " - SKIPPED"
        lines.append(f"- {marker} {stage['stage_name']}{suffix}")

    # CONSTRUCTION PHASE
    lines.append("")
    lines.append("### 🟢 CONSTRUCTION PHASE")
    for marker_obj in construction_stages:
        if marker_obj.status == StageStatus.COMPLETED:
            lines.append(
                f"- [x] {marker_obj.stage_name}"
                f" - completed by {marker_obj.wf_id.value}"
            )
        elif marker_obj.status == StageStatus.DELEGATED:
            lines.append(
                f"- [D] {marker_obj.stage_name}"
                f" - delegated to {marker_obj.wf_id.value}"
            )
        elif marker_obj.status == StageStatus.SKIPPED:
            lines.append(f"- [-] {marker_obj.stage_name}")
        else:
            lines.append(f"- [ ] {marker_obj.stage_name}")

    return "\n".join(lines) + "\n"


def parse_integration_status(state_content: str) -> IntegrationStatus:
    """Extract the integration status from existing aidlc-state.md content.

    Searches for the ``**Integration Status**:`` line within the
    Workflow Integration section and returns the matching enum value.

    Args:
        state_content: The full text content of aidlc-state.md.

    Returns:
        The :class:`IntegrationStatus` enum member matching the value.

    Raises:
        ValueError: If the integration status line is not found or the
            value does not match any valid ``IntegrationStatus``.
    """
    match = re.search(
        r"\*\*Integration Status\*\*:\s*(.+)",
        state_content,
    )
    if not match:
        raise ValueError(
            "Integration status not found in state content. "
            "Expected a line matching '**Integration Status**: <value>'."
        )

    raw_value = match.group(1).strip()

    for member in IntegrationStatus:
        if member.value == raw_value:
            return member

    valid = ", ".join(f'"{m.value}"' for m in IntegrationStatus)
    raise ValueError(
        f"Invalid integration status '{raw_value}'. "
        f"Expected one of: {valid}."
    )


def validate_integration_status(status: str) -> bool:
    """Check whether a status string is a valid IntegrationStatus value.

    Args:
        status: The status string to validate.

    Returns:
        ``True`` if *status* matches one of the four valid
        :class:`IntegrationStatus` enum values, ``False`` otherwise.
    """
    valid_values = {member.value for member in IntegrationStatus}
    return status in valid_values


def update_aidlc_state(
    state_path: str,
    integration_section: str,
    progress_section: str,
) -> None:
    """Update or create aidlc-state.md with integration and progress sections.

    Reads the existing file (if present), replaces the
    ``## Workflow Integration`` and ``## Stage Progress`` sections if they
    already exist, or appends them at the end. Creates the file when it
    does not exist.

    Args:
        state_path: Filesystem path to aidlc-state.md.
        integration_section: Formatted Workflow Integration section
            (from :func:`format_workflow_integration_section`).
        progress_section: Formatted Stage Progress section
            (from :func:`format_stage_progress_section`).
    """
    try:
        with open(state_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except FileNotFoundError:
        content = ""

    content = _replace_or_append_section(
        content, "## Workflow Integration", integration_section
    )
    content = _replace_or_append_section(
        content, "## Stage Progress", progress_section
    )

    with open(state_path, "w", encoding="utf-8") as fh:
        fh.write(content)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _replace_or_append_section(
    content: str,
    heading: str,
    new_section: str,
) -> str:
    """Replace an existing markdown section or append it.

    A *section* starts at ``heading`` (a ``##`` line) and extends until
    the next ``##`` heading or end-of-file.

    Args:
        content: The full file content.
        heading: The ``##`` heading that marks the section start.
        new_section: The replacement section text (including heading).

    Returns:
        Updated content with the section replaced or appended.
    """
    escaped = re.escape(heading)
    pattern = re.compile(
        rf"^{escaped}\s*\n(?:(?!^## ).*\n?)*",
        re.MULTILINE,
    )

    if pattern.search(content):
        content = pattern.sub(new_section, content)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += "\n" + new_section

    return content
