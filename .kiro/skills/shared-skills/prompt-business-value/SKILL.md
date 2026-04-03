---
name: prompt-business-value
description: Iterate over Jira issues and returns the business value of each. Used as a subagent.
compatibility: Requires docker engine and Jira MCP server authenticated with Personal Access Token (PAT).
metadata:
  author: connected-operations
  version: "1.0"
---

# Iterate over Jira issues to get business value

Iterate over the Jira issues to get business value

**Requires**: docker engine to run jira mcp server
**Requires**: Jira mcp authenticated with Personal Access Token (PAT)

**Inputs**:
- The list of jira issues containing the issue ´´´ids´´´
- The ```Fields```to calculate the business value

**Output**: Writes the business summary into output.csv

## Workflow

### 1. Get Business Value for each jira issue

Iterate over each jira issue:

1. Query using ```get_issue_full``` tool and focus on the ```Fields```
2. Get its business value using this prompt:

    Given the ```Fields```,
    write a single clear paragraph of max 120 words, summarizing the business impact
    they imply for the organization, focusing on how they will improve
    processes, reduce costs, or remove blockers. If the Acceptance
    Criteria is vague or undefined, infer likely business impacts
    based on the Benefit Hypothesis while stating assumptions made,
    but do not simply return TBD. Use straightforward, business-friendly
    language. If really there is no information at all, return TBD.
    Do not include assumptions.

3. Then write to file
    - issue ```id```
    - issue ```title```
    - ```business_value```

   Using this command ```id, title, business_value >> output.csv```
