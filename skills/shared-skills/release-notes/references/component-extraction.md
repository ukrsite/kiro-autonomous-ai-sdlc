# Component Field Extraction

Extract from `issue['fields']['components']`, join with `", "`.

```python
components = ""
for c in issue['fields']['components']:
    components += (", " if components else "") + c['name']
processed_issue['component'] = components
```

**Examples:** Single `"Oversite"`, multiple `"Oversite, Sitetracker"`, none `""`.

**Do NOT:** Use `customfield_XXXXX`, `labels`, or `components[0]['name']` only.
