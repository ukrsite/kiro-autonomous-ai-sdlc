---
name: wf3-dependency-upgrades
description: Upgrades outdated third-party dependencies with automated compatibility checking. Use for periodic dependency maintenance.
metadata:
  author: sdlc-prototype-team
  version: "1.0.0"
---

# Dependency Upgrades Workflow

This workflow takes a software project with outdated dependencies and produces updated dependencies with verified compatibility, full test validation, and a comprehensive delta report. It ensures all tests pass post-upgrade, creates a rollback restore point, and logs every step for audit traceability.

## MANDATORY: Rule Details Loading

At workflow start, load the following from `.kiro/aws-aidlc-rule-details/`:

**Common rules** (always load):
- `common/verbosity-mode.md` — read `## Verbosity Mode` from `aidlc-docs/aidlc-state.md` and apply silent/debug output rules throughout this workflow
- `common/error-handling.md` — apply error severity levels, recovery procedures, and escalation guidelines
- `common/overconfidence-prevention.md` — default to asking clarifying questions; never assume when ambiguity exists
- `common/content-validation.md` — validate all generated content before writing files
- `common/depth-levels.md` — adapt artifact detail level to problem complexity

**Construction rules** (load when executing the relevant stage):
- `construction/code-generation.md` — apply code location rules and brownfield file modification rules when generating code updates for breaking changes
- `construction/build-and-test.md` — apply test strategy, instruction file formats, and summary structure for post-upgrade validation

**Extensions** (check enabled status in `aidlc-docs/aidlc-state.md` under `## Extension Configuration`):
- `extensions/security/baseline/security-baseline.md` — if Security Baseline is **Enabled**, enforce SECURITY-10 (supply chain security) as a blocking constraint during dependency scanning and upgrade steps; enforce all other applicable SECURITY rules on any generated code; if **Disabled**, skip

## Workflow Steps

1. **Start Workflow** — Generate a `workflow_id` using the pattern `wf3-{issue-key-or-short-description}` (e.g. `wf3-spring-boot-upgrade`). Log workflow start immediately via audit-logger MCP: `log_event` with `event_type: "workflow_start"`, including the target project path and upgrade scope in `details`. Record this `workflow_id` — it must be used consistently for every subsequent audit-logger and finops call in this workflow.

   **MANDATORY**: This MCP call MUST succeed before proceeding. Do NOT substitute writing to `aidlc-docs/audit.md`.

2. **Create Restore Point** — Before making any changes, use git-rollback MCP: `create_restore_point` to snapshot the current state including lockfiles (`pom.xml`, `package-lock.json`, `requirements.txt`). Record the `restore_point_id` for potential rollback. Log via audit-logger MCP: `log_event`.

3. **Scan Outdated Dependencies** — Use dependency-scanner MCP: `scan_outdated` to identify all outdated dependencies and available updates. Accept a `scope` parameter to filter by upgrade type:
   - `all` — scan all outdated dependencies
   - `security` — only dependencies with known CVEs
   - `major` — only major version upgrades
   - `minor` — only minor and patch version upgrades
   - Log scan results via audit-logger MCP: `log_interaction`

4. **Check Compatibility** — For each outdated dependency, use dependency-scanner MCP: `check_compatibility` to assess breaking changes between the current and target versions. Use dependency-scanner MCP: `get_upgrade_plan` to generate an ordered upgrade plan respecting the dependency graph. Log compatibility results via audit-logger MCP: `log_interaction`.

5. **Generate Code Updates** — When breaking changes are detected, generate code modifications to resolve incompatibilities:
   - Update import statements and API calls for changed interfaces
   - Adjust configuration files for new dependency requirements
   - Update type definitions or signatures as needed
   - Log each code update via audit-logger MCP: `log_interaction`

6. **Run Full Test Suite** — Execute the complete automated test suite against the updated dependencies:
   - Python: `pytest --cov --cov-fail-under=70`
   - Java: `mvn test` with JaCoCo coverage
   - Node JS: `npm test -- --coverage`
   - Verify minimum 70% line coverage
   - Verify all tests pass (zero failures)
   - Log result via audit-logger MCP: `log_checkpoint`

7. **Security Scan** — Run security analysis on updated dependencies:
   - Use security-scanner MCP: `scan_dependencies` on the project
   - Verify no new HIGH or CRITICAL vulnerabilities introduced by upgrades
   - Log result via audit-logger MCP: `log_checkpoint`

8. **Generate Documentation** — Invoke the shared `generate-documentation` skill to produce documentation artifacts for the dependency changes:
   - Release notes (`docs/release-notes-{ISSUE_KEY}.md`) with upgraded dependency list
   - API changelog entry (append to `docs/CHANGELOG.md`) if API signatures changed
   - OpenAPI spec (`docs/openapi.yaml`) update if endpoint behavior changed
   - Architecture diagram (`docs/architecture.md`)
   - See `skill://.kiro/skills/shared-skills/generate-documentation/SKILL.md` for full details

9. **Generate Delta Report** — Produce a comprehensive summary of all dependency changes:
   - Use `scripts/generate_delta_report.py` to compare before/after states
   - List each upgraded dependency with old and new version numbers
   - Document breaking changes detected and code modifications made
   - Include test results (pass/fail counts, coverage before/after)
   - Include security scan comparison
   - Log report via audit-logger MCP: `log_event`

10. **Audit Log** — Record the complete workflow execution summary via audit-logger MCP: `log_event` with event_type `workflow_end`, including all checkpoint results, delta report reference, restore point ID, and output artifacts.

    **MANDATORY**: This MCP call MUST succeed. Do NOT skip it or substitute writing to `aidlc-docs/audit.md`.

11. **Cost Report** — After logging `workflow_end`, call finops-cost-estimator MCP: `calculate_workflow_cost` using the active `workflow_id`. Then log the cost result back to the audit trail via audit-logger MCP: `log_event` with `event_type: "cost_report"`. Include the full cost breakdown table in the final response to the user per the format defined in `finops-cost-reporting.md`.

    **MANDATORY**: Both MCP calls MUST be made. Call `calculate_workflow_cost` even if the cost is zero.

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
- Generated documentation artifacts (release notes, API changelog, OpenAPI spec, architecture diagram)
- Restore point ID for rollback capability
- Audit trail of all interactions, checkpoints, and decisions

## MCP Server Dependencies

- **dependency-scanner**: `scan_outdated`, `check_compatibility`, `get_upgrade_plan`
- **git-rollback**: `create_restore_point`, `rollback`
- **security-scanner**: `scan_dependencies`
- **audit-logger**: `log_interaction`, `log_checkpoint`, `log_event`
- **finops-cost-estimator**: `calculate_workflow_cost`
