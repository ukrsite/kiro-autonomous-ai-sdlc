# Behavior Equivalence Verification

This document describes how to verify behavior equivalence between original and refactored code in the WF2 Autonomous Refactoring workflow.

## Overview

Behavior equivalence means the refactored code produces the same observable outputs as the original code for all valid inputs. This includes return values, side effects, error handling, and state mutations.

## Verification Strategy

### 1. Test Suite Preservation

The most fundamental check: all pre-existing unit tests must pass against the refactored code without modification.

- Run the full test suite before refactoring (baseline)
- Run the full test suite after refactoring
- Compare: zero test failures allowed
- Coverage must remain at or above 80% line coverage

### 2. Input/Output Comparison

For each public function or method that was refactored:

1. **Identify representative inputs**: Collect inputs from existing tests, edge cases, and boundary values
2. **Capture original outputs**: Run the original code with each input set and record outputs
3. **Capture refactored outputs**: Run the refactored code with the same input sets
4. **Compare**: Assert outputs are identical (or equivalent within floating-point tolerance)

Use `scripts/compare_behavior.py` to automate this process.

### 3. Error Handling Equivalence

Verify that the refactored code raises the same exceptions/errors for the same invalid inputs:

- Same exception types for the same error conditions
- Same error messages (or semantically equivalent)
- Same error propagation behavior

### 4. Side Effect Equivalence

If the original code has side effects, verify they are preserved:

- **File I/O**: Same files read/written with same content
- **State mutations**: Same object state changes
- **Logging**: Same log messages produced (content, not necessarily format)
- **External calls**: Same external service calls made (if applicable)

### 5. Property-Based Testing

Use property-based testing to verify equivalence across a wide range of inputs:

```python
from hypothesis import given, strategies as st

@given(st.integers(), st.integers())
def test_add_equivalence(a, b):
    assert original_add(a, b) == refactored_add(a, b)
```

This catches edge cases that hand-written tests may miss.

## Comparison Methodology

### Exact Match

For deterministic functions with discrete outputs:
- Return values must be identical (`==`)
- Exception types and messages must match

### Approximate Match

For functions involving floating-point arithmetic:
- Use tolerance-based comparison (`abs(a - b) < epsilon`)
- Default epsilon: `1e-9`
- Document any tolerance used in the delta report

### Structural Match

For functions returning complex objects:
- Compare structure recursively
- Ignore ordering of unordered collections (sets, dict keys)
- Compare sorted sequences if order is not semantically significant

## Failure Handling

If behavior equivalence verification fails:

1. **STOP** — Do not proceed with the refactoring
2. **Report** — Document the specific behavioral differences:
   - Which function/method diverges
   - What input triggers the difference
   - Expected output (original) vs actual output (refactored)
3. **Rollback** — Use git-rollback MCP: `rollback` to restore original code
4. **Log** — Record failure via audit-logger MCP: `log_checkpoint` with `passed: false`

## Metrics Collected

| Metric | Description |
|--------|-------------|
| `functions_compared` | Number of public functions tested for equivalence |
| `inputs_tested` | Total number of input sets used |
| `exact_matches` | Number of functions with exact output match |
| `approximate_matches` | Number of functions matching within tolerance |
| `failures` | Number of functions with behavioral differences |
| `coverage_before` | Line coverage percentage before refactoring |
| `coverage_after` | Line coverage percentage after refactoring |
