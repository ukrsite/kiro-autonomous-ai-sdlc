# Implementation Plan: Jira-GitLab-Kiro Integration

## Overview

This plan implements the simplified 4-stage Jira-GitLab-Kiro integration pipeline. The new design eliminates the custom `scripts/wf1_pipeline/` Python module and 9-stage pipeline, replacing them with a workflow-agnostic `.gitlab-ci-workflow.yml` that delegates to Kiro CLI MCP calls. Only the `validate` stage uses inline scripting; stages 2–4 are single `kiro-cli chat --no-interactive` invocations. Testable validation logic is extracted into lightweight Python modules under `scripts/validation/` for unit and property-based testing. All tests use pytest + Hypothesis (Python).

## Tasks

- [x] 1. Create validation logic modules for the validate stage
  - [x] 1.1 Create `scripts/validation/__init__.py` and `scripts/validation/config_validator.py`
    - Implement `load_config(path)` — reads YAML, returns parsed dict
    - Implement `validate_config(config)` — checks every project entry has non-empty `repo_path` and `target_branch` (directly or via defaults) and a valid `workflow` identifier
    - Implement `resolve_project(config, project_key)` — merges defaults with project-specific overrides, rejects unmapped keys with descriptive error
    - Define `VALID_WORKFLOWS` list and `COVERAGE_THRESHOLDS` mapping
    - Implement `resolve_coverage_threshold(workflow_id)` — returns threshold for the workflow
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 3.5, 3.6, 3.7, 3.8, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [x] 1.2 Create `scripts/validation/issue_key_validator.py`
    - Implement `validate_issue_key(key)` — returns True iff key matches `^[A-Z][A-Z0-9]+-[0-9]+$`
    - Return descriptive error message on rejection
    - _Requirements: 3.3, 3.4_

  - [x] 1.3 Create `scripts/validation/sanitizer.py`
    - Implement `sanitize_input(text)` — escapes shell metacharacters (`` $ ` \ " ! | ; & ( ) ``), strips HTML tags, truncates inputs exceeding 10,000 characters
    - _Requirements: 8.5_

  - [x] 1.4 Create `scripts/validation/exit_code_handler.py`
    - Implement `classify_exit_code(code)` — returns "success" for 0, "failure" for all non-zero
    - _Requirements: 4.10_

  - [x] 1.5 Create `scripts/validation/branch_naming.py`
    - Implement `generate_branch_name(issue_key, workflow)` — returns `workflow/{workflow}/{issue_key_lower}`, validates issue key format and workflow
    - _Requirements: 6.1, 10.6_

  - [x] 1.6 Create `scripts/validation/merge_request.py`
    - Implement `build_merge_request(issue_key, issue_summary, jira_url, workflow_id, project_config)` — returns dict with title (`{issue_key}: {summary}`), target branch from config, description containing summary, Jira link, and workflow ID
    - _Requirements: 6.4, 6.5_

  - [x] 1.7 Create `scripts/validation/jira_status.py`
    - Implement `determine_transition(success, mr_created)` — success+MR → "In Review", failure → "AI Dev Failed"
    - Implement `build_jira_comment(pipeline_url, outcome_details, mr_url=None)` — comment with pipeline URL and outcome; on success includes MR link
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 1.8 Create `scripts/validation/audit_records.py`
    - Implement `build_workflow_start_record(jira_issue_key, project_key, workflow_id, pipeline_id, trigger_timestamp, initiator)` — returns dict with all required fields, `workflow_run_id` containing issue key
    - Implement `build_workflow_end_record(jira_issue_key, pipeline_id, workflow_id, outcome, duration, branch_name, mr_url)` — returns dict with outcome and artifact references
    - Implement `build_checkpoint_record(jira_issue_key, pipeline_id, checkpoint_name, passed, details, threshold)` — returns dict with checkpoint data
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 1.9 Create `scripts/validation/checkpoint_gates.py`
    - Implement `evaluate_coverage_gate(coverage_percent, threshold)` — pass iff coverage ≥ threshold; null threshold → always pass (skip)
    - Implement `evaluate_security_gate(findings)` — fail iff any finding has severity "HIGH" or "CRITICAL"
    - Implement `evaluate_code_review_gate(review_result)` — fail iff blocking issues > 0
    - _Requirements: 5.9, 5.11, 5.13_

  - [x] 1.10 Create `scripts/validation/pipeline_summary.py`
    - Implement `build_pipeline_summary(pipeline_id, jira_issue_key, project_key, workflow_id, checkpoints, outcome, branch_name=None, mr_url=None)` — returns dict with all required fields; on success includes branch and MR URL
    - _Requirements: 9.5_

- [x] 2. Checkpoint — Ensure all validation modules load and pass basic smoke tests
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Write property-based tests for all 18 correctness properties
  - [ ]* 3.1 Write property tests in `tests/test_config_validation.py` for Properties 1–4
    - **Property 1: Config Validation Completeness** — generate random configs with/without required fields, verify validator accepts iff all entries have non-empty `repo_path`, `target_branch`, and valid `workflow`
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.6**
    - **Property 2: Default Value Application** — generate configs with defaults and partial project entries, verify resolved config contains default values for omitted fields
    - **Validates: Requirements 1.7, 3.7, 3.8**
    - **Property 3: Unmapped Project Key Rejection** — generate configs and random keys not in the projects map, verify rejection with descriptive error
    - **Validates: Requirements 1.5, 3.5, 3.6**
    - **Property 4: Workflow Identifier Validation** — generate random strings, verify accept/reject matches the 5 valid identifiers exactly
    - **Validates: Requirements 1.8, 1.9**

  - [ ]* 3.2 Write property tests in `tests/test_issue_key_validation.py` for Property 5
    - **Property 5: Issue Key Pattern Validation** — generate random strings, verify accept/reject matches regex `^[A-Z][A-Z0-9]+-[0-9]+$`
    - **Validates: Requirements 3.3, 3.4**

  - [ ]* 3.3 Write property tests in `tests/test_exit_code_handler.py` for Property 6
    - **Property 6: Exit Code Classification** — generate random integers, verify 0→success, non-zero→failure
    - **Validates: Requirements 4.10**

  - [ ]* 3.4 Write property tests in `tests/test_threshold_mapping.py` for Property 7
    - **Property 7: Coverage Threshold Mapping** — generate valid workflow IDs, verify correct threshold: WF1=80, WF2=80, WF3=70, WF4=90, WF5=null
    - **Validates: Requirements 5.3, 5.4, 5.5, 5.6, 5.7, 5.8**

  - [ ]* 3.5 Write property tests in `tests/test_checkpoint_gates.py` for Properties 8, 9, 10
    - **Property 8: Coverage Gate Evaluation** — generate random coverage % and thresholds, verify pass iff coverage ≥ threshold; null threshold → always pass
    - **Validates: Requirements 5.9**
    - **Property 9: Security Severity Gate** — generate random finding sets with various severities, verify fail iff any HIGH or CRITICAL
    - **Validates: Requirements 5.11**
    - **Property 10: Code Review Gate** — generate random review results with/without blocking issues, verify fail iff blocking issues > 0
    - **Validates: Requirements 5.13**

  - [ ]* 3.6 Write property tests in `tests/test_branch_naming.py` for Property 11
    - **Property 11: Branch Naming and Isolation** — generate valid issue keys matching `[A-Z][A-Z0-9]+-[0-9]+`, verify branch name = `workflow/{wf}/{key_lower}`
    - **Validates: Requirements 6.1, 10.6**

  - [ ]* 3.7 Write property tests in `tests/test_merge_request.py` for Property 12
    - **Property 12: Merge Request Content Completeness** — generate random issue data and config, verify MR title contains issue key, target branch matches config, description contains summary, Jira link, and workflow ID
    - **Validates: Requirements 6.4, 6.5**

  - [ ]* 3.8 Write property tests in `tests/test_jira_status.py` for Property 13
    - **Property 13: Bidirectional Jira Status Transition** — generate success/failure outcomes, verify success+MR → "In Review", failure → "AI Dev Failed", comment contains pipeline URL
    - **Validates: Requirements 7.1, 7.2, 7.3, 10.2, 10.3**

  - [ ]* 3.9 Write property tests in `tests/test_sanitizer.py` for Property 14
    - **Property 14: Input Sanitization** — generate strings with shell metacharacters, HTML tags, and prompt injection patterns, verify all dangerous characters are escaped or removed
    - **Validates: Requirements 8.5**

  - [ ]* 3.10 Write property tests in `tests/test_audit_logging.py` for Properties 15, 16
    - **Property 15: Audit Record Completeness** — generate random workflow data, verify start/end records contain all required fields and `workflow_run_id` contains Jira issue key
    - **Validates: Requirements 9.1, 9.2, 9.4**
    - **Property 16: Checkpoint Audit Logging** — generate random checkpoint results, verify record contains checkpoint name, pass/fail, details, and threshold
    - **Validates: Requirements 9.3**

  - [ ]* 3.11 Write property tests in `tests/test_pipeline_summary.py` for Properties 17, 18
    - **Property 17: Pipeline Summary Completeness** — generate random pipeline results, verify summary contains issue key, workflow ID, pipeline ID, checkpoints, outcome; on success verify branch and MR URL present
    - **Validates: Requirements 9.5**
    - **Property 18: Pipeline Halt on Failure** — generate stage failure at random positions, verify all subsequent stages are skipped
    - **Validates: Requirements 11.8**

- [ ] 4. Write unit tests for all validation modules
  - [ ]* 4.1 Write unit tests in `tests/test_config_validation.py`
    - Test valid YAML parses correctly, missing file raises error, specific valid/invalid configs
    - Test each of the 5 valid workflow IDs accepted, invalid ID rejected with descriptive error
    - Test threshold mapping: WF1→80, WF2→80, WF3→70, WF4→90, WF5→None
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

  - [ ]* 4.2 Write unit tests in `tests/test_issue_key_validation.py`
    - Test known valid keys ("PROJ-123", "AB-1", "XY99-42"), known invalid keys ("proj-123", "", "123-ABC", "-1", "A-", "A-B")
    - _Requirements: 3.3, 3.4_

  - [ ]* 4.3 Write unit tests in `tests/test_exit_code_handler.py`
    - Test exit code 0 → success, 1 → failure, 137 → failure, negative codes → failure
    - _Requirements: 4.10_

  - [ ]* 4.4 Write unit tests in `tests/test_checkpoint_gates.py`
    - Test coverage: 79.9% → fail, 80.0% → pass, 100% → pass, 0% → fail, null threshold → skip
    - Test security: empty findings → pass, LOW only → pass, one HIGH → fail, one CRITICAL → fail
    - Test code review: 0 blocking → pass, 1+ blocking → fail
    - _Requirements: 5.9, 5.11, 5.13_

  - [ ]* 4.5 Write unit tests in `tests/test_branch_naming.py`
    - Test "PROJ-123" → "workflow/wf1-requirement-to-software/proj-123", invalid key raises error
    - _Requirements: 6.1, 10.6_

  - [ ]* 4.6 Write unit tests in `tests/test_merge_request.py`
    - Test specific issue data produces MR with correct title, description, and target branch
    - _Requirements: 6.4, 6.5_

  - [ ]* 4.7 Write unit tests in `tests/test_jira_status.py`
    - Test success → "In Review", failure → "AI Dev Failed", comment content with/without MR URL
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 4.8 Write unit tests in `tests/test_sanitizer.py`
    - Test known dangerous inputs: `$(rm -rf /)`, `'; DROP TABLE;`, HTML tags, oversized input truncation
    - _Requirements: 8.5_

  - [ ]* 4.9 Write unit tests in `tests/test_audit_logging.py`
    - Test workflow start/end records contain required fields, checkpoint records, workflow_run_id format
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ]* 4.10 Write unit tests in `tests/test_pipeline_summary.py`
    - Test success summary includes branch and MR URL, failure summary includes error, all summaries include per-checkpoint outcomes
    - _Requirements: 9.5_

