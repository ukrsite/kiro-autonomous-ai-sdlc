# GitLab MCP Server Setup

Interactive setup guide for configuring GitLab MCP credentials.

## Workflow

### Step 1: Guide user to create GitLab token

Tell the user:
> Open this URL in your browser:
> https://gitlab.internal.ericsson.com/-/user_settings/personal_access_tokens
> 
> Let me know when you're there.

Wait for user confirmation.

### Step 2: Walk through token creation

Once user confirms, instruct:
> On that page:
> 1. Click **"Add new token"**
> 2. Token name: `Kiro Agent`
> 3. Select scopes: `api`, `read_repository`, `write_repository`
> 4. Click **"Create personal access token"**
> 5. Copy the token
> 
> Let me know when you have the token copied.

Wait for user confirmation.

### Step 3: Get token from user

Ask:
> Please paste your GitLab token here.

User will provide the token.

### Step 4: Test and save token

Run this command with the user's token:

```bash
GITLAB_TOKEN="<user_token>"
echo "Testing GitLab MCP..." && \
docker run --rm \
  -e GITLAB_TOKEN="$GITLAB_TOKEN" \
  -e GITLAB_HOST="gitlab.internal.ericsson.com" \
  armdocker.rnd.ericsson.se/proj-cat-released/gitlab-mcp-server:latest \
  <<< '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_current_user","arguments":{}}}'
```

If output contains "Successfully authenticated", save token:

```bash
SHELL_PROFILE="${HOME}/.$(basename $SHELL)rc"
echo "export GITLAB_TOKEN=\"$GITLAB_TOKEN\"" >> "$SHELL_PROFILE"
```

### Step 5: Confirm completion

Tell user:
> ✅ Setup complete! Your GitLab token has been saved.
> 
> Restart your Kiro agent to use GitLab MCP features.
