# Jira MCP Server Setup

Interactive setup guide for configuring Jira MCP credentials.

## Workflow

### Step 1: Guide user to create Jira token

Tell the user:
> Open this URL in your browser:
> https://eteamproject.internal.ericsson.com/secure/ViewProfile.jspa
> 
> Let me know when you're there.

Wait for user confirmation.

### Step 2: Walk through token creation

Once user confirms, instruct:
> On that page:
> 1. Click **"Personal Access Tokens"**
> 2. Click **"Create token"**
> 3. Copy the token
> 
> Let me know when you have the token copied.

Wait for user confirmation.

### Step 3: Get credentials from user

Ask:
> Please provide:
> 1. Your Jira API token
> 2. Your signum (for analytics tracking)

User will provide the token and signum.

### Step 4: Test and save credentials

Run this command with the user's credentials:

```bash
JIRA_ETEAM_TOKEN="<user_token>"
ANALYTICS_USERNAME="<username>"

echo "Testing Jira MCP..." && \
docker run --pull=always --init --rm -i \
  -e JIRA_ETEAM_TOKEN="$JIRA_ETEAM_TOKEN" \
  -e JIRA_ETEAM_URL="https://eteamproject.internal.ericsson.com/" \
  -e ANALYTICS_USERNAME="$ANALYTICS_USERNAME" \
  armdocker.rnd.ericsson.se/proj-cat-released/jira-mcp-server:latest <<< '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

If output contains tool list, save credentials:

```bash
SHELL_PROFILE="${HOME}/.$(basename $SHELL)rc"
cat >> "$SHELL_PROFILE" << EOF
export JIRA_ETEAM_TOKEN="$JIRA_ETEAM_TOKEN"
export ANALYTICS_USERNAME="$ANALYTICS_USERNAME"
EOF
```

### Step 5: Confirm completion

Tell user:
> ✅ Setup complete! Your Jira credentials have been saved.
> 
> Restart your Kiro agent to use Jira MCP features.
