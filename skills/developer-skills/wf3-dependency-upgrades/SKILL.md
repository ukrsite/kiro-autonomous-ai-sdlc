---
name: wf3-dependency-upgrades
description: Upgrades outdated third-party dependencies with automated compatibility checking. Use for periodic dependency maintenance.
metadata:
  author: sdlc-prototype-team
  version: "1.0.0"
---

# Dependency Upgrades Workflow

This workflow takes a software project with outdated dependencies and produces updated dependencies with verified compatibility, full test validation, and a comprehensive delta report. It ensures all tests pass post-upgrade, creates a rollback restore point, and logs every step for audit traceability.

## Workflow Steps

1. **Create Restore Point** — Before making any changes, use git-rollback MCP: `create_restore_point` to snapshot the current state including lockfiles (`pom.xml`, `package-lock.json`, `requirements.txt`). Record the `restore_point_id` for potential rollback. Log via audit-logger MCP: `log_event`.

2. **Scan Outdated Dependencies** — Use dependency-scanner MCP: `scan_outdated` to identify all outdated dependencies and available updates. Accept a `scope` parameter to filter by upgrade type:
   - `all` — scan all outdated dependencies
   - `security` — only dependencies with known CVEs
   - `major` — only major version upgrades
   - `minor` — only minor and patch version upgrades
   - Log scan results via audit-logger MCP: `log_interaction`

3. **Check Compatibility** — For each outdated dependency, use dependency-scanner MCP: `check_compatibility` to assess breaking changes between the current and target versions. Use dependency-scanner MCP: `get_upgrade_plan` to generate an ordered upgrade plan respecting the dependency graph. Log compatibility results via audit-logger MCP: `log_interaction`.

4. **Generate Code Updates** — When breaking changes are detected, generate code modifications to resolve incompatibilities:
   - Update import statements and API calls for changed interfaces
   - Adjust configuration files for new dependency requirements
   - Update type definitions or signatures as needed
   - Log each code update via audit-logger MCP: `log_interaction`

5. **Run Full Test Suite** — Execute the complete automated test suite against the updated dependencies:
   - Python: `pytest --cov --cov-fail-under=70`
   - Java: `mvn test` with JaCoCo coverage
   - Node JS: `npm test -- --coverage`
   - Verify minimum 70% line coverage
   - Verify all tests pass (zero failures)
   - Log result via audit-logger MCP: `log_checkpoint`

6. **Security Scan** — Run security analysis on updated dependencies:
   - Use security-scanner MCP: `scan_dependencies` on the project
   - Verify no new HIGH or CRITICAL vulnerabilities introduced by upgrades
   - Log result via audit-logger MCP: `log_checkpoint`

7. **Generate Delta Report** — Produce a comprehensive summary of all dependency changes:
   - Use `scripts/generate_delta_report.py` to compare before/after states
   - List each upgraded dependency with old and new version numbers
   - Document breaking changes detected and code modifications made
   - Include test results (pass/fail counts, coverage before/after)
   - Include security scan comparison
   - Log report via audit-logger MCP: `log_event`

8. **Audit Log** — Record the complete workflow execution summary via audit-logger MCP: `log_event` with event_type `workflow_end`, including all checkpoint results, delta report reference, restore point ID, and output artifacts.

## Checkpoints (MUST pass before proceeding)

- [ ] **Test Suite**: All automated tests pass after dependency upgrades (zero failures)
- [ ] **Test Coverage**: Minimum 70% line coverage maintained post-upgrade
- [ ] **Security Scan**: No new HIGH or CRITICAL vulnerabilities introduced by upgrades
- [ ] **Compatibility**: All breaking changes resolved with verified code updates

## If Any Checkpoint Fails

STOP. Do NOT proceed. Report failure details including:
- Which checkpoint failed
- Specific failure reasons and validation details
- Which dependency upgrade caused the failure
- Test failures or security vulnerabilities introduced
- Suggested remediation steps

Use git-rollback MCP: `rollback` to restore the pre-upgrade state using the saved `restore_point_id`.
Log the failure via audit-logger MCP: `log_checkpoint` with `passed: false`.

## Upgrade Strategy

Follow the priority order defined in `references/upgrade-strategy.md`:
1. Security-critical patches first
2. Minor and patch version upgrades
3. Major version upgrades (with full compatibility analysis)

See `references/compatibility-checks.md` for detailed compatibility verification methodology.

## Expected Inputs

- Project path containing dependencies to upgrade (e.g., `sample-app/python-module/`)
- Scope filter (optional): `all`, `security`, `major`, `minor` (default: `all`)
- Language hint (optional): `python`, `java`, `nodejs` (auto-detected if omitted)

## Expected Outputs

- Updated dependency files (`requirements.txt`, `pom.xml`, `package.json`)
- Code modifications resolving breaking changes (if any)
- Delta report summarizing all dependency changes, test results, and security status
- Restore point ID for rollback capability
- Audit trail of all interactions, checkpoints, and decisions

## MCP Server Dependencies

- **dependency-scanner**: `scan_outdated`, `check_compatibility`, `get_upgrade_plan`
- **git-rollback**: `create_restore_point`, `rollback`
- **security-scanner**: `scan_dependencies`
- **audit-logger**: `log_interaction`, `log_checkpoint`, `log_event`
