---
name: wf5-documentation
description: Generates comprehensive documentation from an existing codebase including API docs, architecture diagrams, and onboarding guides.
metadata:
  author: sdlc-prototype-team
  version: "1.0.0"
---

# Documentation Workflow

This workflow takes an existing codebase and generates comprehensive documentation including API docs, architecture diagrams, and onboarding guides. It validates generated documentation for accuracy and completeness, produces a delta report comparing against existing docs, and logs every step for audit traceability.

## Workflow Steps

1. **Start Workflow** — Generate a `workflow_id` using the pattern `wf5-{issue-key-or-short-description}` (e.g. `wf5-api-docs-refresh`). Log workflow start immediately via audit-logger MCP: `log_event` with `event_type: "workflow_start"`, including the target codebase path and documentation types in `details`. Record this `workflow_id` — it must be used consistently for every subsequent audit-logger and finops call in this workflow.

   **MANDATORY**: This MCP call MUST succeed before proceeding. Do NOT substitute writing to `aidlc-docs/audit.md`.

2. **Analyze Codebase** — Accept a target codebase path and documentation types to generate (`api`, `architecture`, `onboarding`) as input. Scan the codebase to identify public interfaces, module structure, dependencies, and existing documentation. Log the analysis via audit-logger MCP: `log_interaction`.

3. **Generate API Documentation** — When `api` is requested, generate documentation covering all public interfaces:
   - Document all public functions, classes, methods, and interfaces
   - Include parameter descriptions, return types, and usage examples
   - Document error handling and exception behavior
   - Organize by module and namespace
   - Follow standards defined in `references/doc-standards.md`
   - Log generation via audit-logger MCP: `log_interaction`

4. **Generate Architecture Diagrams** — When `architecture` is requested, generate diagrams representing the system structure:
   - Component dependency diagrams (Mermaid format)
   - Module interaction diagrams
   - Data flow diagrams for key workflows
   - Layer diagrams showing system architecture
   - Log generation via audit-logger MCP: `log_interaction`

5. **Generate Onboarding Guides** — When `onboarding` is requested, generate guides for new developers:
   - Project setup and installation instructions
   - Development environment configuration
   - Codebase navigation guide (key directories, entry points)
   - Common development tasks and workflows
   - Contribution guidelines and coding conventions
   - Log generation via audit-logger MCP: `log_interaction`

6. **Accuracy Validation Checkpoint** — Validate generated documentation for accuracy:
   - Verify API signatures match actual code signatures
   - Verify code examples compile or parse without errors
   - Verify referenced files and modules exist in the codebase
   - Verify dependency descriptions match actual dependency graph
   - Run `scripts/validate_docs.py` for automated accuracy checks
   - Log result via audit-logger MCP: `log_checkpoint`

7. **Completeness Review Checkpoint** — Review generated documentation for completeness:
   - Verify all public interfaces are documented (API docs)
   - Verify all major components are represented (architecture diagrams)
   - Verify all setup steps are included (onboarding guides)
   - Apply criteria from `references/completeness-criteria.md`
   - Log result via audit-logger MCP: `log_checkpoint`

8. **Generate Delta Report** — Compare generated documentation against existing documentation:
   - Identify new documentation sections not previously covered
   - Identify existing documentation that is outdated or inaccurate
   - Identify gaps where documentation is missing entirely
   - Summarize additions, updates, and removals
   - Include accuracy and completeness metrics
   - Log report via audit-logger MCP: `log_event`

9. **Audit Log** — Record the complete workflow execution summary via audit-logger MCP: `log_event` with event_type `workflow_end`, including all checkpoint results, delta report reference, and output artifacts.

    **MANDATORY**: This MCP call MUST succeed. Do NOT skip it or substitute writing to `aidlc-docs/audit.md`.

10. **Cost Report** — After logging `workflow_end`, call finops-cost-estimator MCP: `calculate_workflow_cost` using the active `workflow_id`. Then log the cost result back to the audit trail via audit-logger MCP: `log_event` with `event_type: "cost_report"`. Include the full cost breakdown table in the final response to the user per the format defined in `finops-cost-reporting.md`.

    **MANDATORY**: Both MCP calls MUST be made. Call `calculate_workflow_cost` even if the cost is zero.

## Checkpoints (MUST pass before proceeding)

- [ ] **Accuracy Validation**: Generated documentation accurately reflects the actual codebase (API signatures match, code examples are valid, references resolve)
- [ ] **Completeness Review**: Generated documentation covers all required areas per the requested doc types (see `references/completeness-criteria.md`)

## If Any Checkpoint Fails

STOP. Do NOT proceed. Report failure details including:
- Which checkpoint failed
- Specific inaccuracies or gaps found
- Which documentation sections need correction
- Suggested remediation steps

Log the failure via audit-logger MCP: `log_checkpoint` with `passed: false`.

## Expected Inputs

- Target codebase path (e.g., `sample-app/python-module/`)
- Documentation types to generate: `api`, `architecture`, `onboarding` (one or more, default: all)
- Existing documentation path (optional, for delta report comparison)

## Expected Outputs

- Generated API documentation (Markdown files)
- Generated architecture diagrams (Mermaid in Markdown)
- Generated onboarding guides (Markdown files)
- Delta report comparing generated docs against existing docs
- Audit trail of all interactions, checkpoints, and decisions

## MCP Server Dependencies

- **audit-logger**: `log_interaction`, `log_checkpoint`, `log_event`
- **finops-cost-estimator**: `calculate_workflow_cost`
