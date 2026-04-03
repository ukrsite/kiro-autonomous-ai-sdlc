# Implementation Plan: AI-DLC Workflow Integration

## Overview

This plan implements the integration of AI-DLC INCEPTION as the unified front-end with WF1–WF5 as CONSTRUCTION back-end. The implementation is organized into 8 components matching the design: Request Type Classifier, Handoff Artifact Generator, WF1 Artifact Consumer, WF2–WF5 Context Loader, Delegation Marker Manager, Unified Audit Writer, CI Auto-Approval Controller, and Session Continuity Handler. All new code lives in `src/workflows/integration/` with tests in `tests/`. Existing `scripts/validation/checkpoint_gates.py` and WF2–WF5 skill definitions are NOT modified.

## Tasks

- [x] 1. Set up integration module structure and core data models
  - [x] 1.1 Create `src/workflows/integration/__init__.py` with module docstring
    - Create the integration package directory
    - _Requirements: 1.1, 1.2_
  - [x] 1.2 Create `src/workflows/integration/models.py` with core data models
    - Define `RequestType` enum: `NEW_FEATURE`, `ENHANCEMENT`, `REFACTORING`, `UPGRADE`, `MIGRATION`, `BUG_FIX`, `DOCUMENTATION`
    - Define `WorkflowId` enum: `WF1`, `WF2`, `WF3`, `WF4`, `WF5` with string values matching `wf1-requirement-to-software`, etc.
    - Define `Confidence` enum: `HIGH`, `MEDIUM`, `LOW`
    - Define `StageStatus` enum: `PENDING`, `DELEGATED`, `COMPLETED`, `SKIPPED`
    - Define `IntegrationStatus` enum: `INCEPTION_IN_PROGRESS`, `HANDOFF_PENDING`, `CONSTRUCTION_IN_PROGRESS`, `COMPLETE`
    - Define `DelegationMarker` dataclass: `stage_name: str`, `wf_id: WorkflowId`, `status: StageStatus`
    - Define `ClassificationResult` dataclass: `request_type: RequestType`, `selected_wf: WorkflowId`, `confidence: Confidence`, `rationale: str`
    - Define `IntentAnalysis` dataclass: `request_clarity`, `scope_estimate`, `complexity_estimate`
    - _Requirements: 2.1, 2.7, 5.2, 8.1, 10.1–10.5_

- [x] 2. Implement Request Type Classifier
  - [x] 2.1 Create `src/workflows/integration/classifier.py`
    - Implement `classify_request(request_type: RequestType) -> WorkflowId` pure mapping function
    - Mapping: `NEW_FEATURE`/`ENHANCEMENT` → WF1, `REFACTORING` → WF2, `UPGRADE`/`MIGRATION` → WF3, `BUG_FIX` → WF4, `DOCUMENTATION` → WF5
    - Implement `build_classification_result(request_type, rationale, confidence) -> ClassificationResult`
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_
  - [ ]* 2.2 Write property test for Request Type Classifier
    - **Property 1: Request type classification maps to correct WF**
    - **Validates: Requirements 2.2, 2.3, 2.4, 2.5, 2.6**
    - Create `tests/test_request_type_classifier.py`
    - Use `@given(st.sampled_from(RequestType))` to generate random request types
    - Assert each maps to the correct WF per the defined mapping table


- [x] 3. Implement Delegation Marker Manager
  - [x] 3.1 Create `src/workflows/integration/delegation.py`
    - Implement `get_delegated_stages(wf_id: WorkflowId) -> list[str]` returning the correct stage set per WF
    - WF1 → `["Functional Design", "NFR Requirements", "NFR Design", "Infrastructure Design", "Code Generation"]`
    - WF2/WF3/WF4 → `["Code Generation", "Build and Test"]`
    - WF5 → `["Code Generation"]`
    - Implement `create_delegation_markers(wf_id: WorkflowId) -> list[DelegationMarker]`
    - Implement `complete_delegation(marker: DelegationMarker) -> DelegationMarker` transitioning `[D]` → `[x]`
    - Implement `is_stage_delegated(stage_name: str, markers: list[DelegationMarker]) -> bool`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 3.5, 3.6_
  - [ ]* 3.2 Write property test for delegation marker mapping
    - **Property 2: Delegation marker mapping is correct per WF**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**
    - Create `tests/test_delegation_markers.py`
    - Use `@given(st.sampled_from(WorkflowId))` to generate random WF selections
    - Assert `get_delegated_stages(wf)` returns exactly the expected stage set
  - [ ]* 3.3 Write property test for delegated stage skipping
    - **Property 6: Delegated stages are skipped by AI-DLC**
    - **Validates: Requirements 3.6, 10.6, 10.7**
    - Assert `is_stage_delegated` returns True for all delegated stages and False for non-delegated
  - [ ]* 3.4 Write property test for delegation marker lifecycle
    - **Property 10: AIDLC state delegation marker lifecycle**
    - **Validates: Requirements 8.2, 8.3, 8.4**
    - Generate random delegation markers, apply `complete_delegation`, verify `PENDING → DELEGATED → COMPLETED` lifecycle

