# Requirements Document

## Introduction

This document defines the requirements for integrating the AI-DLC (Adaptive Development Lifecycle) workflow system with the existing WF1–WF5 project workflows. The integration layers AI-DLC's INCEPTION phase as the unified front-end for all development requests, with AI-DLC's Workflow Planning stage selecting and delegating to the appropriate WF1–WF5 workflow for CONSTRUCTION. This eliminates duplicate requirements/design stages between AI-DLC INCEPTION and WF1, unifies the audit trail across both systems, consolidates checkpoint frameworks, and preserves the specialized WF2–WF5 workflows, the existing GitLab CI pipeline structure, and the Jira integration unchanged.

The integration connects AI-DLC's three-phase lifecycle (INCEPTION → CONSTRUCTION → OPERATIONS) with the five specialized workflows (WF1: Requirement to Software, WF2: Autonomous Refactoring, WF3: Dependency Upgrades, WF4: Bug Fix, WF5: Documentation) through a delegation model. AI-DLC INCEPTION handles workspace detection, reverse engineering, requirements analysis, user stories, and workflow planning. The Workflow Planning stage analyzes the request type and selects the appropriate WF for CONSTRUCTION. AI-DLC CONSTRUCTION stages that overlap with WF capabilities are marked "delegated to WF" rather than executed independently, targeting approximately 60% duplication reduction on WF1 flows.

## Glossary

- **AI_DLC**: The Adaptive Development Lifecycle framework, a 3-phase workflow system (INCEPTION → CONSTRUCTION → OPERATIONS) that provides adaptive depth planning, requirements analysis, and structured approval gates. Rule details are stored in `.kiro/aws-aidlc-rule-details/`.
- **INCEPTION_Phase**: The first phase of AI_DLC, responsible for planning and architecture. Includes stages: Workspace Detection, Reverse Engineering (conditional), Requirements Analysis, User Stories (conditional), Workflow Planning, Application Design (conditional), and Units Generation (conditional).
- **CONSTRUCTION_Phase**: The second phase of AI_DLC, responsible for design, implementation, build and test. In the integrated model, CONSTRUCTION is delegated to the appropriate WF1–WF5 workflow.
- **Workflow_Planning**: The AI_DLC INCEPTION stage that analyzes the user request and selects which WF (WF1–WF5) to delegate CONSTRUCTION to. Produces a workflow execution plan stored in `aidlc-docs/inception/plans/`.
- **WF1_Workflow**: The Requirement to Software workflow. Spec-driven: requirements → design → tasks → implementation. Defined in `.kiro/skills/developer-skills/wf1-requirement-to-software/SKILL.md`.
- **WF2_Workflow**: The Autonomous Refactoring workflow. Behavior equivalence and performance benchmarking. Defined in `.kiro/skills/developer-skills/wf2-autonomous-refactoring/`.
- **WF3_Workflow**: The Dependency Upgrades workflow. Scanning and compatibility checking. Defined in `.kiro/skills/developer-skills/wf3-dependency-upgrades/`.
- **WF4_Workflow**: The Bug Fix workflow. Root cause analysis and side-effect analysis. Defined in `.kiro/skills/developer-skills/wf4-bug-fix/`.
- **WF5_Workflow**: The Documentation generation workflow. Defined in `.kiro/skills/developer-skills/wf5-documentation/`.
- **Request_Type_Classifier**: The component within Workflow_Planning that analyzes the user request to determine which WF to select. Classification categories: New Feature, Bug Fix, Refactoring, Upgrade, Documentation.
- **Delegation_Marker**: A status annotation ("delegated to WF") applied to AI_DLC CONSTRUCTION stages that overlap with WF capabilities, indicating the stage is handled by the selected WF rather than AI_DLC directly.
- **Unified_Audit_Trail**: The combined audit system that writes human-readable entries to `aidlc-docs/audit.md` and machine-readable entries via the Audit_Logger_MCP, covering both AI_DLC and WF execution.
- **Audit_Logger_MCP**: The existing MCP server (`mcp-servers/audit-logger/`) that records machine-readable audit events in NDJSON format to `audit/audit.ndjson`.
- **Checkpoint_Framework**: The existing MCP-based checkpoint system (security-scanner, audit-logger, git-rollback) used by WF1–WF5 and the GitLab CI pipeline for quality gates.
- **AIDLC_State**: The state tracking file at `aidlc-docs/aidlc-state.md` that records phase progress, workspace state, and extension configuration.
- **Handoff_Artifact**: The structured output produced by INCEPTION_Phase and consumed by the selected WF, containing requirements, intent analysis, scope estimates, and workflow selection rationale.
- **CI_Pipeline**: The existing GitLab CI pipeline defined in `.gitlab-ci-workflow.yml` with stages: validate → execute-workflow → checkpoint-gates → finalize.
- **Jira_Integration**: The existing Jira integration via `config/jira-project-mappings.yml` that maps Jira project keys to services, workflows, and branches.

