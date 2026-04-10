---
name: wf4-bug-fix
description: Investigates bug reports, identifies root causes, generates fixes, and creates regression tests. Use for autonomous bug investigation and resolution.
metadata:
  author: sdlc-prototype-team
  version: "1.0.0"
---

# Bug Fix Workflow

This workflow takes a bug report or failing test reference and a target module, then performs root cause analysis, generates a fix, creates regression tests, validates the fix with side-effect analysis, and logs every step for audit traceability. It ensures the fix resolves the defect without introducing new issues.

## MANDATORY: Rule Details Loading

At workflow start, load the following from `.kiro/aws-aidlc-rule-details/`:

**Common rules** (always load):
- `common/verbosity-mode.md` — read `## Verbosity Mode` from `aidlc-docs/aidlc-state.md` and apply silent/debug output rules throughout this workflow
- `common/error-handling.md` — apply error severity levels, recovery procedures, and escalation guidelines
- `common/overconfidence-prevention.md` — default to asking clarifying questions during root cause analysis; never assume the root cause without evidence
- `common/content-validation.md` — validate all generated content before writing files
- `common/depth-levels.md` — adapt artifact detail level to bug complexity and scope

**Construction rules** (load when executing the relevant stage):
- `construction/code-generation.md` — apply code location rules, brownfield file modification rules (modify in-place, never create copies), and automation-friendly code rules when generating the fix and regression tests
- `construction/build-and-test.md` — apply test strategy and summary structure for post-fix validation

**Extensions** (check enabled status in `aidlc-docs/aidlc-state.md` under `## Extension Configuration`):
- `extensions/security/baseline/security-baseline.md` — if Security Baseline is **Enabled**, enforce all SECURITY rules as blocking constraints during fix generation and security scan steps; pay particular attention to SECURITY-05 (input validation), SECURITY-08 (access control), and SECURITY-15 (exception handling) as common bug root causes; if **Disabled**, skip

## Workflow Steps

1. **Start Workflow** — Generate a `workflow_id` using the pattern `wf4-{issue-key-or-short-description}` (e.g. `wf4-login-null-pointer`). Log workflow start immediately via audit-logger MCP: `log_event` with `event_type: "workflow_start"`, including the bug report and target module in `details`. Record this `workflow_id` — it must be used consistently for every subsequent audit-logger and finops call in this workflow.

   **MANDATORY**: This MCP call MUST succeed before proceeding. Do NOT substitute writing to `aidlc-docs/audit.md`.

2. **Root Cause Analysis** — Accept a bug report or failing test reference and target module path as input. Investigate the defect by:
   - Reproducing the bug or confirming the failing test
   - Tracing execution paths to identify the source of the defect
   - Analyzing stack traces, error messages, and relevant code paths
   - Identifying the root cause (logic error, missing validation, race condition, incorrect state, etc.)
   - Documenting the root cause with supporting evidence
   - Log the analysis via audit-logger MCP: `log_interaction`
   - See `references/root-cause-analysis.md` for detailed methodology

3. **Create Restore Point** — Before making any changes, use git-rollback MCP: `create_restore_point` to snapshot the current state. Record the `restore_point_id` for potential rollback. Log via audit-logger MCP: `log_event`.

4. **Generate Fix** — Produce a code fix addressing the identified root cause:
   - Apply the minimal change necessary to resolve the defect
   - Preserve existing behavior for all non-buggy code paths
   - Follow language-specific coding standards and project conventions
   - Add inline comments explaining the fix rationale where appropriate
   - Log the fix via audit-logger MCP: `log_interaction`

5. **Generate Regression Tests** — Create tests that verify the fix and prevent recurrence:
   - Write test(s) that reproduce the original bug (must fail without the fix)
   - Write test(s) that verify the fix resolves the defect (must pass with the fix)
   - Write test(s) covering edge cases related to the root cause
   - Ensure regression tests are deterministic and isolated
   - Python: pytest, Java: JUnit 5, Node JS: Jest
   - Log test creation via audit-logger MCP: `log_interaction`

6. **Run Full Test Suite** — Execute all tests (existing + new regression tests) against the fixed code:
   - Python: `pytest --cov --cov-fail-under=90`
   - Java: `mvn test` with JaCoCo coverage (90% minimum)
   - Node JS: `npm test -- --coverage` (90% minimum)
   - Verify all existing tests still pass (zero regressions)
   - Verify all new regression tests pass
   - Verify minimum 90% line coverage on fix and regression tests
   - Log result via audit-logger MCP: `log_checkpoint`

