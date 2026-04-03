---
inclusion: always
---

# Coding Standards

## Code Review Requirements

1. **All AI-generated code must be reviewed before merge**: No code produced by an AI workflow may be merged without passing a code review checkpoint.
2. **Review scope**: Reviews must verify correctness, adherence to project conventions, and absence of security issues.
3. **Checkpoint enforcement**: Use the `preToolUse` checkpoint-guard hook to block commits that skip review.

## Test Coverage Thresholds

1. **Minimum coverage per workflow**:
   - WF1 (Requirement to Software): 80% line coverage on new code
   - WF2 (Autonomous Refactoring): 80% line coverage; all pre-existing tests must pass
   - WF3 (Dependency Upgrades): 70% line coverage; full test suite must pass post-upgrade
   - WF4 (Bug Fix): 90% coverage on fix and regression tests
   - WF5 (Documentation): No code coverage required
2. **Coverage validation**: Test coverage must be checked at the coverage checkpoint before merge. If coverage falls below the threshold, BLOCK the merge.

## Documentation Standards

1. **Public API documentation**: All public functions, classes, and interfaces must have docstrings or JSDoc comments describing purpose, parameters, and return values.
2. **Inline comments**: Complex logic, non-obvious algorithms, and workarounds must include inline comments explaining intent.
3. **README updates**: When a new module or significant feature is added, the relevant README must be updated.

## Code Quality Rules

1. **No dead code**: Remove unused functions, variables, and imports before merge.
2. **No unused imports**: All imports must be referenced in the file.
3. **Consistent formatting**: Code must follow the project's configured formatter (ruff for Python, prettier for JS/TS, google-java-format for Java).
4. **Naming conventions**: Use descriptive, consistent names following language idioms (snake_case for Python, camelCase for JS/TS, PascalCase for Java classes).
5. **No TODO/FIXME in merged code**: Resolve or file tracked issues for any temporary markers before merge.
