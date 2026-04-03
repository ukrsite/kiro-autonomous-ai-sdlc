---
name: release-notes
description: Generates release notes from Jira using JQL. Extracts business value from Description, Benefit Hypothesis, and Acceptance Criteria. Outputs Markdown and DOCX (Simple Table or template-based). Use when the user wants release notes for a fixVersion, PI, or scope, or mentions JQL, business value summaries, or Word/Template documents.
compatibility: Requires Docker (Jira MCP with Jira PAT), Python 3 with python-docx/docxtpl for DOCX generation.
metadata:
  author: stanislav.kostenich.ext@ericsson.com
  version: "1.0.0"
---

# Release notes generation from Jira issues

This skill implements the **UC Release Notes Generator** use case that the product-owner agent relies on.

## High-level behavior

1. Accept a JQL query describing the release scope (project, fixVersion, status, etc.).
2. Use Jira MCP (`get_all_issues` + `get_issue_full` when needed) to fetch all matching issues efficiently.
3. Let the user choose which Jira fields to use for business value extraction.
4. Generate **business value paragraphs (80–120 words, 4–6 sentences)** per issue.
5. Write all enriched issues to `release_notes_data.json`.
6. Produce:
   - **Markdown release notes**, and
   - Optionally **DOCX** in:
     - **Simple Table** format, or
     - **Template-based** format using the `docx-releasenotes-template` skill.

The product-owner agent should call this skill whenever the user asks to “create release notes” or similar.

## Agent behavior when invoked

1. **Read this SKILL** and follow the workflow below.
2. **For DOCX (Word):** Use the **docx-releasenotes-template** skill for both Simple Table and Template formats. Template selection (list templates, ask user, never auto-select) is defined in that skill — follow it exactly.

## Quick Start

1. User provides JQL (e.g. `project="NDPF" AND fixVersion = "ID 25.4.2 - Nov 28"`)
2. Validate with `search_issues` (max_results=10)
3. Offer field options: (A) All custom: Description, Benefit Hypothesis, Acceptance Criteria — recommended; (B) Description only; (C) Specify which field(s)
4. Fetch all issues via `get_all_issues` (one JQL call — faster); use `get_issue_full` per issue only if response lacks fields
5. Extract selected fields, generate business_value (80–120 words), write `release_notes_data.json`
6. Generate Markdown; offer DOCX (Simple or Template)

**Critical:** Write `release_notes_data.json` before running any scripts. Scripts hang without `--file`. See [error-handling.md](references/error-handling.md).

## Workflow

### 1. JQL Query

Recommend: `project="..." AND fixVersion = "..." AND status = Done`

**Sprint queries:** Often fail. Try `sprint = "Name"` or `Sprint in ("Name")`; prefer `fixVersion` or date range. See [jql-fix.md](references/jql-fix.md).

**Validation:** Run `search_issues` with max_results=10. On 400, follow [jql-fix.md](references/jql-fix.md). On success, show count, ask to proceed. Warn if >500 issues.

### 2. Fields for Business Value

**Offer user:**
- **A)** Use all relevant Description, Benefit Hypothesis, Acceptance Criteria fields (recommended — provides most comprehensive business value)
- **B)** Use only specific field — `description`
- **C)** Use only specific field(s) — please specify which one(s)

| Field | Internal |
|-------|----------|
| Benefit hypothesis | `customfield_36211` |
| Acceptance criteria | `customfield_12818` |
| Description | `description` |

Fewer fields → shorter output.

See [business-value.md](references/business-value.md).

### 3. Output Path

Recommend: `release-notes/PMS_19.3.1_Release_Notes.md`

### 4. Process Issues

**Order:** (1) search_issues to validate (2) get_all_issues with same JQL — fetches all issues in one call; only use get_issue_full per issue if get_all_issues returns thin data without fields.components/description (3) generate business_value (4) fs_write release_notes_data.json (5) run scripts with `--file`

**Component extraction:** See [component-extraction.md](references/component-extraction.md). Use `fields.components`, join with `", "`.

