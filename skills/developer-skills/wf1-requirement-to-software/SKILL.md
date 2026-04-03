---
name: wf1-requirement-to-software
description: Takes a natural language requirement and produces merged, tested, documented code. Leverages Kiro's built-in spec workflow.
metadata:
  author: sdlc-prototype-team
  version: "1.0.0"
---

# Requirement to Working Software Workflow

This workflow takes a natural language requirement or user story and produces merged, tested, documented code with full audit traceability. It maps directly to Kiro's spec-driven development workflow (requirements → design → tasks → implementation).

## Workflow Steps

1. **Parse Requirement** — Accept a natural language requirement or user story as input. Validate that the input is clear and actionable. Log the input via audit-logger MCP: `log_interaction`.

2. **Create Kiro Spec** — Use Kiro's built-in spec workflow to generate:
   - `requirements.md` — Acceptance criteria derived from the input requirement
   - `design.md` — Technical design and architecture decisions
   - `tasks.md` — Implementation task list with sub-tasks

3. **Create Restore Point** — Before implementation, use git-rollback MCP: `create_restore_point` to snapshot the current state.

4. **Implement Tasks** — Execute each task from the generated `tasks.md`, scoping all file writes to the `sandbox_path`:
   - Generate code that satisfies the requirement — write files only under `sandbox_path`
   - MANDATORY: Generate corresponding unit tests for every new or modified source file — write test files under `sandbox_path/tests/`. Tests must cover all new functions, endpoints, models, validation logic, and edge cases. Aim for minimum 80% line coverage on new code.
   - Run the generated tests and verify they pass before proceeding to checkpoints
   - Generate documentation describing the implemented feature — write under `sandbox_path/docs/`
   - Do NOT write any generated application code to the root of the current (orchestration) repository
   - Log each implementation step via audit-logger MCP: `log_interaction`

5. **Code Review Checkpoint** — Submit generated code to code review validation:
   - Verify correctness and adherence to project conventions
   - Verify absence of security issues
   - Verify no dead code, unused imports, or TODO/FIXME markers
   - Log result via audit-logger MCP: `log_checkpoint`

6. **Test Coverage Checkpoint** — Validate test coverage meets the minimum threshold:
   - Run all unit tests against the generated code
   - Verify minimum 80% line coverage on new code
   - Log result via audit-logger MCP: `log_checkpoint`

7. **Security Scan Checkpoint** — Run security analysis on all generated code:
   - Use security-scanner MCP: `scan_code` on all modified files
   - Use security-scanner MCP: `scan_dependencies` if new dependencies were added
   - Verify no HIGH or CRITICAL vulnerabilities
   - Log result via audit-logger MCP: `log_checkpoint`

8. **Documentation Checkpoint** — Verify all required documentation was generated:
   - All public functions, classes, and interfaces have docstrings or JSDoc comments
   - Complex logic includes inline comments explaining intent
   - README is updated if a new module or significant feature was added
   - Feature description document exists summarizing what was implemented and why
   - Log result via audit-logger MCP: `log_checkpoint`

9. **Merge** — If all checkpoints pass, commit and push the code to the target branch. Log the merge event via audit-logger MCP: `log_event`.

10. **Audit Log** — Record the complete workflow execution summary via audit-logger MCP: `log_event` with event_type `workflow_end`, including all checkpoint results and output artifacts.

## Checkpoints (MUST pass before merge)

- [ ] **Code Review**: Generated code passes review for correctness, conventions, and security
- [ ] **Test Coverage**: Minimum 80% line coverage on new code; all tests pass
- [ ] **Security Scan**: No HIGH or CRITICAL vulnerabilities from security-scanner MCP
- [ ] **Documentation**: All public APIs documented, inline comments on complex logic, README updated if applicable, feature description present

## If Any Checkpoint Fails

STOP. Do NOT proceed with the merge. Report failure details including:
- Which checkpoint failed
- Specific failure reasons and validation details
- Suggested remediation steps

Use git-rollback MCP: `rollback` to restore the previous state if needed.
Log the failure via audit-logger MCP: `log_checkpoint` with `passed: false`.

## Expected Inputs

- Natural language requirement or user story (plain text)
- Target module or project path (optional, defaults to sample-app)

## Expected Outputs

- Implemented source code satisfying the requirement
- Unit tests with minimum 80% coverage
- Feature documentation (inline docs, README updates)
- Audit trail of all interactions, checkpoints, and decisions

## MCP Server Dependencies

- **audit-logger**: `log_interaction`, `log_checkpoint`, `log_event`
- **security-scanner**: `scan_code`, `scan_dependencies`
- **git-rollback**: `create_restore_point`, `rollback`