- [x] 4. Implement Coverage Threshold Lookup
  - [x] 4.1 Create `src/workflows/integration/thresholds.py`
    - Implement `get_coverage_threshold(wf_id: WorkflowId) -> Optional[int]`
    - WF1 → 80, WF2 → 80, WF3 → 70, WF4 → 90, WF5 → None
    - This function is used to pass the correct threshold to the existing `evaluate_coverage_gate` in `scripts/validation/checkpoint_gates.py` (which is NOT modified per Requirement 7.7)
    - _Requirements: 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_
  - [ ]* 4.2 Write property test for coverage thresholds
    - **Property 3: Coverage threshold is correct per WF**
    - **Validates: Requirements 7.2, 7.3, 7.4, 7.5, 7.6**
    - Create `tests/test_coverage_thresholds.py`
    - Use `@given(st.sampled_from(WorkflowId))` to verify each WF maps to the correct threshold
    - Verify `evaluate_coverage_gate` receives the correct threshold value from `get_coverage_threshold`

- [x] 5. Checkpoint - Ensure core mapping logic tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Handoff Artifact Generator
  - [x] 6.1 Create `src/workflows/integration/handoff.py`
    - Implement `generate_handoff_artifact(classification: ClassificationResult, intent: IntentAnalysis, inception_stages: list, delegated_stages: list[DelegationMarker], override: Optional[dict]) -> str` returning markdown content
    - Output must contain all required sections per design data model: Selected Workflow, Intent Analysis Summary, Requirements Reference, Reverse Engineering References, INCEPTION Stages Executed, Delegated CONSTRUCTION Stages, User Override (if applicable)
    - Requirements Reference must be a file path to `aidlc-docs/inception/requirements/requirements.md` (not duplicated content)
    - Reverse Engineering References must be file paths to `aidlc-docs/inception/reverse-engineering/` artifacts (not duplicated content)
    - Implement `write_handoff_artifact(content: str, path: str)` writing to `aidlc-docs/inception/plans/workflow-handoff.md`
    - Implement `parse_handoff_artifact(path: str) -> dict` reading and parsing the handoff artifact
    - Implement `validate_handoff_artifact(parsed: dict) -> tuple[bool, list[str]]` returning validity and list of missing sections
    - _Requirements: 1.2, 1.4, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  - [ ]* 6.2 Write property test for handoff artifact required sections
    - **Property 4: Handoff Artifact contains all required sections**
    - **Validates: Requirements 1.2, 2.7, 5.2**
    - Create `tests/test_handoff_artifact.py`
    - Generate random valid classification results and intent analyses
    - Assert `generate_handoff_artifact` output contains all required sections
  - [ ]* 6.3 Write property test for handoff artifact references
    - **Property 5: Handoff Artifact uses references, not duplicates**
    - **Validates: Requirements 5.3, 5.4**
    - Assert requirements section contains file path reference, not full content
    - Assert reverse engineering section contains file path references, not full content
  - [ ]* 6.4 Write property test for WF2–WF5 handoff artifact loading
    - **Property 18: WF2–WF5 receive Handoff Artifact as context without internal changes**
    - **Validates: Requirements 4.5**
    - Generate random handoff artifacts for WF2–WF5, verify `parse_handoff_artifact` succeeds and returns valid context