- [ ] 5. Checkpoint — Ensure all unit and property tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Create the `.gitlab-ci-workflow.yml` pipeline and update `.gitlab-ci.yml`
  - [x] 6.1 Create `.gitlab-ci-workflow.yml` with the 4-stage pipeline (`validate`, `execute-workflow`, `checkpoint-gates`, `finalize`) plus `on-failure` job
    - Add `workflow.rules` to trigger only when `$JIRA_ISSUE_KEY` is present
    - Set `default.timeout` to 30 minutes, `default.image` to `python:3.11`
    - `validate` stage: shell + inline Python script for issue key validation, config lookup, workflow resolution, threshold mapping; writes `validate-output/project-config.json` artifact
    - `execute-workflow` stage: single `kiro-cli chat --no-interactive` invocation wrapped with `scripts/retry-wrapper.sh`; receives workflow ID, issue key, project config
    - `checkpoint-gates` stage: single `kiro-cli chat --no-interactive` invocation for code review, test coverage (workflow-specific threshold), and security scan
    - `finalize` stage: single `kiro-cli chat --no-interactive` invocation for branch creation, MR creation, Jira update, and audit logging
    - `on-failure` job: `when: on_failure`, invokes Kiro CLI to transition Jira to "AI Dev Failed" and log failure to audit
    - Define `needs` and artifact dependencies between stages
    - Reference CI masked variables `JIRA_API_TOKEN` and `GITLAB_TRIGGER_TOKEN`
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 11.10, 4.1, 4.9, 5.1, 5.10, 5.12, 5.14, 6.1, 6.2, 6.3, 6.6, 6.7, 6.8, 6.9, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.6, 9.1, 9.2, 9.3, 9.5, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [x] 6.2 Update `.gitlab-ci.yml` to include `.gitlab-ci-workflow.yml` conditionally (replace old `.gitlab-ci-wf1.yml` include)
    - Change `include` block to reference `.gitlab-ci-workflow.yml` instead of `.gitlab-ci-wf1.yml`
    - Ensure existing stages (lint, test, security, deploy) are not affected
    - _Requirements: 11.9_

  - [ ]* 6.3 Write unit tests in `tests/test_config_validation.py` to verify pipeline YAML structure
    - Test `.gitlab-ci-workflow.yml` defines exactly 4 stages in correct order: `validate`, `execute-workflow`, `checkpoint-gates`, `finalize`
    - Test `workflow.rules` triggers only when `$JIRA_ISSUE_KEY` is present
    - Test `default.timeout` is 30 minutes
    - _Requirements: 11.1, 11.2, 10.5_

