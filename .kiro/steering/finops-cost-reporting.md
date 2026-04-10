# FinOps Cost Reporting

## Mandatory: Report Actual Cost After Every Workflow Run

At the end of EVERY workflow execution (WF1, WF2, WF3, WF4, or WF5), you MUST call the `calculate_workflow_cost` tool from the `finops-cost-estimator` MCP server and include the cost summary in your final response to the user.

### When to trigger

After logging the `workflow_end` event to the audit-logger MCP — that is the signal that the workflow is complete.

### How to call it

Use the same `workflow_id` that was used throughout the workflow run:

```
calculate_workflow_cost(workflow_id="<the active workflow_id>")
```

### How to present the result

Include a full per-dimension cost breakdown at the end of your final response. Use these rules for formatting:

- Use friendly labels instead of raw field names (see mapping below)
- Format quantities with thousands separators and appropriate units
- Format per-dimension costs with full precision (do NOT round) — use as many decimal places as needed to show a non-zero value, e.g. `$0.000240`
- Format the total cost rounded to 2 decimal places, e.g. `$0.03`
- Include workflow_id and token count method as metadata above the table

**Dimension label mapping:**
- `llm_tokens_input` → `LLM Input Tokens`
- `llm_tokens_output` → `LLM Output Tokens`
- `compute_time_seconds` → `Compute Time`
- `mcp_tool_invocations` → `MCP Tool Calls`
- `checkpoint_executions` → `Checkpoints`

**Quantity formatting:**
- tokens → `65,432 tokens`
- compute time → convert seconds to `Xm Ys` (e.g. `5m 29s`)
- tool calls and checkpoints → plain integer

**Example output:**

```
## 💰 Workflow Cost Summary

**Workflow:** wf1-requirement-to-software
**Token counting:** recorded

| Dimension          | Quantity       | Unit Price           | Cost         |
|--------------------|----------------|----------------------|--------------|
| LLM Input Tokens   | 65,432 tokens  | $0.003 / 1K tokens   | $0.196296    |
| LLM Output Tokens  | 28,100 tokens  | $0.015 / 1K tokens   | $0.421500    |
| Compute Time       | 5m 29s         | $0.00005 / sec       | $0.016450    |
| MCP Tool Calls     | 47             | $0.0001 / call       | $0.004700    |
| Checkpoints        | 9              | $0.001 / checkpoint  | $0.009000    |
| **Total**          |                |                      | **$0.65**    |
```

If `calculate_workflow_cost` returns an error, include the error in your response with this format:

```
## 💰 Workflow Cost Summary

**Status:** Cost calculation failed — {error reason}
**Likely cause:** audit-logger MCP `log_event` with `event_type: "workflow_start"` was not called at the beginning of this workflow, so no records exist to calculate from.
**Action required:** Ensure Step 1 (Start Workflow) calls audit-logger MCP before any other work.
```

Do NOT skip silently. The error must be visible so it can be diagnosed and fixed.

### Important

- Do NOT call `estimate_workflow_cost` — only `calculate_workflow_cost` is needed here
- The full report is also written to `reports/finops/` automatically
- `aidlc-docs/audit.md` is a human-readable log only — it is NOT read by `calculate_workflow_cost`
- Cost calculation requires `audit/audit.ndjson` to contain both `workflow_start` and `workflow_end` events with the matching `workflow_id`
