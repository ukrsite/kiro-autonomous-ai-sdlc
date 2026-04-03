# JQL Query Fixer

Diagnoses and fixes JQL query errors through systematic troubleshooting.

## When to Use

- JQL query returns 400 Bad Request error
- Sprint queries fail
- Query returns 0 results unexpectedly
- Need to optimize query for large datasets
- User reports query doesn't match expected issues

## Workflow

### 1. Capture the Error Context

Collect:
- The failing JQL query
- The error message (if any)
- What the user is trying to achieve
- Expected vs actual result count

### 2. Test Basic Connectivity

Try simplest query first:
```jql
project = PROJECTKEY
```

If this fails → Authentication or connection issue
If this works → Problem is with specific filters

### 3. Diagnose Sprint Query Issues

If query contains "sprint" or "Sprint":

**Try these in order:**

A. **Quoted sprint name:**
```jql
project = X AND sprint = "Sprint Name"
```

B. **Sprint IN clause:**
```jql
project = X AND Sprint in ("Sprint Name")
```

C. **Ask user for alternatives:**
- "Do you have a fixVersion that corresponds to this sprint?"
- "Is there a label used for this sprint?"
- "What are the start and end dates for this sprint?"
- "Which components or teams worked on this sprint?"

D. **Suggest alternative filters:**
- fixVersion: `fixVersion = "Sprint 42 Release"`
- labels: `labels = "Sprint42"`
- date range: `resolved >= "2026-01-01" AND resolved <= "2026-02-14"`
- components: `component IN ("Team1", "Team2")`

### 4. Build Query Incrementally

Start simple and add filters one at a time:

**Step 1:** Base query
```jql
project = ADPPRG
```

**Step 2:** Add status
```jql
project = ADPPRG AND status = Done
```

**Step 3:** Add date or version
```jql
project = ADPPRG AND status = Done AND fixVersion = "Version"
```

Test after each addition to identify problematic filter.

### 5. Handle Large Datasets

If query returns 1000+ issues:

**Recommend filters:**
- Status: `AND status IN (Done, Closed)`
- Priority: `AND priority IN (High, Critical)`
- Type: `AND issuetype IN (Story, Bug, Epic)`
- Date: `AND resolved >= "YYYY-MM-DD"`

**Explain trade-offs:**
- Processing 1000+ issues takes significant time
- Filtering by status focuses on completed work
- Can process in batches if needed

### 6. Provide Solution

Based on diagnosis, provide:
1. **Working JQL query** (tested with max_results=10)
2. **Expected result count** from test
3. **Explanation** of what was wrong and how it was fixed
4. **Alternative approaches** if primary solution has limitations

### 7. Confirm with User

Before proceeding with full processing:
- Show the working query
- Display total issue count
- Show 2-3 sample issue keys
- Ask for confirmation to proceed

## Common Fixes

### Fix 1: Sprint Field Not Recognized
**Problem:** `sprint = "Sprint 42"` returns 400
**Solution:** Use alternative filter
```jql
project = X AND fixVersion = "Sprint 42" AND status = Done
```

### Fix 2: Case Sensitivity
**Problem:** Field name case is wrong
**Solution:** Try both cases
- `sprint` vs `Sprint`
- `status` vs `Status`
- `fixVersion` vs `fixversion`

### Fix 3: Missing Quotes
**Problem:** Values with spaces need quotes
**Solution:** Add quotes around multi-word values
```jql
fixVersion = "Sprint 42"  # Correct
fixVersion = Sprint 42    # Wrong
```

### Fix 4: Too Many Results
**Problem:** Query returns thousands of issues
**Solution:** Add status filter
```jql
project = X AND fixVersion = "Y" AND status = Done
```

### Fix 5: Custom Field Reference
**Problem:** Sprint is a custom field
**Solution:** Use custom field ID
```jql
project = X AND cf[11910] = "Sprint 42"
```

### Fix 6: Production Bugs Query
**Problem:** Need to find production bugs for a release
**Solution:** Project-specific — production bugs are typically in a different project (e.g. IDE2E, ESDT). NDPF has no Bug type.
- **IDE2E:** `project = IDE2E AND issuetype = Bug AND affectedVersion = "ID E2E 25.4.2" AND status IN (Done, Resolved, Closed)`
- **ESDT:** `project = ESDT AND issuetype = Bug AND customfield_51018 = "523431" AND status IN (Done, Resolved, Closed)`
See [production-bugs-definition.md](production-bugs-definition.md) for full project-specific JQL.

## Output Format

Provide clear, actionable response:

```
✅ **Query Fixed**

**Working Query:**
```jql
project = ADPPRG AND fixVersion = "Sprint 42" AND status = Done
```

**Results:** 156 issues found

**What was wrong:** Sprint field queries are not supported in this Jira instance. Sprint information is tracked via fixVersion field instead.

**Sample Issues:** ADPPRG-12345, ADPPRG-12346, ADPPRG-12347

**Ready to proceed?** This will process 156 issues and generate business value summaries for each.
```

## Error Prevention

Before returning a "fixed" query:
1. **Test it** with max_results=10
2. **Verify count** is reasonable (not 0, not 100,000)
3. **Check sample issues** match user's intent
4. **Explain changes** made to original query

## Escalation

If unable to fix after trying all approaches:
1. Document what was tried
2. Explain the limitation clearly
3. Offer manual workarounds:
   - User provides list of issue keys
   - User exports from Jira and provides file
   - Use broader query and filter results manually