- [x] 7. Implement Unified Audit Writer
  - [x] 7.1 Create `src/workflows/integration/audit.py`
    - Implement `format_audit_md_entry(stage_name: str, phase: str, user_input: str, ai_response: str, context: str, timestamp: str) -> str` returning markdown-formatted audit entry
    - Implement `format_audit_mcp_record(workflow_id: str, event_type: str, phase: str, details: dict) -> dict` returning MCP-compatible dict with `phase` field
    - Implement `append_audit_md(entry: str, path: str)` appending to `aidlc-docs/audit.md`
    - Implement `validate_audit_entry(entry: dict) -> bool` checking required fields including `phase` in `("INCEPTION", "CONSTRUCTION")`
    - Implement `validate_chronological_order(entries: list[dict]) -> bool` checking ISO 8601 timestamps are non-decreasing
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_
  - [ ]* 7.2 Write property test for audit dual-write consistency
    - **Property 8: Unified audit dual-write consistency**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.7**
    - Create `tests/test_unified_audit.py`
    - Generate random audit events, verify both `format_audit_md_entry` and `format_audit_mcp_record` produce valid output with matching phase field
  - [ ]* 7.3 Write property test for audit chronological ordering
    - **Property 9: Audit trail chronological ordering**
    - **Validates: Requirements 6.5, 6.6**
    - Generate random sequences of ISO 8601 timestamps in sorted order, verify `validate_chronological_order` returns True
    - Generate random unsorted sequences, verify it returns False
  - [ ]* 7.4 Write property test for user override audit recording
    - **Property 17: User override is recorded in both destinations**
    - **Validates: Requirements 2.9**
    - Generate random override events, verify both audit formats contain original selection, override target, and override rationale
  - [ ]* 7.5 Write property test for auto-approval audit completeness
    - **Property 15: CI auto-approval audit completeness**
    - **Validates: Requirements 13.7**
    - Generate random auto-approval events, verify audit record contains gate name, selected option, rationale, compliance checks, and timestamp

- [x] 8. Checkpoint - Ensure handoff and audit tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement AIDLC State Manager
  - [x] 9.1 Create `src/workflows/integration/state.py`
    - Implement `format_workflow_integration_section(wf_id: WorkflowId, request_type: RequestType, handoff_timestamp: str, status: IntegrationStatus) -> str` returning the "Workflow Integration" markdown section
    - Implement `format_stage_progress_section(inception_stages: list[dict], construction_stages: list[DelegationMarker]) -> str` returning the "Stage Progress" markdown section with `[x]`, `[ ]`, `[-]`, `[D]` markers
    - Implement `parse_integration_status(state_content: str) -> IntegrationStatus` extracting status from existing `aidlc-state.md`
    - Implement `validate_integration_status(status: str) -> bool` checking status is one of the four valid values
    - Implement `update_aidlc_state(state_path: str, integration_section: str, progress_section: str)` appending/updating the new sections in `aidlc-state.md`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  - [ ]* 9.2 Write property test for AIDLC state integration status validity
    - **Property 11: AIDLC state integration status validity**
    - **Validates: Requirements 8.1, 8.5**
    - Create `tests/test_aidlc_state.py`
    - Generate random state files with integration sections, verify `validate_integration_status` accepts only the four valid statuses
    - Verify `format_workflow_integration_section` always produces valid status strings
  - [ ]* 9.3 Write property test for INCEPTION-before-CONSTRUCTION ordering
    - **Property 16: INCEPTION executes before WF selection**
    - **Validates: Requirements 1.1**
    - Generate random stage progress sections, verify no `[D]` markers appear before all required INCEPTION stages show `[x]`

- [x] 10. Implement Session Continuity Handler
  - [x] 10.1 Create `src/workflows/integration/session.py`
    - Implement `determine_resume_point(state_content: str, handoff_exists: bool) -> str` returning the stage to resume from
    - If INCEPTION complete + handoff exists → return `"CONSTRUCTION"`
    - If CONSTRUCTION in progress via WF → return `"CONSTRUCTION:{wf_id}"`
    - If INCEPTION in progress → return `"INCEPTION:{last_incomplete_stage}"`
    - Implement `load_session_state(state_path: str) -> dict` reading `aidlc-state.md` and extracting integration progress
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_
  - [ ]* 10.2 Write property test for session resumption correctness
    - **Property 12: Session resumption correctness**
    - **Validates: Requirements 12.1, 12.2, 12.3**
    - Create `tests/test_session_continuity.py`
    - Generate random state files with various progress levels, verify `determine_resume_point` returns the correct resume target