## Requirements

### Requirement 1: AI-DLC INCEPTION as Unified Front-End

**User Story:** As a developer, I want all development requests to flow through AI-DLC INCEPTION before reaching WF1–WF5, so that every request receives consistent workspace analysis, requirements gathering, and intelligent workflow selection regardless of request type.

#### Acceptance Criteria

1. WHEN a development request is received, THE AI_DLC SHALL execute the INCEPTION_Phase stages (Workspace Detection, Reverse Engineering if brownfield, Requirements Analysis) before selecting a WF for CONSTRUCTION.
2. THE Workflow_Planning stage SHALL execute after Requirements Analysis completes and SHALL produce a Handoff_Artifact containing the selected WF identifier, requirements summary, intent analysis, scope estimate, and complexity estimate.
3. THE INCEPTION_Phase SHALL preserve all existing AI_DLC stage behaviors including adaptive depth (minimal/standard/comprehensive) and structured approval gates at each stage.
4. WHEN INCEPTION_Phase completes, THE AI_DLC SHALL store the Handoff_Artifact at `aidlc-docs/inception/plans/workflow-handoff.md` for consumption by the selected WF.
5. THE INCEPTION_Phase SHALL execute identically regardless of which WF is ultimately selected for CONSTRUCTION.

### Requirement 2: Request Type Classification and Workflow Selection

**User Story:** As a developer, I want AI-DLC Workflow Planning to automatically classify my request and select the appropriate WF1–WF5 workflow, so that the correct specialized workflow handles the implementation without manual workflow selection.

#### Acceptance Criteria

1. THE Request_Type_Classifier SHALL analyze the user request, requirements artifacts, and reverse engineering context (if available) to determine the request type.
2. WHEN the Request_Type_Classifier determines the request type is "New Feature" or "Enhancement", THE Workflow_Planning SHALL select WF1_Workflow for CONSTRUCTION.
3. WHEN the Request_Type_Classifier determines the request type is "Refactoring", THE Workflow_Planning SHALL select WF2_Workflow for CONSTRUCTION.
4. WHEN the Request_Type_Classifier determines the request type is "Upgrade" or "Migration", THE Workflow_Planning SHALL select WF3_Workflow for CONSTRUCTION.
5. WHEN the Request_Type_Classifier determines the request type is "Bug Fix", THE Workflow_Planning SHALL select WF4_Workflow for CONSTRUCTION.
6. WHEN the Request_Type_Classifier determines the request type is "Documentation", THE Workflow_Planning SHALL select WF5_Workflow for CONSTRUCTION.
7. THE Workflow_Planning SHALL record the classification rationale, confidence level, and selected WF in the Handoff_Artifact.
8. THE Workflow_Planning SHALL present the selected WF to the user for approval before proceeding to CONSTRUCTION, allowing the user to override the selection.
9. IF the user overrides the WF selection, THEN THE Workflow_Planning SHALL record the override and rationale in the Handoff_Artifact and the Unified_Audit_Trail.

### Requirement 3: WF1 Duplication Elimination

**User Story:** As a developer, I want the duplicate requirements and design stages between AI-DLC INCEPTION and WF1 to be eliminated, so that I do not repeat the same planning work twice when building new features.

