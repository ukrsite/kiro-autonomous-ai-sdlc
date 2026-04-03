---
name: wf2-autonomous-refactoring
description: Refactors legacy code while preserving behavior. Use when refactoring technical debt, modernizing code patterns, or improving code quality.
metadata:
  author: sdlc-prototype-team
  version: "1.0.0"
---

# Autonomous Refactoring Workflow

This workflow takes a legacy code module or technical debt item and produces refactored code with verified behavior equivalence, performance benchmarks, security validation, and full audit traceability. It ensures all pre-existing tests continue to pass and no new vulnerabilities are introduced.

## Workflow Steps

1. **Analyze Legacy Code** — Accept a target module path and refactoring goals as input. Identify technical debt, code smells, and refactoring opportunities (long methods, poor naming, code duplication, complex conditionals, dead code). Log the analysis via audit-logger MCP: `log_interaction`.

2. **Create Restore Point** — Before making any changes, use git-rollback MCP: `create_restore_point` to snapshot the current state. Record the `restore_point_id` for potential rollback. Log via audit-logger MCP: `log_event`.

3. **Apply Refactoring** — Generate refactored code applying modern patterns and improvements:
   - Extract method for long or duplicated code blocks
   - Rename variables and functions for clarity
   - Simplify complex conditionals
   - Remove code duplication (DRY principle)
   - Apply language-specific idioms and best practices
   - Preserve all public API signatures unless explicitly requested otherwise
   - Log each refactoring step via audit-logger MCP: `log_interaction`

4. **Run Existing Tests** — Execute all pre-existing unit tests against the refactored code:
   - Use git-rollback MCP: `verify_consistency` to run the project's test suite
   - Verify all pre-existing tests pass (zero failures)
   - Verify minimum 80% line coverage is maintained
   - If tests fail, use git-rollback MCP: `rollback` to restore the previous state
   - Log result via audit-logger MCP: `log_checkpoint`

5. **Behavior Equivalence Check** — Compare original vs refactored behavior:
   - Use the skill's `scripts/compare_behavior.py` helper to automate comparison
   - Verify identical outputs for identical inputs across representative test cases
   - Verify no change in error handling behavior
   - Verify no change in side effects (file I/O, network calls, state mutations)
   - Log result via audit-logger MCP: `log_checkpoint`
   - See `references/behavior-equivalence.md` for detailed methodology

6. **Performance Benchmark** — Run benchmarks comparing original vs refactored code:
   - Use the skill's `scripts/run_benchmarks.py` helper to measure timing and memory
   - Verify performance is not degraded beyond acceptable threshold (10% tolerance)
   - Log result via audit-logger MCP: `log_checkpoint`

7. **Security Scan** — Run security analysis on all refactored code:
   - Use security-scanner MCP: `scan_code` on all modified files
   - Verify no new HIGH or CRITICAL vulnerabilities introduced
   - Compare scan results against pre-refactoring baseline
   - Log result via audit-logger MCP: `log_checkpoint`

8. **Generate Delta Report** — Produce a summary of all changes:
   - List all files modified, added, or deleted
   - Summarize refactoring patterns applied
   - Include before/after code metrics (lines, complexity, coverage)
   - Include performance benchmark comparison
   - Include security scan comparison
   - Log report via audit-logger MCP: `log_event`

9. **Audit Log** — Record the complete workflow execution summary via audit-logger MCP: `log_event` with event_type `workflow_end`, including all checkpoint results, delta report reference, and output artifacts.

## Checkpoints (MUST pass before proceeding)

- [ ] **Existing Tests**: All pre-existing unit tests pass on refactored code (zero failures)
- [ ] **Test Coverage**: Minimum 80% line coverage maintained; all pre-existing tests pass
- [ ] **Behavior Equivalence**: Original and refactored code produce identical outputs for identical inputs
- [ ] **Performance**: Performance not degraded beyond 10% tolerance threshold
- [ ] **Security Scan**: No new HIGH or CRITICAL vulnerabilities introduced

## If Any Checkpoint Fails

STOP. Do NOT proceed. Report failure details including:
- Which checkpoint failed
- Specific failure reasons and validation details
- Behavioral differences or performance regressions detected
- Suggested remediation steps

Use git-rollback MCP: `rollback` to restore the previous state using the saved `restore_point_id`.
Log the failure via audit-logger MCP: `log_checkpoint` with `passed: false`.

## Expected Inputs

- Target module path containing legacy code or technical debt (e.g., `sample-app/python-module/legacy/`)
- Refactoring goals (optional, e.g., "reduce duplication", "simplify conditionals", "modernize patterns")

## Expected Outputs

- Refactored source code with modern patterns applied
- Performance benchmark report (original vs refactored)
- Behavior equivalence verification results
- Delta report summarizing all changes and metrics
- Audit trail of all interactions, checkpoints, and decisions

## MCP Server Dependencies

- **audit-logger**: `log_interaction`, `log_checkpoint`, `log_event`
- **security-scanner**: `scan_code`
- **git-rollback**: `create_restore_point`, `rollback`