- [x] 7. Update `config/jira-project-mappings.yml` to ensure all projects have valid `workflow` field
  - Verify each project entry has a valid `workflow` identifier (directly or via defaults)
  - Ensure the config is compatible with the new validate stage's inline validation logic
  - _Requirements: 1.2, 1.6, 1.8_

- [x] 8. Clean up old pipeline artifacts
  - [x] 8.1 Delete the old `scripts/wf1_pipeline/` directory and all its contents
    - Remove: `__init__.py`, `config_loader.py`, `issue_key_validator.py`, `sanitizer.py`, `prompt_formatter.py`, `exit_code_handler.py`, `branch_naming.py`, `merge_request.py`, `jira_status.py`, `checkpoint_gates.py`, `pipeline_orchestration.py`, `audit_logging.py`, `pipeline_summary.py`, `main.py`
    - _Requirements: 11.10_

  - [x] 8.2 Delete the old `.gitlab-ci-wf1.yml` pipeline file
    - _Requirements: 11.9_

  - [x] 8.3 Update any imports or references in existing test files that point to `scripts.wf1_pipeline.*` to use `scripts.validation.*` instead
    - _Requirements: 11.10_

- [x] 9. Final checkpoint — Ensure all tests pass and pipeline is complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each major component group
- Property tests validate all 18 correctness properties from the design document using Hypothesis
- Unit tests validate specific examples and edge cases
- The new `scripts/validation/` module replaces the old `scripts/wf1_pipeline/` module with lighter, focused validation functions
- The pipeline file `.gitlab-ci-workflow.yml` replaces `.gitlab-ci-wf1.yml` and is workflow-agnostic (supports WF1–WF5)
- All Kiro CLI invocations in stages 2–4 are wrapped with `scripts/retry-wrapper.sh` for retry with exponential backoff
