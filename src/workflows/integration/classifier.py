"""Request Type Classifier for AI-DLC Workflow Integration.

Maps development request types to the appropriate WF1–WF5 workflow
for CONSTRUCTION delegation. Provides a pure mapping function and a
builder for ClassificationResult instances.

Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
"""

from src.workflows.integration.models import (
    ClassificationResult,
    Confidence,
    RequestType,
    WorkflowId,
)

# Canonical mapping from RequestType to WorkflowId.
_REQUEST_TYPE_TO_WF: dict[RequestType, WorkflowId] = {
    RequestType.NEW_FEATURE: WorkflowId.WF1,
    RequestType.ENHANCEMENT: WorkflowId.WF1,
    RequestType.REFACTORING: WorkflowId.WF2,
    RequestType.UPGRADE: WorkflowId.WF3,
    RequestType.MIGRATION: WorkflowId.WF3,
    RequestType.BUG_FIX: WorkflowId.WF4,
    RequestType.DOCUMENTATION: WorkflowId.WF5,
}


def classify_request(request_type: RequestType) -> WorkflowId:
    """Map a request type to the corresponding workflow identifier.

    Pure mapping function implementing the classification rules defined
    in the design document:
        - NEW_FEATURE / ENHANCEMENT → WF1
        - REFACTORING → WF2
        - UPGRADE / MIGRATION → WF3
        - BUG_FIX → WF4
        - DOCUMENTATION → WF5

    Args:
        request_type: The classified request type.

    Returns:
        The WorkflowId for the workflow that should handle CONSTRUCTION.

    Raises:
        KeyError: If request_type is not a valid RequestType member.
    """
    return _REQUEST_TYPE_TO_WF[request_type]


def build_classification_result(
    request_type: RequestType,
    rationale: str,
    confidence: Confidence,
) -> ClassificationResult:
    """Build a ClassificationResult by classifying the request type internally.

    Calls ``classify_request`` to determine the selected workflow, then
    assembles a full ClassificationResult dataclass instance containing
    the request type, selected workflow, confidence level, and rationale.

    Args:
        request_type: The classified request type.
        rationale: Free-text explanation of the classification reasoning.
        confidence: Confidence level of the classification decision.

    Returns:
        A ClassificationResult with the selected_wf populated from the
        classification mapping.
    """
    selected_wf = classify_request(request_type)
    return ClassificationResult(
        request_type=request_type,
        selected_wf=selected_wf,
        confidence=confidence,
        rationale=rationale,
    )
