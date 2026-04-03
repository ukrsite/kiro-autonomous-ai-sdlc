# DOCX Generation Workflow

## Offer Message

After Markdown, offer: "(1) Simple Table (2) Template — choose from available templates (e.g. ESDT)"

**Prerequisites:** `pip install python-docx` (simple), `pip install docxtpl` (template)

## Script Order

1. Write `release_notes_data.json` with fs_write
2. Run script with `--file` — never without; scripts hang on stdin

## Paths (from project root)

- Simple: `python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_release_notes.py --file release_notes_data.json`
- Template: `python3 .kiro/skills/shared-skills/release-notes/scripts/process_release_notes.py --file release_notes_data.json | python3 .kiro/skills/shared-skills/docx-releasenotes-template/scripts/generate_from_template.py`

## JSON for simple DOCX (generate_release_notes.py)

- Required: `version`, `issues`
- Optional: `project` (inferred from first issue `fields.project` when missing), `date`

## JSON for template

- Keep full `get_issue_full` response; add `business_value`; use `key` not `issue_key`; use `summary` or `title` for issue title (from `fields.summary`)
- Output only `business_value` — no `business_impact` or `business_value_custom`
- Escape quotes in strings for valid JSON
- All JQL issues as top-level; optional child fetch only for extras not in JQL result

## Success Messages

Simple: `✅ Release notes generated! 📄 Markdown: ... 📄 Word (Simple): ...`
Template: `✅ Release notes generated! 📄 Markdown: ... 📄 Word (Template): ...`
