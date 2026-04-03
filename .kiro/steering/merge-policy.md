---
inclusion: manual
---

# Merge Policy

## Merge Prerequisites

Before any AI-generated code may be merged into the target branch, ALL of the following conditions must be satisfied:

1. **All checkpoints passed**: The code review, security scan, and test coverage checkpoints must all have `passed: true` status recorded in the audit log for the current workflow run.
2. **Audit log entry recorded**: A `log_event` entry with `event_type: "pre_merge_audit"` must be written to the audit-logger MCP before the merge is executed. This entry must include the `workflow_id`, `workflow_run_id`, `initiator`, and a summary of all checkpoint results.
3. **No unresolved checkpoint failures**: There must be no `passed: false` checkpoint records for the current workflow run that have not been subsequently resolved and re-passed.

## Merge Execution

When all prerequisites are met:

1. Execute the merge into the target branch.
2. Log a `log_event` entry with `event_type: "merge_completed"` to the audit-logger MCP, including the merge commit hash and branch details.
3. If the merge is part of a CI/CD pipeline, return exit code 0 to indicate success.

## When Merge Is Blocked

If any prerequisite is not met, the merge MUST be blocked:

1. **Do NOT merge**. Reject the merge attempt.
2. Log a `log_event` entry with `event_type: "merge_blocked"` to the audit-logger MCP, including which prerequisite(s) failed.
3. Report to the user which conditions are unmet:
   - If a checkpoint has not been run, indicate which checkpoint is missing.
   - If a checkpoint failed, reference the checkpoint failure details from the audit log.
   - If the pre-merge audit log entry is missing, indicate that the audit entry must be created first.
4. The `preToolUse` checkpoint-guard hook (`checkpoint-guard.json`) enforces this policy automatically by intercepting `git_commit` tool calls and verifying all conditions before allowing the commit.

## Rollback After Merge

If issues are discovered after a successful merge:

1. Use the git-rollback MCP `rollback` tool to revert to the pre-merge restore point.
2. Log the rollback via audit-logger MCP `log_event` with `event_type: "post_merge_rollback"` and the reason.
3. Use git-rollback MCP `verify_consistency` to confirm the repository is in a consistent state after rollback.