- [x] 11. Implement CI Auto-Approval Controller
  - [x] 11.1 Create `src/workflows/integration/ci_approval.py`
    - Implement `is_ci_mode(args: list[str]) -> bool` detecting `--no-interactive` flag
    - Implement `should_auto_approve(gate_name: str, gate_output: dict, ci_mode: bool) -> tuple[bool, str]` returning (approved, rationale)
    - Auto-approve INCEPTION gates (Requirements Analysis, User Stories, Workflow Planning, Application Design, Units Generation) only in CI mode
    - Never auto-approve checkpoint gates (test coverage, security scan, code review) — these always execute
    - Block auto-approval if gate output contains: unresolved security findings, missing input validation, hardcoded credentials, or violations of security-rules.md/coding-standards.md
    - Implement `format_auto_approval_record(gate_name: str, selected_option: str, rationale: str, compliance_checks: list[str], timestamp: str) -> dict` returning audit-compatible record
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9_
  - [ ]* 11.2 Write property test for CI auto-approval mode activation
    - **Property 13: CI auto-approval mode activation**
    - **Validates: Requirements 13.1, 13.8, 13.9**
    - Create `tests/test_ci_auto_approval.py`
    - Generate random arg lists with/without `--no-interactive`, verify `is_ci_mode` returns correct boolean
    - Verify checkpoint gates are never auto-approved regardless of mode
  - [ ]* 11.3 Write property test for auto-approval security blocking
    - **Property 14: CI auto-approval blocks on security violations**
    - **Validates: Requirements 13.5**
    - Generate random gate outputs containing security violations, verify `should_auto_approve` returns `(False, ...)`

- [x] 12. Checkpoint - Ensure state, session, and CI approval tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Modify WF1 SKILL.md to consume Handoff Artifact
  - [x] 13.1 Update `.kiro/skills/developer-skills/wf1-requirement-to-software/SKILL.md`
    - Add conditional logic to Step 1 (Parse Requirement): if `aidlc-docs/inception/plans/workflow-handoff.md` exists, load requirements from the Handoff Artifact reference path instead of raw user input
    - Add conditional logic to Step 2 (Create Kiro Spec): if Handoff Artifact exists, skip `requirements.md` generation and use `aidlc-docs/inception/requirements/requirements.md` as the authoritative source
    - Steps 3–10 remain unchanged
    - Do NOT modify WF2–WF5 skill definitions (Requirement 4.6)
    - _Requirements: 3.1, 3.2, 3.3, 4.6_
  - [ ]* 13.2 Write property test for WF1 handoff artifact consumption
    - **Property 7: WF1 skips requirements gathering when Handoff Artifact exists**
    - **Validates: Requirements 3.1, 3.2**
    - Add test to `tests/test_handoff_artifact.py`
    - Generate random valid handoff artifacts, verify WF1 entry point logic detects the artifact and returns skip-requirements signal

- [x] 14. Update CI pipeline execute-workflow prompt
  - [x] 14.1 Update `.gitlab-ci-workflow.yml` execute-workflow stage prompt
    - Change the `kiro-cli chat --no-interactive -a` prompt to instruct Kiro CLI to run AI-DLC INCEPTION first, then delegate CONSTRUCTION to the selected WF (default: `${WORKFLOW}`)
    - Preserve all existing prompt content (audit logging, documentation generation, artifact saving)
    - The `validate` stage still resolves the workflow from `config/jira-project-mappings.yml` and passes it as a hint
    - Do NOT modify any other CI pipeline stages (validate, checkpoint-gates, finalize, on-failure)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

- [x] 15. Create Handoff Artifact template
  - [x] 15.1 Create `aidlc-docs/inception/plans/workflow-handoff.md` template
    - Create the template file matching the design data model structure
    - Include all required sections with placeholder values
    - This template is used by `generate_handoff_artifact` as the output format reference
    - _Requirements: 5.1, 5.2_

- [x] 16. Wire integration orchestrator
  - [x] 16.1 Create `src/workflows/integration/orchestrator.py`
    - Implement `run_integrated_workflow(request_text: str, ci_mode: bool, state_path: str, handoff_path: str, audit_md_path: str) -> dict` as the main entry point
    - Orchestrate: check session state → run INCEPTION (or resume) → classify request → generate handoff artifact → apply delegation markers → update AIDLC state → write audit entries → delegate to selected WF
    - Handle error cases: INCEPTION failure (log + abort), handoff failure (log + update state), WF failure (log + rollback)
    - Wire all components: classifier, delegation, thresholds, handoff, audit, state, session, ci_approval
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 11.1, 11.2, 11.3, 11.4, 11.5_
  - [ ]* 16.2 Write integration tests for orchestrator
    - Test end-to-end flow: request → INCEPTION → handoff → WF delegation
    - Test error handling at each boundary
    - Test session resumption through orchestrator
    - _Requirements: 1.1, 11.1, 11.2, 11.3, 12.1_

- [x] 17. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (18 properties across 8 test files)
- Unit tests validate specific examples and edge cases
- `scripts/validation/checkpoint_gates.py` is NOT modified (Requirement 7.7)
- WF2–WF5 skill definitions are NOT modified (Requirement 4.6)
- All new source code goes in `src/workflows/integration/`
- All new tests go in `tests/` following existing naming convention
- Python with Hypothesis is used for all property-based tests (already in `requirements-dev.txt`)
