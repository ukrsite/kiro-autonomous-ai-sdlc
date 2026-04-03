# Checkpoint Pass/Fail Criteria

This document defines the pass/fail criteria for each checkpoint in the WF1 Requirement to Working Software workflow.

## 1. Code Review Checkpoint

### Pass Criteria

- Generated code correctly implements the requirement as described in the spec
- Code follows project coding conventions (naming, formatting, structure)
- All public functions, classes, and interfaces have docstrings or JSDoc comments
- No hardcoded secrets, API keys, passwords, or credentials
- No dead code, unused variables, or unused imports
- No TODO/FIXME markers in code to be merged
- Complex logic includes inline comments explaining intent
- Consistent formatting per project formatter (ruff for Python, prettier for JS/TS, google-java-format for Java)

### Fail Criteria

- Code does not satisfy the stated requirement
- Code contains security vulnerabilities (hardcoded secrets, SQL injection, etc.)
- Code violates project naming conventions or formatting standards
- Public APIs lack documentation
- Dead code or unused imports present

## 2. Test Coverage Checkpoint

### Pass Criteria

- All unit tests pass (zero failures)
- Minimum 80% line coverage on new/modified code
- Tests cover core functional logic and important edge cases
- Tests validate real functionality (no mocks that bypass logic)
- Pre-existing tests continue to pass (no regressions)

### Fail Criteria

- Any unit test fails
- Line coverage on new code falls below 80%
- Tests rely on mocks or fake data that bypass real validation
- Pre-existing tests broken by new code

### Measurement

- Python: `pytest --cov` with `--cov-fail-under=80`
- Java: JaCoCo with 80% minimum line coverage
- Node JS: Jest with `--coverage --coverageThreshold='{"global":{"lines":80}}'`

## 3. Security Scan Checkpoint

### Pass Criteria

- security-scanner MCP `scan_code` returns zero HIGH or CRITICAL findings
- security-scanner MCP `scan_dependencies` returns zero HIGH or CRITICAL CVEs (if new dependencies added)
- No production credentials or API keys detected in code
- Input validation present for all user-facing inputs
- Parameterized queries used for any database operations

### Fail Criteria

- Any HIGH or CRITICAL vulnerability found by `scan_code`
- Any HIGH or CRITICAL CVE found by `scan_dependencies`
- Hardcoded secrets or production credentials detected
- Missing input validation on user-facing inputs
- SQL injection or command injection patterns detected

### Severity Levels

| Severity | Action |
|----------|--------|
| CRITICAL | Block merge immediately. Must be resolved. |
| HIGH | Block merge. Must be resolved before proceeding. |
| MEDIUM | Warning. Should be resolved but does not block merge. |
| LOW | Informational. Log and track for future resolution. |

## 4. Documentation Checkpoint

### Pass Criteria

- All public functions, classes, and interfaces have docstrings (Python), JSDoc (JS/TS), or Javadoc (Java) comments describing purpose, parameters, and return values
- Complex logic, non-obvious algorithms, and workarounds include inline comments explaining intent
- README is updated when a new module or significant feature is added
- A feature description document exists summarizing what was implemented and why
- Inline documentation is accurate and matches the actual implementation

### Fail Criteria

- Any public API (function, class, interface) lacks a docstring/JSDoc/Javadoc comment
- Complex logic has no inline comments explaining intent
- A new module or significant feature was added but the README was not updated
- No feature description document was generated
- Documentation is inaccurate or contradicts the implementation