#### Acceptance Criteria

1. WHEN WF1_Workflow is selected for CONSTRUCTION, THE WF1_Workflow SHALL skip its own requirements gathering step and consume the requirements from the Handoff_Artifact produced by INCEPTION_Phase.
2. WHEN WF1_Workflow is selected for CONSTRUCTION, THE WF1_Workflow SHALL skip its own Kiro spec `requirements.md` generation and use the INCEPTION_Phase requirements document at `aidlc-docs/inception/requirements/requirements.md` as the authoritative requirements source.
3. THE WF1_Workflow SHALL retain its design generation (`design.md`), task generation (`tasks.md`), and implementation steps, consuming INCEPTION artifacts as input rather than generating requirements from scratch.
4. THE integrated WF1 flow SHALL reduce the total number of duplicated planning stages by approximately 60% compared to running AI_DLC INCEPTION and WF1 independently.
5. THE AIDLC_State SHALL mark the AI_DLC CONSTRUCTION stages that overlap with WF1 (Functional Design, NFR Requirements, NFR Design, Infrastructure Design) with the Delegation_Marker "delegated to WF1".
6. WHEN a CONSTRUCTION stage is marked with a Delegation_Marker, THE AI_DLC SHALL skip execution of that stage and record the delegation in the Unified_Audit_Trail.

### Requirement 4: WF2–WF5 Preservation

**User Story:** As a developer, I want the specialized WF2–WF5 workflows to remain intact and unchanged in their internal behavior, so that refactoring, dependency upgrades, bug fixes, and documentation generation continue to work as designed.

#### Acceptance Criteria

1. THE WF2_Workflow SHALL retain all existing internal stages (behavior equivalence analysis, refactoring execution, performance benchmarking, delta report) without modification.
2. THE WF3_Workflow SHALL retain all existing internal stages (dependency scanning, compatibility checking, upgrade execution, delta report) without modification.
3. THE WF4_Workflow SHALL retain all existing internal stages (root cause analysis, fix implementation, regression testing, side-effect analysis) without modification.
4. THE WF5_Workflow SHALL retain all existing internal stages (codebase analysis, documentation generation, architecture diagrams) without modification.
5. WHEN WF2_Workflow, WF3_Workflow, WF4_Workflow, or WF5_Workflow is selected for CONSTRUCTION, THE selected WF SHALL receive the Handoff_Artifact from INCEPTION_Phase as additional context input without requiring changes to the WF's internal processing logic.
6. THE WF2_Workflow, WF3_Workflow, WF4_Workflow, and WF5_Workflow skill definitions in `.kiro/skills/developer-skills/` SHALL remain unchanged by this integration.

### Requirement 5: Handoff Artifact Structure

**User Story:** As a developer, I want a well-defined handoff artifact between AI-DLC INCEPTION and the selected WF, so that the WF receives all necessary context from INCEPTION without requiring additional user input for information already gathered.

#### Acceptance Criteria

1. THE Handoff_Artifact SHALL be a markdown file stored at `aidlc-docs/inception/plans/workflow-handoff.md`.
2. THE Handoff_Artifact SHALL contain the following sections: selected WF identifier, request type classification with rationale, intent analysis summary (request clarity, request type, scope estimate, complexity estimate), reference path to the full requirements document, list of INCEPTION stages executed with completion timestamps, and list of CONSTRUCTION stages delegated to the selected WF.
3. THE Handoff_Artifact SHALL reference (not duplicate) the full requirements document at `aidlc-docs/inception/requirements/requirements.md`.
4. THE Handoff_Artifact SHALL reference (not duplicate) reverse engineering artifacts in `aidlc-docs/inception/reverse-engineering/` when available.
5. WHEN the selected WF begins execution, THE selected WF SHALL load the Handoff_Artifact and use the referenced artifacts as input context.
6. IF the Handoff_Artifact is missing or incomplete when a WF attempts to load it, THEN THE selected WF SHALL halt execution and report the missing artifact to the user.

### Requirement 6: Unified Audit Trail

