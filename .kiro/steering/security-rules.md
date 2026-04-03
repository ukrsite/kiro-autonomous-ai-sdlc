---
inclusion: always
---

# Security Rules

## Mandatory Security Checks

1. **No hardcoded secrets**: Never include API keys, passwords, tokens, or credentials in code.
2. **No production access**: Never access production systems, databases, or APIs from sandbox code.
3. **Input validation**: All user inputs must be validated and sanitized.
4. **Dependency security**: All dependencies must be scanned for known CVEs before use.
5. **SQL injection prevention**: Use parameterized queries. Never concatenate user input into SQL.

## Before Any Merge

- Run security-scanner MCP `scan_code` tool on all modified files
- If any HIGH or CRITICAL vulnerabilities found, BLOCK the merge
- Log scan results via audit-logger MCP `log_checkpoint` tool
