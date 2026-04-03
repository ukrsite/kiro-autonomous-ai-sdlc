# Root Cause Analysis Methodology

This document describes the methodology for performing root cause analysis of bugs in the WF4 Bug Fix workflow.

## Overview

Root cause analysis (RCA) is the process of identifying the fundamental reason a defect exists, rather than just addressing symptoms. A thorough RCA ensures the fix targets the actual problem and prevents recurrence.

## Analysis Strategy

### 1. Reproduce the Bug

Before investigating, confirm the defect is reproducible:

- Run the failing test or follow the bug report reproduction steps
- Capture the exact error message, stack trace, and failure output
- Document the environment conditions (language version, OS, dependencies)
- If the bug is intermittent, identify conditions that increase reproduction likelihood

### 2. Isolate the Failure

Narrow down the scope of the defect:

- **Binary search**: Disable or comment out code sections to isolate the failing path
- **Minimal reproduction**: Create the smallest possible input that triggers the bug
- **Dependency check**: Determine if the bug is in application code or a dependency
- **Version bisect**: Use `git bisect` to identify the commit that introduced the defect

### 3. Trace Execution

Follow the code path from input to failure:

- **Stack trace analysis**: Read the stack trace bottom-up to identify the failing call chain
- **Data flow tracing**: Track variable values through the execution path
- **Control flow analysis**: Identify which branches and conditions lead to the failure
- **State inspection**: Check object state at each step for unexpected mutations

### 4. Classify the Root Cause

Categorize the defect to guide the fix approach:

| Category | Description | Example |
|----------|-------------|---------|
| Logic error | Incorrect conditional or algorithm | Off-by-one in loop bound |
| Missing validation | Input not checked before use | Null pointer on unvalidated input |
| Race condition | Timing-dependent failure | Concurrent access to shared state |
| Incorrect state | Object in unexpected state | Stale cache after update |
| Type error | Wrong type passed or returned | String where integer expected |
| Resource leak | Resource not properly released | Unclosed file handle or connection |
| Configuration error | Wrong setting or missing config | Incorrect timeout value |
| Integration error | Mismatch between components | API contract violation |

### 5. Verify the Root Cause

Confirm the identified cause is correct:

- Explain how the root cause produces the observed symptoms
- Predict what a fix targeting this cause would change
- Check if the root cause explains all reported symptoms (not just some)
- Verify no other defects are masking or contributing to the failure

## Documentation Requirements

The root cause analysis must document:

1. **Bug summary**: One-line description of the defect
2. **Reproduction steps**: Exact steps or test to reproduce
3. **Root cause**: Clear description of why the defect occurs
4. **Evidence**: Stack traces, variable values, or code references supporting the analysis
5. **Impact scope**: Which code paths, features, or users are affected
6. **Fix recommendation**: Proposed approach to resolve the root cause

## Common Pitfalls

- **Fixing symptoms, not causes**: Ensure the fix addresses the root cause, not just the visible error
- **Incomplete analysis**: Verify the root cause explains all symptoms before proceeding
- **Scope creep**: Focus on the reported defect; log unrelated issues separately
- **Assumption bias**: Test hypotheses with evidence rather than assuming the cause

## Metrics Collected

| Metric | Description |
|--------|-------------|
| `reproduction_confirmed` | Whether the bug was successfully reproduced |
| `root_cause_category` | Classification of the root cause |
| `files_investigated` | Number of files examined during analysis |
| `commits_bisected` | Number of commits checked during version bisect (if used) |
| `confidence_level` | High, medium, or low confidence in the identified root cause |
