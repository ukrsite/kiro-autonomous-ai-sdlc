---
name: wf1-requirement-to-software
description: Takes a natural language requirement and produces merged, tested, documented code. Leverages Kiro's built-in spec workflow.
metadata:
  author: sdlc-prototype-team
  version: "1.0.0"
---

# Requirement to Working Software Workflow

This workflow takes a natural language requirement or user story and produces merged, tested, documented code with full audit traceability. It maps directly to Kiro's spec-driven development workflow (requirements → design → tasks → implementation).

## MANDATORY: Rule Details Loading

At workflow start, load the following from `.kiro/aws-aidlc-rule-details/`:

**Common rules** (always load):
- `common/verbosity-mode.md` — read `## Verbosity Mode` from `aidlc-docs/aidlc-state.md` and apply silent/debug output rules throughout this workflow
- `common/error-handling.md` — apply error severity levels, recovery procedures, and escalation guidelines
- `common/overconfidence-prevention.md` — default to asking clarifying questions; never assume when ambiguity exists
- `common/content-validation.md` — validate all generated content before writing files
- `common/depth-levels.md` — adapt artifact detail level to problem complexity

**Construction rules** (load when executing the relevant stage):
- `construction/code-generation.md` — apply code location rules, brownfield file modification rules, automation-friendly code rules, and checkbox tracking
- `construction/build-and-test.md` — apply test strategy, instruction file formats, and summary structure

**Extensions** (check enabled status in `aidlc-docs/aidlc-state.md` under `## Extension Configuration`):
- `extensions/security/baseline/security-baseline.md` — if Security Baseline is **Enabled**, enforce all SECURITY rules as blocking constraints during code generation and checkpoints; if **Disabled**, skip

## Workflow Steps

1. **Start Workflow** — Generate a `workflow_id` using the pattern `wf1-{issue-key-or-short-description}` (e.g. `wf1-add-date-utils`). Log workflow start immediately via audit-logger MCP: `log_event` with `event_type: "workflow_start"`, including the requirement and target module in `details`. Record this `workflow_id` — it must be used consistently for every subsequent audit-logger and finops call in this workflow.

   **MANDATORY**: This MCP call MUST succeed before proceeding. If it fails, halt and report the error. Do NOT substitute writing to `aidlc-docs/audit.md` — that file is for human-readable notes only and is NOT read by `calculate_workflow_cost`.

2. **Parse Requirement** — Check if the Handoff Artifact exists at `aidlc-docs/inception/plans/workflow-handoff.md`.
   - **If Handoff Artifact exists**: Load the Handoff Artifact and extract the requirements reference path from the "Requirements Reference" section. Use the referenced requirements document at `aidlc-docs/inception/requirements/requirements.md` as the authoritative input instead of raw user input. Validate that the Handoff Artifact is complete (contains all required sections). If the Handoff Artifact is missing or incomplete, halt execution and report the missing artifact to the user.
   - **If Handoff Artifact does not exist**: Accept a natural language requirement or user story as input. Validate that the input is clear and actionable.
   - Log the input via audit-logger MCP: `log_interaction`.

3. **Create Kiro Spec** — Use Kiro's built-in spec workflow to generate design and tasks:
   - **If Handoff Artifact exists**: Skip `requirements.md` generation entirely. Use `aidlc-docs/inception/requirements/requirements.md` (produced by AI-DLC INCEPTION) as the authoritative requirements source. Generate only:
     - `design.md` — Technical design and architecture decisions (consuming INCEPTION requirements as input)
     - `tasks.md` — Implementation task list with sub-tasks
   - **If Handoff Artifact does not exist**: Generate all spec artifacts from the input requirement:
     - `requirements.md` — Acceptance criteria derived from the input requirement
     - `design.md` — Technical design and architecture decisions
     - `tasks.md` — Implementation task list with sub-tasks

4. **Create Restore Point** — Before implementation, use git-rollback MCP: `create_restore_point` to snapshot the current state.

5. **Implement Tasks** — Execute each task from the generated `tasks.md`, scoping all file writes to the `sandbox_path`:
   - Generate code that satisfies the requirement — write files only under `sandbox_path`
   - MANDATORY: Generate corresponding unit tests for every new or modified source file — write test files under `sandbox_path/tests/`. Tests must cover all new functions, endpoints, models, validation logic, and edge cases. Aim for minimum 80% line coverage on new code.
   - Run the generated tests and verify they pass before proceeding to checkpoints
   - Generate documentation describing the implemented feature — write under `sandbox_path/docs/`
   - Do NOT write any generated application code to the root of the current (orchestration) repository
   - Log each implementation step via audit-logger MCP: `log_interaction`

6. **Code Review Checkpoint** — Submit generated code to code review validation:
   - Verify correctness and adherence to project conventions
   - Verify absence of security issues
   - Verify no dead code, unused imports, or TODO/FIXME markers
   - Log result via audit-logger MCP: `log_checkpoint`

7. **Test Coverage Checkpoint** — Validate test coverage meets the minimum threshold:
   - Run all unit tests against the generated code
   - Verify minimum 80% line coverage on new code
   - Log result via audit-logger MCP: `log_checkpoint`

8. **Security Scan Checkpoint** — Run security analysis on all generated code:
   - Use security-scanner MCP: `scan_code` on all modified files
   - Use security-scanner MCP: `scan_dependencies` if new dependencies were added
   - Verify no HIGH or CRITICAL vulnerabilities
   - Log result via audit-logger MCP: `log_checkpoint`

9. **Generate Documentation** — Create the following documentation artifacts in `docs/` under the sandbox path. Each artifact is MANDATORY — do not skip any:
   - [ ] Release notes (`docs/release-notes-{ISSUE_KEY}.md`) — use the Release Notes Template from `.kiro/skills/shared-skills/generate-documentation/references/output-templates.md`
   - [ ] API changelog entry (append to `docs/CHANGELOG.md`) — use Keep a Changelog format
   - [ ] OpenAPI spec (`docs/openapi.yaml`) — create or update if REST endpoints exist, skip only if no REST endpoints
   - [ ] Architecture diagram (`docs/architecture.md`) — Mermaid diagram of service components and endpoints
   - [ ] WF1 Summary Report (`docs/wf1-summary-{ISSUE_KEY}.md`) — use the WF1 Summary Report Template from `.kiro/skills/shared-skills/generate-documentation/references/output-templates.md`. Populate from checkpoint results (steps 6–8), audit data, and finops cost data. This is the same structure used in the final chat response.

10. **Merge** — If all checkpoints pass, commit and push the code (including generated docs and summary) to the target branch. Log the merge event via audit-logger MCP: `log_event`.

11. **Audit Log** — Record the complete workflow execution summary via audit-logger MCP: `log_event` with `event_type: "workflow_end"`, using the same `workflow_id` from Step 1. Include all checkpoint results and output artifacts in `details`.

    **MANDATORY**: This MCP call MUST succeed. Do NOT skip it or substitute writing to `aidlc-docs/audit.md`.

12. **Cost Report** — Immediately after Step 11, call finops-cost-estimator MCP: `calculate_workflow_cost` using the same `workflow_id`. Include the full cost breakdown table in the final response to the user per the format defined in `finops-cost-reporting.md`.

    **MANDATORY**: Call this even if the cost is zero. If it returns an error, include the error reason in the response — do not silently skip it.
