# Checkpoint Enforcement

## Checkpoint Pipeline

All AI-generated code must pass through the following ordered checkpoint pipeline before merge. Each checkpoint must pass before proceeding to the next. If any checkpoint fails, the workflow halts immediately.

### Pipeline Order

1. **Code Review Checkpoint**
2. **Security Scan Checkpoint**
3. **Test Coverage Checkpoint**
4. **Merge**

## Checkpoint 1: Code Review

- All AI-generated code must be reviewed for correctness, adherence to project conventions, and absence of security issues.
- The review must be completed and recorded before proceeding to the security scan.
- Log the review result via audit-logger MCP `log_checkpoint` tool with `checkpoint_id: "code_review"`.

## Checkpoint 2: Security Scan

- Run security-scanner MCP `scan_code` tool on all modified files.
- Run security-scanner MCP `scan_dependencies` tool on the target project.
- If any HIGH or CRITICAL vulnerabilities are found, this checkpoint FAILS.
- Log the scan result via audit-logger MCP `log_checkpoint` tool with `checkpoint_id: "security_scan"`.

## Checkpoint 3: Test Coverage

- Execute the full test suite against the modified code.
- Measure line coverage on new and modified code.
- Validate coverage meets the minimum threshold for the active workflow:
  - WF1 (Requirement to Software): 80% line coverage
  - WF2 (Autonomous Refactoring): 80% line coverage; all pre-existing tests must pass
  - WF3 (Dependency Upgrades): 70% line coverage; full test suite must pass
  - WF4 (Bug Fix): 90% coverage on fix and regression tests
  - WF5 (Documentation): No code coverage required
- If coverage falls below the threshold or any test fails, this checkpoint FAILS.
- Log the coverage result via audit-logger MCP `log_checkpoint` tool with `checkpoint_id: "test_coverage"`.

## On Checkpoint Failure

- **HALT** the workflow immediately. Do NOT proceed to the next checkpoint or merge.
- Log the failure details via audit-logger MCP `log_checkpoint` tool with `passed: false` and `validation_details` describing the failure reason.
- Report the failure to the user with actionable details (which checkpoint failed, why, and what to fix).
- Do NOT attempt to auto-fix and retry. The user must resolve the issue and re-run the pipeline.

## On All Checkpoints Passed

- All three checkpoints (code review, security scan, test coverage) must show `passed: true` in the audit log.
- Only then may the workflow proceed to the merge step.
- See `merge-policy.md` for merge prerequisites and rules.
