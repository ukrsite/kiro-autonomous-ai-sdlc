# Checkpoint Pass/Fail Criteria

This document defines the pass/fail criteria for each checkpoint in the WF2 Autonomous Refactoring workflow.

## 1. Existing Tests Checkpoint

### Pass Criteria

- All pre-existing unit tests pass (zero failures)
- Minimum 80% line coverage maintained on refactored code
- No regressions introduced by the refactoring
- git-rollback MCP `verify_consistency` reports `consistent: true`

### Fail Criteria

- Any pre-existing unit test fails
- Line coverage drops below 80%
- New test failures introduced by refactoring

## 2. Behavior Equivalence Checkpoint

### Pass Criteria

- All public functions produce identical outputs for identical inputs
- Exception types and messages match between original and refactored code
- Side effects (file I/O, state mutations) are preserved
- `scripts/compare_behavior.py` reports `overall_passed: true`

### Fail Criteria

- Any public function produces different output for the same input
- Exception behavior differs between original and refactored code
- Side effects changed (files written, state mutated differently)

## 3. Performance Benchmark Checkpoint

### Pass Criteria

- Execution time not degraded beyond 10% tolerance
- Memory usage not significantly increased
- `scripts/run_benchmarks.py` reports `overall_passed: true`

### Fail Criteria

- Execution time degraded more than 10% compared to original
- Significant memory regression detected

## 4. Security Scan Checkpoint

### Pass Criteria

- security-scanner MCP `scan_code` returns zero new HIGH or CRITICAL findings
- No hardcoded secrets or production credentials in refactored code
- No new injection patterns introduced

### Fail Criteria

- Any new HIGH or CRITICAL vulnerability found by `scan_code`
- Hardcoded secrets or production credentials detected
- New SQL injection or command injection patterns introduced

### Severity Levels

| Severity | Action |
|----------|--------|
| CRITICAL | Block immediately. Must be resolved. |
| HIGH | Block. Must be resolved before proceeding. |
| MEDIUM | Warning. Should be resolved but does not block. |
| LOW | Informational. Log and track for future resolution. |
