"""Core data models for AI-DLC Workflow Integration.

Defines enums and dataclasses used across the integration module for
request classification, workflow selection, delegation tracking, and
state management.

Requirements: 2.1, 2.7, 5.2, 8.1, 10.1–10.5
"""

from dataclasses import dataclass
from enum import Enum


class RequestType(Enum):
    """Classification of a development request.

    Used by the Request Type Classifier to categorize incoming requests
    and map them to the appropriate WF1-WF5 workflow.

    Values:
        NEW_FEATURE: A new capability or feature request.
        ENHANCEMENT: An improvement to existing functionality.
        REFACTORING: Code restructuring without behavior change.
        UPGRADE: Dependency or platform version upgrade.
        MIGRATION: System or data migration.
        BUG_FIX: Defect correction.
        DOCUMENTATION: Documentation creation or update.
    """

    NEW_FEATURE = "New Feature"
    ENHANCEMENT = "Enhancement"
    REFACTORING = "Refactoring"
    UPGRADE = "Upgrade"
    MIGRATION = "Migration"
    BUG_FIX = "Bug Fix"
    DOCUMENTATION = "Documentation"


class WorkflowId(Enum):
    """Identifier for each specialized workflow.

    String values match the workflow identifiers used in CI pipeline
    configuration and Jira project mappings.

    Values:
        WF1: Requirement to Software workflow.
        WF2: Autonomous Refactoring workflow.
        WF3: Dependency Upgrades workflow.
        WF4: Bug Fix workflow.
        WF5: Documentation workflow.
    """

    WF1 = "wf1-requirement-to-software"
    WF2 = "wf2-autonomous-refactoring"
    WF3 = "wf3-dependency-upgrades"
    WF4 = "wf4-bug-fix"
    WF5 = "wf5-documentation"


class Confidence(Enum):
    """Confidence level of the request type classification.

    Indicates how certain the Request Type Classifier is about its
    classification decision.

    Values:
        HIGH: Strong signal from request text and context.
        MEDIUM: Reasonable confidence with some ambiguity.
        LOW: Weak signal; user override likely needed.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StageStatus(Enum):
    """Status of a CONSTRUCTION stage in the integrated workflow.

    Tracks the lifecycle of each stage through delegation and completion.

    Values:
        PENDING: Stage has not started yet.
        DELEGATED: Stage is delegated to a WF for execution.
        COMPLETED: Stage has been completed (by AI-DLC or by a WF).
        SKIPPED: Stage was skipped (not applicable).
    """

    PENDING = "pending"
    DELEGATED = "delegated"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class IntegrationStatus(Enum):
    """Overall status of the integrated AI-DLC + WF workflow.

    Recorded in the 'Workflow Integration' section of aidlc-state.md.

    Values:
        INCEPTION_IN_PROGRESS: INCEPTION phase is currently executing.
        HANDOFF_PENDING: INCEPTION complete, awaiting WF delegation.
        CONSTRUCTION_IN_PROGRESS: CONSTRUCTION delegated to a WF and executing.
        COMPLETE: Integrated workflow has finished.
    """

    INCEPTION_IN_PROGRESS = "INCEPTION in progress"
    HANDOFF_PENDING = "Handoff pending"
    CONSTRUCTION_IN_PROGRESS = "CONSTRUCTION in progress"
    COMPLETE = "Complete"


@dataclass
class DelegationMarker:
    """Tracks delegation of a CONSTRUCTION stage to a specific workflow.

    Used to mark which AI-DLC CONSTRUCTION stages are handled by the
    selected WF rather than by AI-DLC directly. Recorded in aidlc-state.md
    and the Unified Audit Trail.

    Attributes:
        stage_name: Name of the CONSTRUCTION stage (e.g. 'Code Generation').
        wf_id: The workflow this stage is delegated to.
        status: Current status of the delegation.
    """

    stage_name: str
    wf_id: WorkflowId
    status: StageStatus


@dataclass
class ClassificationResult:
    """Result of the Request Type Classifier.

    Produced by Workflow Planning and written into the Handoff Artifact.
    Contains the classification decision, selected workflow, confidence
    level, and the rationale behind the classification.

    Attributes:
        request_type: The classified request type.
        selected_wf: The workflow selected for CONSTRUCTION.
        confidence: Confidence level of the classification.
        rationale: Free-text explanation of the classification reasoning.
    """

    request_type: RequestType
    selected_wf: WorkflowId
    confidence: Confidence
    rationale: str


@dataclass
class IntentAnalysis:
    """Summary of the intent analysis from INCEPTION Requirements Analysis.

    Captures key dimensions of the user request that inform workflow
    selection and handoff artifact generation.

    Attributes:
        request_clarity: Clarity of the request ('Clear', 'Vague', 'Incomplete').
        scope_estimate: Estimated scope of the change
            ('Single File', 'Single Component', 'Multiple Components',
             'System-wide', 'Cross-system').
        complexity_estimate: Estimated complexity
            ('Trivial', 'Simple', 'Moderate', 'Complex').
    """

    request_clarity: str
    scope_estimate: str
    complexity_estimate: str