7. **Side-Effect Analysis** — Verify the fix does not introduce new defects:
   - Identify all callers and dependents of the modified code
   - Run integration tests covering affected code paths
   - Check for changes in error handling, return types, or API contracts
   - Verify no new warnings or deprecation notices introduced
   - Run the validation script: `scripts/validate_fix.py`
   - Log result via audit-logger MCP: `log_checkpoint`

8. **Security Scan** — Run security analysis on all modified files:
   - Use security-scanner MCP: `scan_code` on all modified files
   - Verify no new HIGH or CRITICAL vulnerabilities introduced by the fix
   - Log result via audit-logger MCP: `log_checkpoint`

9. **Fix Validation Checkpoint** — Final validation gate before accepting the fix:
   - All existing tests pass (zero regressions)
   - All regression tests pass
   - Test coverage meets 90% minimum on fix and regression tests
   - Side-effect analysis shows no new defects
   - Security scan shows no new vulnerabilities
   - If validation passes, accept the fix
   - If validation fails, HALT and report failure
   - Log result via audit-logger MCP: `log_checkpoint`

10. **Generate Documentation** — Invoke the shared `generate-documentation` skill to produce documentation artifacts for the bug fix:
   - Release notes (`docs/release-notes-{ISSUE_KEY}.md`) with root cause summary and fix description
   - API changelog entry (append to `docs/CHANGELOG.md`) if endpoint behavior changed
   - OpenAPI spec (`docs/openapi.yaml`) update if response codes or schemas changed
   - Architecture diagram (`docs/architecture.md`)
   - See `skill://.kiro/skills/shared-skills/generate-documentation/SKILL.md` for full details

11. **Audit Log** — Record the complete workflow execution summary via audit-logger MCP: `log_event` with event_type `workflow_end`, including root cause analysis, fix description, regression test results, side-effect analysis, all checkpoint results, and output artifacts.

    **MANDATORY**: This MCP call MUST succeed. Do NOT skip it or substitute writing to `aidlc-docs/audit.md`.

12. **Cost Report** — After logging `workflow_end`, call finops-cost-estimator MCP: `calculate_workflow_cost` using the active `workflow_id`. Then log the cost result back to the audit trail via audit-logger MCP: `log_event` with `event_type: "cost_report"`. Include the full cost breakdown table in the final response to the user per the format defined in `finops-cost-reporting.md`.

    **MANDATORY**: Both MCP calls MUST be made. Call `calculate_workflow_cost` even if the cost is zero.

## Checkpoints (MUST pass before proceeding)

- [ ] **Existing Tests**: All pre-existing unit tests pass after the fix (zero regressions)
- [ ] **Regression Tests**: All new regression tests pass, confirming the fix resolves the defect
- [ ] **Test Coverage**: Minimum 90% line coverage on fix and regression tests
- [ ] **Side-Effect Analysis**: No new defects introduced by the fix
- [ ] **Security Scan**: No new HIGH or CRITICAL vulnerabilities introduced

## If Any Checkpoint Fails

STOP. Do NOT proceed. Report failure details including:
- Which checkpoint failed
- Specific failure reasons and validation details
- Test failures, coverage gaps, or side effects detected
- Root cause analysis summary for context
- Suggested remediation steps

Use git-rollback MCP: `rollback` to restore the previous state using the saved `restore_point_id`.
Log the failure via audit-logger MCP: `log_checkpoint` with `passed: false`.

## Expected Inputs

- Bug report description or failing test reference (e.g., `test_user_login_fails_with_special_chars`)
- Target module path (e.g., `sample-app/python-module/src/auth.py`)

## Expected Outputs

- Code fix addressing the identified root cause
- Regression tests verifying the fix and preventing recurrence
- Side-effect analysis report
- Root cause analysis documentation
- Generated documentation artifacts (release notes, API changelog, OpenAPI spec, architecture diagram)
- Audit trail of all interactions, checkpoints, and decisions

## MCP Server Dependencies

- **audit-logger**: `log_interaction`, `log_checkpoint`, `log_event`
- **security-scanner**: `scan_code`
- **git-rollback**: `create_restore_point`, `rollback`
- **finops-cost-estimator**: `calculate_workflow_cost`
