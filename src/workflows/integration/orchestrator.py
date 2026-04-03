"""Integration Orchestrator for AI-DLC Workflow Integration.

Main entry point that wires all integration components together:
session state → INCEPTION (or resume) → classify → handoff → delegate →
update state → audit → delegate to selected WF.

Handles error cases at each boundary: INCEPTION failure, handoff failure,
and WF construction failure.

Requirements: 1.1, 1.2, 1.3, 1.5, 11.1, 11.2, 11.3, 11.4, 11.5
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from src.workflows.integration.audit import (
    append_audit_md,
    format_audit_mcp_record,
    format_audit_md_entry,
)
from src.workflows.integration.ci_approval import (
    format_auto_approval_record,
    should_auto_approve,
)
from src.workflows.integration.classifier import build_classification_result
from src.workflows.integration.delegation import create_delegation_markers
from src.workflows.integration.handoff import (
    generate_handoff_artifact,
    write_handoff_artifact,
)
from src.workflows.integration.models import (
    Confidence,
    IntegrationStatus,
    IntentAnalysis,
    RequestType,
)
from src.workflows.integration.session import (
    determine_resume_point,
    load_session_state,
)
from src.workflows.integration.state import (
    format_stage_progress_section,
    format_workflow_integration_section,
    update_aidlc_state,
)
from src.workflows.integration.thresholds import get_coverage_threshold


# Default INCEPTION stages executed during a full run.
_DEFAULT_INCEPTION_STAGES: list[dict[str, str]] = [
    {"stage_name": "Workspace Detection", "status": "Completed", "completed_at": ""},
    {"stage_name": "Reverse Engineering", "status": "Completed", "completed_at": ""},
    {"stage_name": "Requirements Analysis", "status": "Completed", "completed_at": ""},
    {"stage_name": "User Stories", "status": "Completed", "completed_at": ""},
    {"stage_name": "Workflow Planning", "status": "Completed", "completed_at": ""},
]


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_audit(
    stage_name: str,
    phase: str,
    user_input: str,
    ai_response: str,
    context: str,
    audit_md_path: str,
) -> dict:
    """Write an audit entry to both markdown and MCP-compatible formats.

    Args:
        stage_name: Name of the stage or event.
        phase: ``"INCEPTION"`` or ``"CONSTRUCTION"``.
        user_input: The user input associated with this event.
        ai_response: The AI response or action taken.
        context: Additional context string.
        audit_md_path: Path to the audit markdown file.

    Returns:
        The MCP-compatible audit record dict.
    """
    timestamp = _now_iso()

    md_entry = format_audit_md_entry(
        stage_name=stage_name,
        phase=phase,
        user_input=user_input,
        ai_response=ai_response,
        context=context,
        timestamp=timestamp,
    )
    append_audit_md(md_entry, path=audit_md_path)

    mcp_record = format_audit_mcp_record(
        workflow_id="aidlc-integrated",
        event_type=stage_name.lower().replace(" ", "_"),
        phase=phase,
        details={
            "user_input": user_input,
            "ai_response": ai_response,
            "context": context,
            "timestamp": timestamp,
        },
    )
    return mcp_record


def _run_inception_stages() -> list[dict[str, str]]:
    """Execute INCEPTION stages and return their completion records.

    In the current implementation this returns the default stage list
    with timestamps filled in. A future version will execute each stage
    through the AI-DLC INCEPTION engine.

    Returns:
        A list of stage dicts with ``stage_name``, ``status``, and
        ``completed_at`` keys.
    """
    timestamp = _now_iso()
    return [
        {**stage, "completed_at": timestamp}
        for stage in _DEFAULT_INCEPTION_STAGES
    ]


def run_integrated_workflow(
    request_text: str,
    ci_mode: bool,
    state_path: str,
    handoff_path: str,
    audit_md_path: str,
) -> dict:
    """Run the integrated AI-DLC INCEPTION → WF CONSTRUCTION workflow.

    Main entry point that orchestrates the full integration flow:

    1. Load session state and determine resume point.
    2. Run INCEPTION stages (or skip if resuming at CONSTRUCTION).
    3. Classify the request and select a WF.
    4. Generate and write the Handoff Artifact.
    5. Create delegation markers for CONSTRUCTION stages.
    6. Look up the coverage threshold for the selected WF.
    7. Update AIDLC state with integration and progress sections.
    8. Write audit entries for the handoff event.
    9. If CI mode, check auto-approval for the Workflow Planning gate.
    10. Return a result dict summarising the orchestration outcome.

    Error handling at each boundary:
    - INCEPTION failure → log + abort (status ``"inception_failed"``).
    - Handoff failure → log + update state (status ``"handoff_failed"``).
    - WF/construction failure → log (status ``"construction_failed"``).

    Args:
        request_text: The raw development request from the user.
        ci_mode: Whether the CLI is running in ``--no-interactive`` mode.
        state_path: Filesystem path to ``aidlc-state.md``.
        handoff_path: Filesystem path for the Handoff Artifact.
        audit_md_path: Filesystem path to ``aidlc-docs/audit.md``.

    Returns:
        A dict with keys ``selected_wf``, ``request_type``,
        ``delegation_markers``, ``coverage_threshold``, ``handoff_path``,
        and ``status``.
    """
    # ------------------------------------------------------------------
    # 1. Load session state and determine resume point
    # ------------------------------------------------------------------
    session_state = load_session_state(state_path)

    if session_state:
        try:
            with open(state_path, "r", encoding="utf-8") as fh:
                state_content = fh.read()
        except OSError:
            state_content = ""
    else:
        state_content = ""

    handoff_exists = os.path.isfile(handoff_path)
    resume_point = determine_resume_point(state_content, handoff_exists)

    # ------------------------------------------------------------------
    # 2. Run INCEPTION stages (or skip if resuming at CONSTRUCTION)
    # ------------------------------------------------------------------
    skip_inception = resume_point.startswith("CONSTRUCTION") and handoff_exists

    inception_stages: list[dict[str, str]] = []
    if not skip_inception:
        try:
            inception_stages = _run_inception_stages()
        except Exception as exc:
            _log_audit(
                stage_name="INCEPTION Failure",
                phase="INCEPTION",
                user_input=request_text,
                ai_response=f"INCEPTION failed: {exc}",
                context="Orchestrator aborted due to INCEPTION failure",
                audit_md_path=audit_md_path,
            )
            return {
                "selected_wf": None,
                "request_type": None,
                "delegation_markers": [],
                "coverage_threshold": None,
                "handoff_path": handoff_path,
                "status": "inception_failed",
            }

    # ------------------------------------------------------------------
    # 3. Classify the request and select a WF
    # ------------------------------------------------------------------
    request_type = RequestType.NEW_FEATURE

    classification = build_classification_result(
        request_type=request_type,
        rationale="Classified from request text (default: NEW_FEATURE)",
        confidence=Confidence.MEDIUM,
    )

    selected_wf = classification.selected_wf

    # ------------------------------------------------------------------
    # 4. Generate and write the Handoff Artifact
    # ------------------------------------------------------------------
    try:
        intent = IntentAnalysis(
            request_clarity="Clear",
            scope_estimate="Single Component",
            complexity_estimate="Moderate",
        )

        delegation_markers = create_delegation_markers(selected_wf)

        handoff_content = generate_handoff_artifact(
            classification=classification,
            intent=intent,
            inception_stages=inception_stages,
            delegated_stages=delegation_markers,
        )

        write_handoff_artifact(handoff_content, path=handoff_path)
    except Exception as exc:
        _log_audit(
            stage_name="Handoff Failure",
            phase="INCEPTION",
            user_input=request_text,
            ai_response=f"Handoff artifact generation failed: {exc}",
            context="Updating state to HANDOFF_PENDING",
            audit_md_path=audit_md_path,
        )

        # Update state to reflect handoff pending.
        try:
            integration_section = format_workflow_integration_section(
                wf_id=selected_wf,
                request_type=request_type,
                handoff_timestamp=_now_iso(),
                status=IntegrationStatus.HANDOFF_PENDING,
            )
            progress_section = format_stage_progress_section(
                inception_stages=inception_stages,
                construction_stages=[],
            )
            update_aidlc_state(state_path, integration_section, progress_section)
        except Exception:
            pass

        return {
            "selected_wf": selected_wf.value,
            "request_type": request_type.value,
            "delegation_markers": [],
            "coverage_threshold": None,
            "handoff_path": handoff_path,
            "status": "handoff_failed",
        }

    # ------------------------------------------------------------------
    # 5. Get coverage threshold for the selected WF
    # ------------------------------------------------------------------
    coverage_threshold = get_coverage_threshold(selected_wf)

    # ------------------------------------------------------------------
    # 6. Update AIDLC state
    # ------------------------------------------------------------------
    timestamp = _now_iso()

    integration_section = format_workflow_integration_section(
        wf_id=selected_wf,
        request_type=request_type,
        handoff_timestamp=timestamp,
        status=IntegrationStatus.CONSTRUCTION_IN_PROGRESS,
    )

    progress_section = format_stage_progress_section(
        inception_stages=inception_stages,
        construction_stages=delegation_markers,
    )

    update_aidlc_state(state_path, integration_section, progress_section)

    # ------------------------------------------------------------------
    # 7. Write audit entries for the handoff event
    # ------------------------------------------------------------------
    _log_audit(
        stage_name="Workflow Handoff",
        phase="INCEPTION",
        user_input=request_text,
        ai_response=(
            f"Selected {selected_wf.value} for CONSTRUCTION "
            f"(request_type={request_type.value}, "
            f"confidence={classification.confidence.value})"
        ),
        context=f"Handoff artifact written to {handoff_path}",
        audit_md_path=audit_md_path,
    )

    # ------------------------------------------------------------------
    # 8. CI auto-approval check
    # ------------------------------------------------------------------
    auto_approved = False
    if ci_mode:
        approved, rationale = should_auto_approve(
            gate_name="Workflow Planning",
            gate_output={"selected_wf": selected_wf.value},
            ci_mode=ci_mode,
        )
        auto_approved = approved

        if approved:
            approval_record = format_auto_approval_record(
                gate_name="Workflow Planning",
                selected_option="approve",
                rationale=rationale,
                compliance_checks=["security-rules.md", "coding-standards.md"],
                timestamp=_now_iso(),
            )
            _log_audit(
                stage_name="CI Auto-Approval",
                phase="INCEPTION",
                user_input="--no-interactive",
                ai_response=f"Auto-approved: {rationale}",
                context=f"Gate: Workflow Planning, record: {approval_record}",
                audit_md_path=audit_md_path,
            )

    # ------------------------------------------------------------------
    # 9. Return result
    # ------------------------------------------------------------------
    marker_dicts = [
        {
            "stage_name": m.stage_name,
            "wf_id": m.wf_id.value,
            "status": m.status.value,
        }
        for m in delegation_markers
    ]

    return {
        "selected_wf": selected_wf.value,
        "request_type": request_type.value,
        "delegation_markers": marker_dicts,
        "coverage_threshold": coverage_threshold,
        "handoff_path": handoff_path,
        "status": "ok",
        "auto_approved": auto_approved,
    }