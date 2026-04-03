"""Delegation Marker Manager for AI-DLC Workflow Integration.

Manages the creation, tracking, and lifecycle of delegation markers that
indicate which AI-DLC CONSTRUCTION stages are handled by the selected
WF1-WF5 workflow rather than by AI-DLC directly.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 3.5, 3.6
"""

from src.workflows.integration.models import DelegationMarker, StageStatus, WorkflowId

# Mapping of each workflow to the CONSTRUCTION stages it handles.
# These stages are delegated to the WF and skipped by AI-DLC.
_DELEGATION_MAP: dict[WorkflowId, list[str]] = {
    WorkflowId.WF1: [
        "Functional Design",
        "NFR Requirements",
        "NFR Design",
        "Infrastructure Design",
        "Code Generation",
    ],
    WorkflowId.WF2: [
        "Code Generation",
        "Build and Test",
    ],
    WorkflowId.WF3: [
        "Code Generation",
        "Build and Test",
    ],
    WorkflowId.WF4: [
        "Code Generation",
        "Build and Test",
    ],
    WorkflowId.WF5: [
        "Code Generation",
    ],
}


def get_delegated_stages(wf_id: WorkflowId) -> list[str]:
    """Return the CONSTRUCTION stages delegated to the given workflow.

    Each workflow handles a specific set of CONSTRUCTION stages. This
    function returns that set so AI-DLC knows which stages to skip.

    Args:
        wf_id: The selected workflow identifier.

    Returns:
        A list of stage name strings delegated to the workflow.
    """
    return list(_DELEGATION_MAP[wf_id])


def create_delegation_markers(wf_id: WorkflowId) -> list[DelegationMarker]:
    """Create delegation markers for all stages delegated to a workflow.

    Each marker is initialised with DELEGATED status, indicating the
    stage is owned by the selected WF and should be skipped by AI-DLC.

    Args:
        wf_id: The selected workflow identifier.

    Returns:
        A list of DelegationMarker instances, one per delegated stage.
    """
    return [
        DelegationMarker(stage_name=stage, wf_id=wf_id, status=StageStatus.DELEGATED)
        for stage in get_delegated_stages(wf_id)
    ]


def complete_delegation(marker: DelegationMarker) -> DelegationMarker:
    """Transition a delegation marker from DELEGATED to COMPLETED.

    Called when the selected WF finishes executing a delegated stage.
    The marker status changes from [D] to [x] in aidlc-state.md terms.

    Args:
        marker: The delegation marker to complete.

    Returns:
        A new DelegationMarker with status set to COMPLETED.

    Raises:
        ValueError: If the marker is not in DELEGATED status.
    """
    if marker.status != StageStatus.DELEGATED:
        raise ValueError(
            f"Cannot complete delegation for stage '{marker.stage_name}': "
            f"expected status DELEGATED, got {marker.status.value}"
        )
    return DelegationMarker(
        stage_name=marker.stage_name,
        wf_id=marker.wf_id,
        status=StageStatus.COMPLETED,
    )


def is_stage_delegated(stage_name: str, markers: list[DelegationMarker]) -> bool:
    """Check whether a CONSTRUCTION stage has a delegation marker.

    Used by AI-DLC to decide whether to skip a stage (because a WF
    is handling it) or execute it directly.

    Args:
        stage_name: The name of the CONSTRUCTION stage to check.
        markers: The list of active delegation markers.

    Returns:
        True if the stage has a delegation marker, False otherwise.
    """
    return any(m.stage_name == stage_name for m in markers)
