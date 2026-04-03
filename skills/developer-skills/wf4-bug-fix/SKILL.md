---
name: wf4-bug-fix
description: Investigates bug reports, identifies root causes, generates fixes, and creates regression tests. Use for autonomous bug investigation and resolution.
metadata:
  author: sdlc-prototype-team
  version: "1.0.0"
---

# Bug Fix Workflow

This workflow takes a bug report or failing test reference and a target module, then performs root cause analysis, generates a fix, creates regression tests, validates the fix with side-effect analysis, and logs every step for audit traceability. It ensures the fix resolves the defect without introducing new issues.

## Workflow Steps

1. **Root Cause Analysis** — Accept a bug report or failing test reference and target module path as input. Investigate the defect by:
   - Reproducing the bug or confirming the failing test
   - Tracing execution paths to identify the source of the defect
   - Analyzing stack traces, error messages, and relevant code paths
   - Identifying the root cause (logic error, missing validation, race condition, incorrect state, etc.)
   - Documenting the root cause with supporting evidence
   - Log the analysis via audit-logger MCP: `log_interaction`
   - See `references/root-cause-analysis.md` for detailed methodology

2. **Create Restore Point** — Before making any changes, use git-rollback MCP: `create_restore_point` to snapshot the current state. Record the `restore_point_id` for potential rollback. Log via audit-logger MCP: `log_event`.

3. **Generate Fix** — Produce a code fix addressing the identified root cause:
   - Apply the minimal change necessary to resolve the defect
   - Preserve existing behavior for all non-buggy code paths
   - Follow language-specific coding standards and project conventions
   - Add inline comments explaining the fix rationale where appropriate
   - Log the fix via audit-logger MCP: `log_interaction`

4. **Generate Regression Tests** — Create tests that verify the fix and prevent recurrence:
   - Write test(s) that reproduce the original bug (must fail without the fix)
   - Write test(s) that verify the fix resolves the defect (must pass with the fix)
   - Write test(s) covering edge cases related to the root cause
   - Ensure regression tests are deterministic and isolated
   - Python: pytest, Java: JUnit 5, Node JS: Jest
   - Log test creation via audit-logger MCP: `log_interaction`

5. **Run Full Test Suite** — Execute all tests (existing + new regression tests) against the fixed code:
   - Python: `pytest --cov --cov-fail-under=90`
   - Java: `mvn test` with JaCoCo coverage (90% minimum)
   - Node JS: `npm test -- --coverage` (90% minimum)
   - Verify all existing tests still pass (zero regressions)
   - Verify all new regression tests pass
   - Verify minimum 90% line coverage on fix and regression tests
   - Log result via audit-logger MCP: `log_checkpoint`

6. **Side-Effect Analysis** — Verify the fix does not introduce new defects:
   - Identify all callers and dependents of the modified code
   - Run integration tests covering affected code paths
   - Check for changes in error handling, return types, or API contracts
   - Verify no new warnings or deprecation notices introduced
   - Run the validation script: `scripts/validate_fix.py`
   - Log result via audit-logger MCP: `log_checkpoint`

7. **Security Scan** — Run security analysis on all modified files:
   - Use security-scanner MCP: `scan_code` on all modified files
   - Verify no new HIGH or CRITICAL vulnerabilities introduced by the fix
   - Log result via audit-logger MCP: `log_checkpoint`

8. **Fix Validation Checkpoint** — Final validation gate before accepting the fix:
   - All existing tests pass (zero regressions)
   - All regression tests pass
   - Test coverage meets 90% minimum on fix and regression tests
   - Side-effect analysis shows no new defects
   - Security scan shows no new vulnerabilities
   - If validation passes, accept the fix
   - If validation fails, HALT and report failure
   - Log result via audit-logger MCP: `log_checkpoint`

9. **Audit Log** — Record the complete workflow execution summary via audit-logger MCP: `log_event` with event_type `workflow_end`, including root cause analysis, fix description, regression test results, side-effect analysis, all checkpoint results, and output artifacts.

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
- Audit trail of all interactions, checkpoints, and decisions

## MCP Server Dependencies

- **audit-logger**: `log_interaction`, `log_checkpoint`, `log_event`
- **security-scanner**: `scan_code`
- **git-rollback**: `create_restore_point`, `rollback`
