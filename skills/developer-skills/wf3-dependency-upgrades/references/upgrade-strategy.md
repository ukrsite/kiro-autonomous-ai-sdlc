# Dependency Upgrade Strategy

This document defines the strategy for upgrading outdated dependencies in the WF3 Dependency Upgrades workflow.

## Overview

Dependency upgrades follow a risk-minimizing, security-first approach. Upgrades are applied in a specific order to reduce the chance of cascading failures and to prioritize the most impactful changes.

## Upgrade Priority Order

### 1. Security-Critical Patches (Highest Priority)

Dependencies with known CVEs (Common Vulnerabilities and Exposures) are upgraded first, regardless of version jump size.

- Scan for CVEs using security-scanner MCP: `scan_dependencies`
- Upgrade to the nearest version that resolves the vulnerability
- Prefer patch-level fixes over major version jumps when available
- If only a major version resolves the CVE, proceed with full compatibility analysis

**Rationale:** Security vulnerabilities pose immediate risk. Patching them takes precedence over all other upgrade considerations.

### 2. Patch Version Upgrades

Patch versions (e.g., `1.2.3` → `1.2.5`) contain bug fixes and minor improvements with no API changes.

- Apply all available patch upgrades in a single batch
- Run the test suite after applying patches
- These should be low-risk and rarely require code changes

### 3. Minor Version Upgrades

Minor versions (e.g., `1.2.x` → `1.3.x`) may introduce new features but should maintain backward compatibility.

- Apply minor upgrades one dependency at a time
- Run compatibility checks via dependency-scanner MCP: `check_compatibility`
- Run the test suite after each minor upgrade
- If tests fail, investigate and generate code updates before proceeding

### 4. Major Version Upgrades (Lowest Priority)

Major versions (e.g., `1.x` → `2.x`) may contain breaking changes and require significant code modifications.

- Apply major upgrades one dependency at a time
- Run full compatibility analysis via dependency-scanner MCP: `check_compatibility`
- Generate an upgrade plan via dependency-scanner MCP: `get_upgrade_plan`
- Generate code updates for all breaking changes before running tests
- Run the full test suite after each major upgrade
- If tests fail after code updates, halt and report

## Scope Filters

The workflow accepts a `scope` parameter to control which upgrades are applied:

| Scope | Description |
|-------|-------------|
| `all` | Apply all available upgrades (default) |
| `security` | Only upgrade dependencies with known CVEs |
| `major` | Only apply major version upgrades |
| `minor` | Only apply minor and patch version upgrades |

## Dependency Graph Ordering

When multiple dependencies need upgrading, respect the dependency graph:

1. Upgrade leaf dependencies first (those with no dependents in the project)
2. Work inward toward core dependencies
3. Use dependency-scanner MCP: `get_upgrade_plan` to generate the correct order
4. Never upgrade a dependency before its own dependencies are stable

## Rollback Strategy

- A restore point is created before any upgrades begin
- If any upgrade causes test failures that cannot be resolved:
  1. Attempt to rollback only the failing dependency
  2. If isolated rollback is not possible, rollback all changes to the restore point
  3. Log the failure and partial results in the delta report

## Language-Specific Considerations

### Python (pip)

- Use `pip-audit` and `pip list --outdated` for scanning
- Update `requirements.txt` or `pyproject.toml`
- Pin exact versions to avoid drift
- Run `pip install -r requirements.txt` to verify resolution

### Java (Maven)

- Use `mvn versions:display-dependency-updates` for scanning
- Update `pom.xml` dependency versions
- Run `mvn dependency:resolve` to verify resolution
- Check for transitive dependency conflicts

### Node JS (npm)

- Use `npm outdated` for scanning
- Update `package.json` dependency versions
- Run `npm install` to regenerate `package-lock.json`
- Check for peer dependency warnings

## Metrics Collected

| Metric | Description |
|--------|-------------|
| `total_outdated` | Number of outdated dependencies found |
| `upgrades_attempted` | Number of upgrades attempted |
| `upgrades_successful` | Number of upgrades that passed all checks |
| `upgrades_failed` | Number of upgrades that caused failures |
| `breaking_changes_found` | Number of breaking changes detected |
| `code_updates_generated` | Number of code modifications made |
| `cves_resolved` | Number of CVEs resolved by upgrades |
