# Input Format Reference

The script supports two input formats for release notes data.

## Format 1: Simple Format (Direct Issues Array)

Use this format when you have pre-processed issue data:

```json
{
  "version": "ID 25.4.2 - Nov 28",
  "date": "2026-02-20",
  "issues": [
    {
      "key": "ADPPRG-282639",
      "title": "PMS 18.3.1 Upgrade",
      "status": "Backlog",
      "business_value": "This upgrade reduces operational costs by 15%.",
      "component": "PMS",
      "ndsd_ticket": "NDSD-12345",
      "child_issues": []
    }
  ]
}
```

## Format 2: Jira Processor Format

Use this format when piping from `process_release_notes.py`:

```json
{
  "version": "ID 25.4.2 - Nov 28",
  "date": "2026-02-20",
  "processed_issues": {
    "all": [
      {
        "key": "ADPPRG-282639",
        "title": "PMS 18.3.1 Upgrade",
        "status": "Backlog",
        "business_value": "This upgrade reduces operational costs by 15%.",
        "component": "PMS",
        "ndsd_ticket": "NDSD-12345",
        "child_issues": [
          {
            "key": "ADPPRG-282640",
            "title": "Database Migration",
            "status": "Done",
            "business_value": "Enables faster queries."
          }
        ]
      }
    ],
    "by_component": {
      "PMS": [
        {
          "key": "ADPPRG-282639",
          "title": "PMS 18.3.1 Upgrade",
          "status": "Backlog",
          "business_value": "This upgrade reduces operational costs by 15%.",
          "component": "PMS",
          "ndsd_ticket": "NDSD-12345",
          "child_issues": [...]
        }
      ]
    }
  }
}
```

## Field Descriptions

### Top-Level Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `version` | Yes | string | Release version (e.g., "ID 25.4.2 - Nov 28") |
| `date` | Yes | string | Release date (e.g., "2026-02-20") |
| `issues` | Yes* | array | Array of issue objects (Format 1) |
| `processed_issues` | Yes* | object | Processed issues with grouping (Format 2) |
| `production_bugs` | No | array | Production bugs resolved in this release (see release-notes production-bugs-definition) |

*Either `issues` or `processed_issues` is required, not both.

### Issue Object Fields

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| `key` | Yes | string | - | Jira issue key (e.g., "NDPF-844") |
| `title` | Yes | string | - | Issue summary |
| `status` | No | string | "Unknown" | Issue status (e.g., "Done", "Backlog") |
| `business_value` | No | string | "" | Business value summary (80-120 words recommended) |
| `component` | No | string or array | "" | Component name. Use string (e.g., "PMS", "Oversite, Sitetracker") or array of strings. Jira format `[{"name":"X"}]` is auto-normalized. **Do not use list as dict key** — script converts to string. |
| `ndsd_ticket` | No | string | null | NDSD ticket reference (e.g., "NDSD-12345") |
| `child_issues` | No | array | [] | Array of child issue objects with same structure |
| `fix_version` | No | string | null | Fix version from Jira |

### production_bugs Array (Optional)

When `production_bugs` is provided, a dedicated "Production Bugs Resolved" section is rendered in the DOCX (if the template includes `{{ Replace_Production_Bugs }}`). Each bug object should have:

| Field | Required | Description |
|-------|----------|-------------|
| `key` | Yes | Jira issue key |
| `title` / `summary` | Yes | Bug summary |
| `status` | No | e.g. Done, Resolved |
| `business_value` | No | Brief fix description |

## Alternative Field Names

The script accepts alternative field names for compatibility:

- `version`: Can also be `release_info.version`, `release_version`
- `date`: Can also be `release_info.date`, `release_date`
- `key`: Can also be `issue_key`
- `title`: Can also be `summary`

## Component Deduplication

When an issue has multiple components (e.g., "Oversite, Sitetracker"):

1. Issue appears in multi-component group: "Oversite, Sitetracker"
2. Issue is removed from single-component groups: "Oversite" and "Sitetracker"
3. This prevents duplicate entries while preserving multi-component relationships

**Example:**
- Issue NDPF-709 has components: "Oversite, Sitetracker"
- Result: Appears only in "Oversite, Sitetracker" section
- Not duplicated in separate "Oversite" or "Sitetracker" sections

## Child Issues

Child issues are displayed under their parent with:
- Bullet point format: `• KEY: Summary`
- Business value (if provided)
- Indented under parent issue

Example output:
```
• NDPF-844: Parent Issue Title

Business value for parent issue...

  • NDPF-845: Child Issue Title
  
  Business value for child issue...
```

## Business Value Guidelines

- **Length**: 80-120 words
- **Structure**: 4-6 sentences
- **Content**: Focus on business impact, cost savings, risk reduction, or capability enablement
- **Tone**: Professional, factual, outcome-focused

Good example:
```
This integration enables the legacy MANA ST instance with Global ST package to leverage Oversite functionality through standard APIs via the ID integration architecture on AWS ML. The solution ensures seamless integration between ECO, ID ST, and Americas teams for the hybrid NA01 instance. This enabler is critical for North American customers to implement Oversite capabilities on their existing infrastructure.
```

Poor example:
```
Adds new feature.
```
