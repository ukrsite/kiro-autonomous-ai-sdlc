# Production Bugs Definition and JQL

This reference defines how to identify **production bugs resolved per release** and how to query them in Jira.

**Important:** Production bugs are typically tracked in a **different project** than the main release (e.g. NDPF initiatives). Verify which project tracks bugs for your release scope.

---

## Project-Specific Configurations

### NDPF (Network Deployment Portfolio)

**Production bugs are NOT tracked in NDPF.**

- NDPF has no "Bug" issue type
- NDPF contains Initiatives, Test Plans, and other non-bug types
- Use IDE2E or ESDT for production bugs depending on release scope

### IDE2E (Intelligent Deployment E2E)

**Project:** Intelligent Deployment E2E (IDE2E)  
**Issue Type:** Bug  
**Tracking method:** `affectedVersion` (NOT fixVersion)

**Version format:** `"ID E2E 25.4.2"` (note: not "ID 25.4.2 - Nov 28" as in NDPF)

**JQL for production bugs per release:**
```jql
project = IDE2E AND issuetype = Bug 
AND affectedVersion = "ID E2E {RELEASE_VERSION}" 
AND status IN (Done, Resolved, Closed)
```

Replace `{RELEASE_VERSION}` with the version number (e.g. `25.4.2` → `"ID E2E 25.4.2"`).

**Version mapping:** NDPF release "ID 25.4.2 - Nov 28" → IDE2E version "ID E2E 25.4.2"

**Optional:** Some bugs have label `EGProd`; many mention "EGProd" in summary/description.

### ESDT

**Project:** ESDT  
**Issue Type:** Bug  
**Tracking method:** Custom field `customfield_51018` (Environment)

**Production indicator:** Environment = "Prod" (id: "523431")

**JQL for production bugs:**
```jql
project = ESDT AND issuetype = Bug AND customfield_51018 = "523431"
```

Or using cf syntax:
```jql
project = ESDT AND issuetype = Bug AND cf[51018] = "523431"
```

**Scoped by release:** Add fixVersion or affectedVersion if you need bugs for a specific release:
```jql
project = ESDT AND issuetype = Bug AND customfield_51018 = "523431" 
AND fixVersion = "YOUR_RELEASE" AND status IN (Done, Resolved, Closed)
```

**Other values:** "Test" (id: "523127") = test environment bugs.

---

## General Verification Checklist

When using a project not listed above, verify:

- [ ] **Issue type** — Is there a "Bug" type? What is the exact name?
- [ ] **Tracking field** — fixVersion, affectedVersion, or custom field?
- [ ] **Environment/Production** — Labels, custom fields (e.g. Environment), or components?
- [ ] **Status** — How bugs move to Done/Resolved/Closed
- [ ] **Version format** — Exact string format for the project

---

## Definition Options (Generic)

| Option | JQL approach | Notes |
|--------|--------------|-------|
| **Label** | `labels = "production"` or `labels = "EGProd"` | Simple; requires consistent labelling |
| **Issue type + label** | `issuetype = Bug AND labels = "production"` | Common combination |
| **Affected version** | `affectedVersion = "Release Name"` | Used by IDE2E |
| **Custom field** | `customfield_51018 = "523431"` | ESDT Environment field |
| **Component** | `issuetype = Bug AND component = "Production"` | If components track environment |

---

## Workflow Integration

1. **Identify project** — Production bugs for NDPF releases come from IDE2E or ESDT, not NDPF.
2. **Map version** — NDPF "ID 25.4.2 - Nov 28" → IDE2E "ID E2E 25.4.2" (extract major.minor.patch).
3. Ask user: "Include production bugs in this release?"
4. If yes, run the **appropriate JQL** for IDE2E or ESDT (based on release scope).
5. Validate with `search_issues` (max_results=10), then fetch with `get_all_issues`.
6. Merge into `release_notes_data.json` under the `production_bugs` key.
7. The DOCX template will render a dedicated "Production Bugs Resolved" section.
