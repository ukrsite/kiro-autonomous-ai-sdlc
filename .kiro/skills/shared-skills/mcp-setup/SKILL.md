---
name: mcp-setup
description: Configure MCP servers for Kiro agents. Guides users through environment variable setup, Docker configuration, and MCP server verification. Use when skills require MCP dependencies or when users need to set up Jira, GitLab, Confluence, or other MCP servers.
metadata:
  author: connected-operations
  version: "1.0"
---

# MCP Server Setup

Configure Model Context Protocol (MCP) servers for Kiro agents.

## Available MCP Servers

| MCP Server | Purpose | Required By |
|------------|---------|-------------|
| [Jira](#jira-mcp) | Query Jira issues, create release notes | `analyze-jira-issues` |
| [GitLab](#gitlab-mcp) | Manage GitLab repositories, MRs, issues | Various GitLab operations |
| [Confluence](#confluence-mcp) | Access Confluence pages and spaces | Documentation access |

## Workflow

### 1. Identify Required MCP

**Ask user:** "Which MCP server do you need to set up?"

Options:
- `jira` - For Jira integration
- `gitlab` - For GitLab integration
- `confluence` - For Confluence integration

### 2. Run Setup for Specific MCP

Follow the setup guide for the selected MCP server:

- **Jira MCP** → See [references/jira-mcp-setup.md](references/jira-mcp-setup.md)
- **GitLab MCP** → See [references/gitlab-mcp-setup.md](references/gitlab-mcp-setup.md)
- **Confluence MCP** → See [references/confluence-mcp-setup.md](references/confluence-mcp-setup.md)

### 3. Verify Setup

After configuration, run the verification commands from the specific MCP setup guide to confirm everything works.

### 4. Restart Terminal

After bash profile configuration, instruct the user:

> Please restart your terminal to load the new environment variables, then restart Kiro to use the MCP features.