**User Story:** As a team lead, I want a single unified audit trail that covers both AI-DLC INCEPTION and WF execution, so that the complete lifecycle of every development request is traceable from initial request through implementation.

#### Acceptance Criteria

1. THE Unified_Audit_Trail SHALL write human-readable audit entries to `aidlc-docs/audit.md` using the existing AI_DLC audit format (timestamp, user input, AI response, context).
2. THE Unified_Audit_Trail SHALL write machine-readable audit entries via the Audit_Logger_MCP to `audit/audit.ndjson` using the existing NDJSON format.
3. WHEN INCEPTION_Phase transitions to CONSTRUCTION via the Handoff_Artifact, THE Unified_Audit_Trail SHALL record a handoff event in both `aidlc-docs/audit.md` and via the Audit_Logger_MCP, including the selected WF identifier, classification rationale, and timestamp.
4. WHEN the selected WF executes checkpoint gates (code review, test coverage, security scan), THE Unified_Audit_Trail SHALL record each checkpoint result in both `aidlc-docs/audit.md` and via the Audit_Logger_MCP.
5. THE Unified_Audit_Trail SHALL maintain chronological ordering across INCEPTION and CONSTRUCTION entries within `aidlc-docs/audit.md`.
6. THE Unified_Audit_Trail SHALL use ISO 8601 timestamp format for all entries.
7. THE Audit_Logger_MCP records SHALL include a `phase` field with value "INCEPTION" or "CONSTRUCTION" to distinguish which phase generated the entry.

### Requirement 7: Consolidated Checkpoint Framework

**User Story:** As a devops engineer, I want a single checkpoint framework that serves both AI-DLC approval gates and WF quality gates, so that checkpoint logic is not duplicated and quality standards are consistently enforced.

#### Acceptance Criteria

1. THE Checkpoint_Framework SHALL use the existing MCP-based checkpoints (security-scanner, audit-logger, git-rollback) for all quality gates across both AI_DLC and WF execution.
2. WHEN WF1_Workflow executes CONSTRUCTION, THE Checkpoint_Framework SHALL apply the WF1 coverage threshold (80% line coverage on new code) as defined in the existing WF1 skill.
3. WHEN WF2_Workflow executes CONSTRUCTION, THE Checkpoint_Framework SHALL apply the WF2 coverage threshold (80% line coverage, all pre-existing tests pass).
4. WHEN WF3_Workflow executes CONSTRUCTION, THE Checkpoint_Framework SHALL apply the WF3 coverage threshold (70% line coverage, full test suite passes post-upgrade).
5. WHEN WF4_Workflow executes CONSTRUCTION, THE Checkpoint_Framework SHALL apply the WF4 coverage threshold (90% coverage on fix and regression tests).
6. WHEN WF5_Workflow executes CONSTRUCTION, THE Checkpoint_Framework SHALL skip the test coverage check.
7. THE Checkpoint_Framework SHALL use the existing `scripts/validation/checkpoint_gates.py` gate evaluators (evaluate_coverage_gate, evaluate_security_gate, evaluate_code_review_gate) without modification.
8. THE AI_DLC structured approval gates during INCEPTION_Phase SHALL remain separate from the Checkpoint_Framework quality gates during CONSTRUCTION, as they serve different purposes (human approval vs. automated quality verification).
9. IF any Checkpoint_Framework gate fails during CONSTRUCTION, THEN THE selected WF SHALL halt execution, log the failure to the Unified_Audit_Trail, and report the failure to the user.

### Requirement 8: AIDLC State Tracking for Integrated Workflow

**User Story:** As a developer, I want the AIDLC state file to accurately reflect the integrated workflow progress including delegation markers, so that I can see which stages were handled by AI-DLC INCEPTION and which were delegated to a WF.

#### Acceptance Criteria

