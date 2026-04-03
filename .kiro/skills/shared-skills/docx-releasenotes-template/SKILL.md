---
name: docx-releasenotes-template
description: Generates Word release notes from a template and JSON data. Creates documents with business requirements, business impacts, and descriptions grouped by component. Supports multiple templates (ESDT, Intelligent Deployment, etc.). Use when generating Word release notes, using a DOCX template, or when the user mentions ESDT Release Notes, template-based DOCX, or Word output.
compatibility: Requires Python 3 with docxtpl package (pip install docxtpl).
metadata:
  author: stanislav.kostenich.ext@ericsson.com
  version: "1.0.0"
---

# Generate DOCX from Template

Generate professionally formatted Word documents from a template and JSON data. Choose from available templates (e.g. ESDT Release Notes Template).

## Quick Start

**CRITICAL: Use Python only — NO Node.js.** Run from project root with `python3`.

```bash
# Basic usage (recommended)
python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py --file release_notes_data.json

# With custom output path
python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py --file release_notes_data.json --output release-notes/Release_Notes.docx

# With custom template
python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py --file release_notes_data.json --template /path/to/template.docx
```

Output: `Release_Notes_{version}.docx` in current directory

## Prerequisites

```bash
pip install docxtpl
```

## Input Requirements

**Required JSON fields:**
- `version`: Release version string
- `date`: Release date string
- `issues`: Array of issue objects OR `processed_issues`: Processed format

**Required issue fields:**
- `key`: Jira issue key
- `title`: Issue summary

**Optional issue fields:**
- `status`, `business_value`, `component`, `ndsd_ticket`, `child_issues`, `fix_version`

**Optional top-level field:**
- `production_bugs`: Array of production bugs resolved in this release (see release-notes [production-bugs-definition.md](../release-notes/references/production-bugs-definition.md))

See [input-formats.md](references/input-formats.md) for detailed format examples.

## Document Structure

The generated document includes:

1. **Business Requirements** - All issues with keys and titles
2. **Business Impacts** - Grouped by component with business value summaries (80-120 words)
3. **Descriptions** - Grouped by component with titles and status
4. **Production Bugs Resolved** - When `production_bugs` is provided (optional)

Issues are deduplicated across components (multi-component groups take precedence).

## Template Location and Selection

**Paths:** When installed to project (`.kiro/`): `skills/shared-skills/docx-releasenotes-template/` lives under `.kiro/skills/`. When installed globally (`~/.kiro/`): use `~/.kiro/skills/shared-skills/docx-releasenotes-template/`.

Templates folder: `.kiro/skills/shared-skills/docx-releasenotes-template/assets/templates/` (or `~/.kiro/...` for global install).
Typical contents of the `assets/templates` folder:
- `ESDT Release Notes Template.docx` (default)
- `Intelligent Deployment YY.H.N Release Notes Template.docx`
- `Not AI release notes template v2.0.docx`

**How to select a template (required behavior):**
1. List all `.docx` files in the `assets/templates` folder.
2. Present them to the user as a **numbered list**, for example:
   - `1. ESDT Release Notes Template.docx`
   - `2. Intelligent Deployment YY.H.N Release Notes Template.docx`
   - `3. Not AI release notes template v2.0.docx`
3. Ask explicitly: **"Which template number should I use? (1, 2, 3, ...)"**
4. Wait for the user’s answer, then call:

   ```bash
   python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py \
     --file release_notes_data.json \
     --template ".kiro/skills/shared-skills/docx-releasenotes-template/assets/templates/<chosen_filename>.docx"
   ```

5. **Never auto-select a template** without user confirmation.

If no templates are present, add your own `.docx` template files to this folder or pass an absolute path via `--template /path/to/your/template.docx`.

See [templates.md](references/templates.md) for placeholder requirements and custom template creation.

## Pipeline Integration

- **Option A (Pipeline):** Use when JSON has raw Jira structure — run release-notes `process_release_notes.py` first, pipe output to `generate_from_template.py`.
- **Option B (Direct):** Use when JSON is already in expected format (e.g. from release-notes workflow or pre-processed).

```bash
# Option A: Pipeline (raw Jira structure)
python3 .kiro/skills/shared-skills/release-notes/scripts/process_release_notes.py --file release_notes_data.json | python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py

# Option B: Direct (pre-processed JSON)
python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py --file release_notes_data.json
```

## Common Issues

- **Template not found**: Verify template exists at default path or use `--template`
- **Invalid JSON**: Check for unescaped quotes in strings
- **Missing fields**: Ensure `version`, `date`, and `issues` are present

See [error-handling.md](references/error-handling.md) for complete troubleshooting guide.

## Output

**Success:**
- Filename printed to stdout
- Exit code 0
- File created in current directory

**Error:**
- Error message to stderr
- Non-zero exit code

## Tips

- Use `--file` flag to avoid stdin blocking
- Include `component` field for proper grouping
- Business value format: 80–120 words, 4–6 sentences (see release-notes skill [business-value.md](../release-notes/references/business-value.md))
- Component names are sorted alphabetically

## Dependencies

- **docxtpl**: Template rendering
- **python-docx**: Word document manipulation (installed with docxtpl)
- **jinja2**: Template engine (installed with docxtpl)
