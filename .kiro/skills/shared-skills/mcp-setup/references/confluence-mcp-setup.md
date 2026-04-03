# Confluence MCP Server Setup

Interactive setup guide for configuring Confluence MCP credentials.

## Workflow

### Step 1: Guide user to create Confluence token

Tell the user:
> Open this URL in your browser:
> https://eteamspace.internal.ericsson.com/plugins/personalaccesstokens/usertokens.action
> 
> Let me know when you're there.

Wait for user confirmation.

### Step 2: Walk through token creation

Once user confirms, instruct:
> On that page:
> 1. Click **"Create token"**
> 2. Token name: `Kiro Agent`
> 3. Click **"Create"**
> 4. Copy the token
> 
> Let me know when you have the token copied.

Wait for user confirmation.

### Step 3: Get token from user

Ask:
> Please paste your Confluence token here.

User will provide the token.

### Step 4: Test and save token

Run this command with the user's token:

```bash
CONFLUENCE_ETEAM_TOKEN="<user_token>"
echo "Testing Confluence MCP..." && \
docker run --rm -i \
  -e CONFLUENCE_ETEAM_TOKEN="$CONFLUENCE_ETEAM_TOKEN" \
  -e CONFLUENCE_ETEAM_URL="https://eteamspace.internal.ericsson.com" \
  -e CONFLUENCE_MCP_LOG_LEVEL="INFO" \
  -e ANALYTICS_USERNAME="$USER" \
  armdocker.rnd.ericsson.se/proj-cat-released/confluence-mcp-server:latest \
  <<< '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

If output contains "Confluence MCP Server initialized successfully", save token:

```bash
SHELL_PROFILE="${HOME}/.$(basename $SHELL)rc"
cat >> "$SHELL_PROFILE" << EOF
export CONFLUENCE_ETEAM_TOKEN="$CONFLUENCE_ETEAM_TOKEN"
export CONFLUENCE_ETEAM_URL="https://eteamspace.internal.ericsson.com"
export CONFLUENCE_MCP_LOG_LEVEL="INFO"
EOF
```

### Step 5: Confirm completion

Tell user:
> ✅ Setup complete! Your Confluence token has been saved.
> 
> Restart your Kiro agent to use Confluence MCP features.
