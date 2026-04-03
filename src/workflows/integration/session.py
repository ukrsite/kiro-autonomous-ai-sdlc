"""Session Continuity Handler for AI-DLC Workflow Integration.

Provides session resumption logic for the integrated AI-DLC + WF workflow.
Determines the correct resume point based on AIDLC state progress and
loads session state from aidlc-state.md for continuity across sessions.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import os
import re

from src.workflows.integration.models import IntegrationStatus
from src.workflows.integration.state import parse_integration_status


def determine_resume_point(state_content: str, handoff_exists: bool) -> str:
    """Determine the correct stage to resume from based on current state.

    Analyses the ``aidlc-state.md`` content and handoff artifact existence
    to decide where the integrated workflow should resume.

    Decision logic (evaluated in order):
    1. INCEPTION complete + handoff exists -> ``"CONSTRUCTION"``
    2. CONSTRUCTION in progress via a WF -> ``"CONSTRUCTION:{wf_id}"``
    3. INCEPTION in progress -> ``"INCEPTION:{last_incomplete_stage}"``
    4. No integration section found -> ``"INCEPTION:start"``

    Args:
        state_content: The full text content of aidlc-state.md.
        handoff_exists: Whether the handoff artifact file exists at
            ``aidlc-docs/inception/plans/workflow-handoff.md``.

    Returns:
        A string indicating the resume point. Format varies by case:
        ``"CONSTRUCTION"``, ``"CONSTRUCTION:{wf_id}"``,
        ``"INCEPTION:{stage_name}"``, or ``"INCEPTION:start"``.
    """
    try:
        status = parse_integration_status(state_content)
    except ValueError:
        return _resume_from_basic_stages(state_content)

    # Case 1: INCEPTION complete + handoff exists -> resume at CONSTRUCTION.
    if status in (IntegrationStatus.HANDOFF_PENDING, IntegrationStatus.COMPLETE) and handoff_exists:
        return "CONSTRUCTION"

    # Case 2: CONSTRUCTION in progress via a WF -> resume that WF.
    if status == IntegrationStatus.CONSTRUCTION_IN_PROGRESS:
        wf_id = _extract_selected_wf(state_content)
        if wf_id:
            return f"CONSTRUCTION:{wf_id}"
        return "CONSTRUCTION"

    # Case 3: INCEPTION in progress -> find last incomplete stage.
    if status == IntegrationStatus.INCEPTION_IN_PROGRESS:
        last_incomplete = _find_last_incomplete_inception_stage(state_content)
        if last_incomplete:
            return f"INCEPTION:{last_incomplete}"
        return "INCEPTION:start"

    # Fallback for HANDOFF_PENDING without handoff file.
    if status == IntegrationStatus.HANDOFF_PENDING and not handoff_exists:
        return "INCEPTION:Workflow Planning"

    return "INCEPTION:start"


def load_session_state(state_path: str) -> dict:
    """Read aidlc-state.md and extract integration progress information.

    Parses the state file to extract the workflow integration section
    and stage progress, returning a dict with the extracted info for
    use by the session continuity mechanism.

    Args:
        state_path: Filesystem path to aidlc-state.md.

    Returns:
        A dict with keys:
        - ``integration_status``: The IntegrationStatus value string,
          or ``None`` if not found.
        - ``selected_wf``: The selected workflow identifier string,
          or ``None`` if not found.
        - ``stages``: A list of dicts with ``name``, ``status``, and
          ``detail`` for each stage found in the Stage Progress section.

        Returns an empty dict if the file does not exist.
    """
    if not os.path.isfile(state_path):
        return {}

    try:
        with open(state_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        return {}

    result: dict = {
        "integration_status": None,
        "selected_wf": None,
        "stages": [],
    }

    # Extract integration status.
    try:
        status = parse_integration_status(content)
        result["integration_status"] = status.value
    except ValueError:
        pass

    # Extract selected WF.
    result["selected_wf"] = _extract_selected_wf(content)

    # Extract stage progress entries.
    result["stages"] = _parse_stage_entries(content)

    return result


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _extract_selected_wf(state_content: str) -> str | None:
    """Extract the selected WF identifier from the Workflow Integration section.

    Args:
        state_content: The full text content of aidlc-state.md.

    Returns:
        The WF identifier string (e.g. ``"wf1-requirement-to-software"``),
        or ``None`` if not found.
    """
    match = re.search(
        r"\*\*Selected WF\*\*:\s*(.+)",
        state_content,
    )
    if match:
        return match.group(1).strip()
    return None


def _find_last_incomplete_inception_stage(state_content: str) -> str | None:
    """Find the first pending INCEPTION stage from the Stage Progress section.

    Scans the INCEPTION PHASE subsection for stages marked ``[ ]``
    (pending). These are valid resume targets.

    Args:
        state_content: The full text content of aidlc-state.md.

    Returns:
        The name of the first pending INCEPTION stage, or ``None``
        if all stages are completed/skipped or no stages found.
    """
    inception_match = re.search(
        r"###\s*🔵\s*INCEPTION\s*PHASE\s*\n(.*?)(?=###|$)",
        state_content,
        re.DOTALL,
    )
    if not inception_match:
        return _find_first_pending_stage(state_content)

    return _find_first_pending_stage(inception_match.group(1))


def _find_first_pending_stage(content: str) -> str | None:
    """Find the first pending stage (``[ ]``) in the given content.

    Args:
        content: Text containing stage progress lines.

    Returns:
        The stage name of the first pending stage, or ``None``.
    """
    pattern = re.compile(r"^-\s*\[ \]\s*(.+?)$", re.MULTILINE)
    for match in pattern.finditer(content):
        stage_name = match.group(1).strip()
        if " - " in stage_name:
            stage_name = stage_name.split(" - ")[0].strip()
        return stage_name
    return None


def _parse_stage_entries(content: str) -> list[dict]:
    """Parse all stage progress entries from aidlc-state.md content.

    Recognises markers: ``[x]`` completed, ``[ ]`` pending,
    ``[-]`` skipped, ``[D]`` delegated.

    Args:
        content: The full text content of aidlc-state.md.

    Returns:
        A list of dicts, each with keys ``name``, ``status``, and
        ``detail`` (the text after the stage name, if any).
    """
    marker_map = {
        "[x]": "completed",
        "[ ]": "pending",
        "[-]": "skipped",
        "[D]": "delegated",
    }

    pattern = re.compile(
        r"^-\s*(\[[ xD\-]\])\s*(.+)$",
        re.MULTILINE,
    )

    stages: list[dict] = []
    for match in pattern.finditer(content):
        marker = match.group(1)
        raw_text = match.group(2).strip()

        status = marker_map.get(marker, "unknown")

        if " - " in raw_text:
            name, detail = raw_text.split(" - ", 1)
            name = name.strip()
            detail = detail.strip()
        else:
            name = raw_text
            detail = ""

        stages.append({
            "name": name,
            "status": status,
            "detail": detail,
        })

    return stages


def _resume_from_basic_stages(state_content: str) -> str:
    """Determine resume point from basic stage progress (no integration section).

    Used when no Workflow Integration section is found in the state file.
    Falls back to scanning the basic Stage Progress for the first pending
    INCEPTION stage.

    Args:
        state_content: The full text content of aidlc-state.md.

    Returns:
        ``"INCEPTION:{stage_name}"`` if a pending stage is found,
        otherwise ``"INCEPTION:start"``.
    """
    first_pending = _find_first_pending_stage(state_content)
    if first_pending:
        return f"INCEPTION:{first_pending}"
    return "INCEPTION:start"
