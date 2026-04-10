# Behavior Equivalence Methodology — WF2

## Overview

Behavior equivalence verification ensures that refactored code produces identical
observable outputs for identical inputs compared to the original code. This document
defines the methodology used by `scripts/compare_behavior.py`.

## Two Verification Modes

### 1. Live HTTP Comparison (preferred)

Both the original and refactored services are started on separate ports. A set of
representative HTTP test cases is executed against both, and responses are compared.

**When used**: When `mvn` is available and both service paths have a `pom.xml`.

**What is compared**:
- HTTP status codes (must match, or match expected for new endpoints)
- Response body structure (top-level JSON keys)
- Error handling behavior (4xx responses for invalid inputs)
- Public endpoint accessibility (no auth required)

### 2. Static Source Analysis (fallback)

When live servers cannot be started, the source files of both versions are compared
to verify structural equivalence of security configuration, endpoint signatures,
and DTO shapes.

**When used**: When `mvn` is not in PATH, or `--static-only` flag is passed.

## Test Case Categories

### Preserved Behavior (must be equivalent)

| Category | Test Case | Expected |
|---|---|---|
| Authentication | Unauthenticated request | 401 Unauthorized |
| Authentication | Authenticated request | 200 OK |
| Public endpoints | Actuator health | 200 OK (no auth) |
| Public endpoints | Swagger UI | 200 OK (no auth) |

### New Behavior (additive — not a regression)

| Category | Test Case | Original | Refactored |
|---|---|---|---|
| New endpoint | GET /api/users | 404 (no handler) | 200 + JSON array |
| New endpoint | GET /api/users/{id} | 404 (no handler) | 200 + JSON |
| New endpoint | GET /api/users/99999 | 404 (no handler) | 404 + error body |

### Intentional Changes (documented divergence)

| Aspect | Original | Refactored | Reason |
|---|---|---|---|
| Password encoding | NoOpPasswordEncoder | BCryptPasswordEncoder | Security hardening |
| CORS origins | Wildcard `*` | `http://localhost:*` | Security hardening |

Intentional changes must be documented in the Behavior-Preservation Contract and do NOT
constitute a behavioral regression.

## Pass/Fail Criteria

A behavior equivalence check **passes** when:
1. All "preserved behavior" test cases produce equivalent results
2. All "new behavior" test cases produce the expected results in the refactored version
3. All "intentional changes" are documented in the Behavior-Preservation Contract

A behavior equivalence check **fails** when:
1. Any previously working endpoint returns a different status code (not documented as intentional)
2. Any authentication/authorization behavior changes unexpectedly
3. Any error handling behavior changes unexpectedly

## Report Output

Results are written to `reports/behavior-equivalence-report.json` with:
- `summary.overall_passed`: boolean — the checkpoint result
- `results[]`: per-test-case details with status codes and notes
- `mode`: `"live"` or `"static"`

## Integration with WF2 Checkpoints

```
scripts/compare_behavior.py
  exit 0 → log_checkpoint(passed=True)  → continue to Performance Benchmark
  exit 1 → log_checkpoint(passed=False) → STOP, trigger rollback
```