**Large datasets:** See [batch-processing.md](references/batch-processing.md) and [context-management.md](references/context-management.md).

### 4b. Production Bugs (optional)

If the user wants **production bugs resolved per release** included:

1. Ask: "Include production bugs in this release?"
2. If yes: run a **second JQL query** for production bugs (same project, same fixVersion). See [production-bugs-definition.md](references/production-bugs-definition.md).
3. Validate with `search_issues`, then fetch with `get_all_issues`.
4. Add to `release_notes_data.json` under `production_bugs` array. Each bug: `key`, `title` (or `summary`), `status`, optional `business_value`, optional `component`.
5. The DOCX template will render a dedicated "Production Bugs Resolved" section when `production_bugs` is present.

### 5. Generate Markdown

- Header (version, date, project)
- Overview, issues (key, title, status, business_value), summary
- For 100+ issues: aggregated summary; see [batch-processing.md](references/batch-processing.md)

### 6. Offer DOCX

Always offer after Markdown: "(1) Simple Table (2) Template — choose from available templates"

Full workflow: [docx-workflow.md](references/docx-workflow.md).

**Template JSON:** Keep full get_issue_full; add business_value; use `key` not `issue_key`; use `summary` or `title` for issue title (from `fields.summary`). Output only `business_value` (no business_impact). Include `fields.components`. All JQL issues as top-level — do not nest. Escape `"` as `\"` in JSON (Jira text often has quotes).

**Scripts (from project root):** Simple Table DOCX uses `generate_release_notes.py` from docx-releasenotes-template; Template DOCX uses the pipeline below.

```bash
# Simple Table
python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_release_notes.py --file release_notes_data.json

# Template pipeline
python3 .kiro/skills/shared-skills/release-notes/scripts/process_release_notes.py --file release_notes_data.json | python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py
```

**Do NOT:** Run scripts without JSON; use Node.js; embed JSON in Python. **ALWAYS:** Write JSON first; use `--file`.

## Jira Field Mapping (Business Value)

Options: (A) All custom: Description, Benefit Hypothesis, Acceptance Criteria; (B) Description only; (C) Specify which field(s).

| Display | Internal |
|---------|----------|
| Description | `description` |
| Benefit Hypothesis | `customfield_36211` |
| Acceptance Criteria | `customfield_12818` |
| Components | `components` (array) |
| Fix Version | `fixVersions` |
| Labels | `labels` |

## Query Examples

```jql
# By fix version
project="Network Deployment Portfolio" AND fixVersion = "ID 25.4.2 - Nov 28" AND status = Done

# By date
project = ADPPRG AND status = Done AND updated >= "2026-01-01" AND updated <= "2026-02-14"

# By component
project = ADPPRG AND component = "Oversite" AND status IN (Done, Closed)

# By labels
project = ADPPRG AND labels = "Sprint42" AND status = Done

# Production bugs — IDE2E (uses affectedVersion, NOT fixVersion)
project = IDE2E AND issuetype = Bug AND affectedVersion = "ID E2E 25.4.2" AND status IN (Done, Resolved, Closed)

# Production bugs — ESDT (uses customfield_51018 for Prod env)
project = ESDT AND issuetype = Bug AND customfield_51018 = "523431" AND status IN (Done, Resolved, Closed)
```

## References

- [business-value.md](references/business-value.md) — Extraction, verification
- [jql-fix.md](references/jql-fix.md) — JQL troubleshooting
- [component-extraction.md](references/component-extraction.md) — Component field
- [batch-processing.md](references/batch-processing.md) — Large datasets
- [context-management.md](references/context-management.md) — Size strategies
- [docx-workflow.md](references/docx-workflow.md) — DOCX steps
- [error-handling.md](references/error-handling.md) — Common errors
- [llm-prompting.md](references/llm-prompting.md) — Business value generation
- [production-bugs-definition.md](references/production-bugs-definition.md) — Production bugs JQL and workflow