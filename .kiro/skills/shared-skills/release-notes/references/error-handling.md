# Common Error Scenarios and Solutions

## JQL Query Errors (400)

Follow [jql-fix.md](jql-fix.md). Quick checks: field names (sprint vs Sprint), custom field syntax, try simpler query first.

## Sprint Field Issues

Sprint fields vary by instance. Prefer fixVersion: `project = X AND fixVersion = "Version Name"` or date ranges.

## Large Dataset Performance

Add status filter, process in batches of 100–200, show progress, offer partial results.

## Missing Field Data

Use fallbacks (N/A, Unassigned, TBD). Check field exists in schema. Document missing fields.

## API Rate Limiting

Add 1–2s delays between batches, reduce batch size, save progress, resume from last batch.

## Component Grouping Issues

**Symptom:** Issues under wrong component (e.g. "ECO Integration" instead of "Oversite, Sitetracker").

**Fix:** Extract from `issue['fields']['components']`, join with `", "`:
```python
components = ""
for c in issue['fields']['components']:
    components += (", " if components else "") + c['name']
processed_issue['component'] = components
```

Do NOT use labels, custom fields, or different separators.
