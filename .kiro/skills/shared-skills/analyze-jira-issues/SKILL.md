---
name: analyze-jira-issues
description: Iterate over Jira issues and creates a release notes file with the business value summary. Use when you need to create the release notes.
compatibility: Requires docker engine and Jira MCP server authenticated with Personal Access Token (PAT).
metadata:
  author: connected-operations
  version: "1.0"
---

# Iterate over Jira issues to create release notes

Iterate over the Jira issues required to be included in release notes.

**Requires**: docker engine to run jira mcp server
**Requires**: Jira mcp authenticated with Personal Access Token (PAT)

## Workflow

### 1. Prompt user for JQL query

- `jql` - what jira tickets should be analyzed:

Recommend to filter by project and fixVersion like JQL ```project = ADPPRG AND fixVersion = "PMS 19.3.1" ```  

Confirm JQL can be executed using jira tool ```search_issues``` with 10 max_results. Promt for a different JQL when it fails.

Warn the user if the number of issues is greater than 500.

### 2. Prompt user for Jira Fields to get Business Value

- `fields` - what jira fields should be analyzed?

Recommend to select description field ```Description ```  

Check the Fields exist using jira tool ```get_issue_full``` for one of the issues retreived from previous JQL. Promt for different fields when it fails.

### 3. Get Business Value for each jira issue

Execute JQL using jira ````search_issues``` and using max_results=5

For each block of 5 issues do:

1. Spawn a new subagent using ```prompt-business-value``` skill
2. The input are the jira issues
3. The output are the business value of each issue

When concluded write a release notes file with the summary.
