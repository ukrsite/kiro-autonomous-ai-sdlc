# Compatibility Checks Reference

This document describes how to verify compatibility between dependency versions in the WF3 Dependency Upgrades workflow.

## Overview

Compatibility checking ensures that upgrading a dependency does not break the existing codebase. This involves analyzing API changes, detecting breaking changes, and verifying that all existing tests pass with the new version.

## Compatibility Check Strategy

### 1. API Surface Analysis

For each dependency being upgraded, analyze the API surface for breaking changes:

- **Removed functions or classes**: Functions or classes that existed in the old version but are absent in the new version
- **Changed signatures**: Parameters added, removed, reordered, or type-changed
- **Changed return types**: Functions that return different types in the new version
- **Changed behavior**: Functions that produce different outputs for the same inputs
- **Deprecated features**: Features marked deprecated in the old version and removed in the new version

Use dependency-scanner MCP: `check_compatibility` to automate this analysis.

### 2. Import Verification

After upgrading a dependency, verify all imports resolve correctly:

1. Scan all project files for imports from the upgraded dependency
2. Verify each imported symbol exists in the new version
3. Flag any imports that reference removed or renamed symbols
4. Generate import update suggestions for renamed symbols

### 3. Type Compatibility

For statically typed languages or projects using type hints:

- Verify type annotations remain valid with the new dependency version
- Check for changes in generic type parameters
- Verify interface implementations still satisfy contracts
- Run type checkers (`mypy` for Python, `tsc` for TypeScript) after upgrade

### 4. Transitive Dependency Conflicts

Upgrading one dependency may affect others through transitive dependencies:

- Check for version conflicts in the resolved dependency tree
- Verify no two dependencies require incompatible versions of a shared transitive dependency
- Use the package manager's resolution mechanism to detect conflicts:
  - Python: `pip check`
  - Java: `mvn dependency:tree -Dverbose`
  - Node JS: `npm ls`

### 5. Runtime Behavior Verification

The most reliable compatibility check is running the full test suite:

- Execute all unit tests with the upgraded dependency
- Execute integration tests if available
- Compare test results against the pre-upgrade baseline
- Any new test failure indicates a compatibility issue

## Breaking Change Categories

| Category | Severity | Action Required |
|----------|----------|-----------------|
| Removed API | High | Generate code update to use replacement API |
| Changed signature | High | Update all call sites to match new signature |
| Changed return type | Medium | Update code handling the return value |
| New required parameter | Medium | Add the required parameter at all call sites |
| Deprecated API | Low | Plan migration but no immediate action needed |
| Changed default value | Low | Verify behavior is still correct with new default |
| New optional parameter | None | No action needed |

## Compatibility Check Process

For each dependency upgrade:

```
1. Record current version and target version
2. Run: dependency-scanner MCP check_compatibility(dep, from_ver, to_ver)
3. If breaking changes detected:
   a. Categorize each breaking change by severity
   b. For High severity: generate code updates before proceeding
   c. For Medium severity: generate code updates before proceeding
   d. For Low severity: document in delta report, proceed with caution
4. Apply the version upgrade
5. Run the full test suite
6. If tests pass: mark upgrade as compatible
7. If tests fail: analyze failures, generate fixes, or rollback
```

## Failure Handling

If compatibility checks reveal issues that cannot be automatically resolved:

1. **STOP** — Do not proceed with the upgrade for this dependency
2. **Report** — Document the incompatibility:
   - Which dependency and version transition caused the issue
   - Specific breaking changes detected
   - Which project files are affected
   - Suggested manual resolution steps
3. **Continue** — Proceed with other dependency upgrades if possible
4. **Log** — Record the failure via audit-logger MCP: `log_checkpoint` with `passed: false`

If the overall upgrade batch fails (test suite does not pass after all upgrades):

1. Use git-rollback MCP: `rollback` to restore the pre-upgrade state
2. Log the rollback via audit-logger MCP: `log_event`
3. Include partial results in the delta report

## Metrics Collected

| Metric | Description |
|--------|-------------|
| `dependencies_checked` | Number of dependencies analyzed for compatibility |
| `breaking_changes_found` | Total breaking changes detected across all upgrades |
| `auto_resolved` | Breaking changes resolved by generated code updates |
| `manual_required` | Breaking changes requiring manual intervention |
| `tests_passed_post_upgrade` | Number of tests passing after upgrades |
| `tests_failed_post_upgrade` | Number of tests failing after upgrades |
| `coverage_before` | Line coverage percentage before upgrades |
| `coverage_after` | Line coverage percentage after upgrades |
