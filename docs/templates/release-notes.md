# Release Notes — {JIRA_ISSUE_KEY}

## Summary

**Issue:** [{JIRA_ISSUE_KEY}]({JIRA_URL}/browse/{JIRA_ISSUE_KEY})
**Title:** {ISSUE_SUMMARY}
**Workflow:** {WORKFLOW_ID}
**Date:** {DATE}
**Branch:** `ai/{JIRA_ISSUE_KEY}`
**MR:** {MR_URL}

## Changes

### New Features

- {description of each new feature or endpoint}

### Modified

- {description of each modified file and what changed}

### Dependencies

- {any new or updated dependencies}

## API Changes

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| {method} | {path} | {description} | New / Modified / Deprecated |

## Breaking Changes

- None / {list any breaking changes}

## Test Coverage

| Scope | Coverage | Threshold |
|-------|----------|-----------|
| New code | {X}% | {threshold}% |
| Overall | {Y}% | — |
| Tests added | {N} | — |
| Tests passed | {N}/{N} | — |

## Security

- Bandit scan: {N} findings ({N} HIGH/CRITICAL)
- Dependency scan: {N} known CVEs

## Audit Trail

| Event | ID |
|-------|----|
| Workflow start | `{event_id}` |
| Code review | `{checkpoint_id}` |
| Test coverage | `{checkpoint_id}` |
| Security scan | `{checkpoint_id}` |
| Workflow end | `{event_id}` |

## Rollback

If issues are found after merge, revert the MR or use:
```bash
git revert ai/{JIRA_ISSUE_KEY}
```