1. THE AIDLC_State SHALL include a "Workflow Integration" section that records the selected WF identifier, the request type classification, and the handoff timestamp.
2. WHEN a CONSTRUCTION stage is delegated to a WF, THE AIDLC_State SHALL mark that stage with the Delegation_Marker format: `[D] Stage Name - delegated to {WF_identifier}`.
3. WHEN the selected WF completes a delegated CONSTRUCTION stage, THE AIDLC_State SHALL update the stage status to `[x] Stage Name - completed by {WF_identifier}`.
4. THE AIDLC_State SHALL track INCEPTION_Phase stages with the existing checkbox format: `[x]` for completed, `[ ]` for pending, `[-]` for skipped.
5. THE AIDLC_State SHALL record the overall integration status as one of: "INCEPTION in progress", "Handoff pending", "CONSTRUCTION in progress via {WF_identifier}", or "Complete".

### Requirement 9: CI Pipeline Compatibility

**User Story:** As a devops engineer, I want the AI-DLC integration to work within the existing GitLab CI pipeline structure without requiring pipeline stage changes, so that the CI/CD infrastructure remains stable and the Jira integration continues to function.

#### Acceptance Criteria

1. THE CI_Pipeline SHALL retain its existing 4-stage structure (validate, execute-workflow, checkpoint-gates, finalize) without modification.
2. THE CI_Pipeline `execute-workflow` stage SHALL invoke the integrated AI_DLC + WF flow through the same `kiro-cli chat --no-interactive` interface used today.
3. THE CI_Pipeline `validate` stage SHALL continue to resolve the Workflow_Identifier from `config/jira-project-mappings.yml` and pass it to the execute-workflow stage.
4. THE Jira_Integration configuration in `config/jira-project-mappings.yml` SHALL remain unchanged in schema and behavior.
5. THE CI_Pipeline `checkpoint-gates` stage SHALL continue to use the existing parallel jobs (java-tests, python-tests, security-scan, review) without modification.
6. THE CI_Pipeline `finalize` stage SHALL continue to push branches, create merge requests, and transition Jira issues using the existing logic.
7. WHEN the CI_Pipeline triggers a workflow execution, THE `execute-workflow` stage prompt SHALL instruct Kiro_CLI to run AI_DLC INCEPTION followed by the resolved WF for CONSTRUCTION, rather than running the WF directly.

### Requirement 10: Delegation Marker Management

**User Story:** As a developer, I want AI-DLC CONSTRUCTION stages that overlap with WF capabilities to be clearly marked as delegated, so that the system does not execute redundant stages and the audit trail shows which system handled each stage.

#### Acceptance Criteria

1. WHEN WF1_Workflow is selected, THE AI_DLC SHALL apply the Delegation_Marker to the following CONSTRUCTION stages: Functional Design, NFR Requirements, NFR Design, Infrastructure Design, and Code Generation.
2. WHEN WF2_Workflow is selected, THE AI_DLC SHALL apply the Delegation_Marker to the following CONSTRUCTION stages: Code Generation and Build and Test.
3. WHEN WF3_Workflow is selected, THE AI_DLC SHALL apply the Delegation_Marker to the following CONSTRUCTION stages: Code Generation and Build and Test.
4. WHEN WF4_Workflow is selected, THE AI_DLC SHALL apply the Delegation_Marker to the following CONSTRUCTION stages: Code Generation and Build and Test.
5. WHEN WF5_Workflow is selected, THE AI_DLC SHALL apply the Delegation_Marker to the following CONSTRUCTION stages: Code Generation.
6. THE Delegation_Marker SHALL be recorded in both the AIDLC_State and the Unified_Audit_Trail at the time of delegation.
7. THE AI_DLC SHALL skip execution of any CONSTRUCTION stage that has a Delegation_Marker applied.

### Requirement 11: Error Handling Across Integration Boundary

**User Story:** As a developer, I want errors during the INCEPTION-to-WF handoff and during delegated CONSTRUCTION to be handled gracefully, so that failures are reported clearly and the system can recover without leaving inconsistent state.

#### Acceptance Criteria

