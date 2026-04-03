"""Coverage threshold lookup for each WF workflow.

Provides the correct test-coverage threshold to pass to
``evaluate_coverage_gate`` in ``scripts/validation/checkpoint_gates.py``
(which is NOT modified by this integration — see Requirement 7.7).

Requirements: 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
"""

from __future__ import annotations

from typing import Optional

from src.workflows.integration.models import WorkflowId

# Mapping of workflow to minimum line-coverage percentage.
# None means the coverage check is skipped entirely (e.g. WF5 docs).
_THRESHOLDS: dict[WorkflowId, Optional[int]] = {
    WorkflowId.WF1: 80,   # Requirement 7.2 — 80% new-code coverage
    WorkflowId.WF2: 80,   # Requirement 7.3 — 80% + pre-existing tests pass
    WorkflowId.WF3: 70,   # Requirement 7.4 — 70% + full suite post-upgrade
    WorkflowId.WF4: 90,   # Requirement 7.5 — 90% on fix & regression tests
    WorkflowId.WF5: None,  # Requirement 7.6 — no coverage check
}


def get_coverage_threshold(wf_id: WorkflowId) -> Optional[int]:
    """Return the coverage threshold for the given workflow.

    The returned value is intended to be passed directly to
    ``evaluate_coverage_gate(coverage_percent, threshold)`` in
    ``scripts/validation/checkpoint_gates.py``.

    Args:
        wf_id: The workflow whose threshold is requested.

    Returns:
        The minimum line-coverage percentage required, or ``None``
        when the coverage gate should be skipped (WF5).
    """
    return _THRESHOLDS[wf_id]