1. IF INCEPTION_Phase fails at any stage before producing the Handoff_Artifact, THEN THE AI_DLC SHALL log the failure to the Unified_Audit_Trail and report the failure to the user without invoking any WF.
2. IF the Handoff_Artifact is produced but the selected WF fails to start, THEN THE AI_DLC SHALL log the handoff failure to the Unified_Audit_Trail, update the AIDLC_State to "Handoff failed", and report the failure to the user.
3. IF the selected WF fails during CONSTRUCTION, THEN THE selected WF SHALL log the failure to the Unified_Audit_Trail, invoke git-rollback MCP to restore the previous state, and update the AIDLC_State to reflect the failure.
4. WHEN a failure occurs during CI_Pipeline execution, THE CI_Pipeline `on-failure` job SHALL continue to transition the Jira issue to "AI Dev Failed" and log the failure using the existing failure handler logic.
5. THE error handling behavior of each individual WF (WF1–WF5) SHALL remain unchanged; the integration SHALL add error handling only at the INCEPTION-to-WF boundary.

### Requirement 12: Session Continuity Across Phases

**User Story:** As a developer, I want to be able to resume an interrupted integrated workflow from the last completed stage, so that I do not lose progress if a session is interrupted between INCEPTION and CONSTRUCTION.

#### Acceptance Criteria

1. WHEN a new session starts, THE AI_DLC SHALL check the AIDLC_State for existing progress and resume from the last incomplete stage.
2. IF the AIDLC_State shows INCEPTION_Phase completed and a Handoff_Artifact exists, THEN THE AI_DLC SHALL resume directly at CONSTRUCTION by loading the Handoff_Artifact and invoking the selected WF.
3. IF the AIDLC_State shows CONSTRUCTION in progress via a specific WF, THEN THE AI_DLC SHALL resume the selected WF from its last checkpoint.
4. THE session continuity mechanism SHALL use the existing AIDLC_State file and the existing AI_DLC session resumption guidance from `common/session-continuity.md`.
5. THE Handoff_Artifact SHALL persist across sessions, enabling CONSTRUCTION to start in a different session than INCEPTION.

### Requirement 13: CI Autonomous Mode with Security-Aware Auto-Approval

**User Story:** As a devops engineer, I want AI-DLC approval gates to auto-approve when running in `--no-interactive` CI mode, selecting the most secure and compliant option at each gate, so that the pipeline runs fully autonomously while adhering to enterprise application security policies and compliance requirements.

#### Acceptance Criteria

1. WHEN kiro-cli is invoked with `--no-interactive` flag (CI mode), THE AI_DLC SHALL detect the non-interactive context and switch all INCEPTION_Phase approval gates to auto-approve mode.
2. WHEN auto-approving at an INCEPTION_Phase gate, THE AI_DLC SHALL select the option that best satisfies enterprise security policies, compliance requirements, and coding standards — defaulting to the most restrictive/comprehensive option when multiple valid choices exist.
3. THE AI_DLC SHALL auto-approve the following INCEPTION gates in CI mode: Requirements Analysis completion, User Stories completion (if executed), Workflow Planning completion (including WF selection), Application Design completion (if executed), and Units Generation completion (if executed).
4. WHEN auto-approving Workflow Planning in CI mode, THE AI_DLC SHALL select the WF identified by the Request_Type_Classifier without user override, and SHALL record the auto-approval decision and rationale in the Unified_Audit_Trail.
5. THE AI_DLC SHALL NOT auto-approve any gate where the output contains unresolved security findings, missing input validation, hardcoded credentials, or violations of the project's security-rules.md or coding-standards.md steering rules.
6. IF an auto-approval gate encounters a blocking compliance issue, THEN THE AI_DLC SHALL halt execution, log the blocking issue to the Unified_Audit_Trail, and fail the CI pipeline with a descriptive error message.
7. THE Unified_Audit_Trail SHALL record every auto-approval decision with the following fields: gate name, selected option, rationale for selection, compliance checks performed, and timestamp.
8. THE auto-approval behavior SHALL only activate when the `--no-interactive` flag is detected; interactive sessions SHALL continue to require explicit human approval at each gate.
9. THE CI_Pipeline `checkpoint-gates` stage (deterministic quality gates: test coverage, security scan, code review) SHALL remain mandatory and SHALL NOT be affected by auto-approval — these gates always execute regardless of interactive or non-interactive mode.
