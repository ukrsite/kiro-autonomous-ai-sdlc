#!/usr/bin/env python3
"""Build the kiro-cli prompt for the execute-workflow CI stage.

Reads config from environment variables and writes the prompt to
/tmp/kiro-prompt.txt. This avoids shell metacharacter issues from
Jira descriptions and keeps the YAML clean.
"""
import os
import sys


def main() -> int:
    issue_key = os.environ.get("JIRA_ISSUE_KEY", "UNKNOWN")
    workflow = os.environ.get("WORKFLOW", "auto")
    summary = os.environ.get("ISSUE_SUMMARY", "Unknown")
    pipeline_id = os.environ.get("CI_PIPELINE_ID", "")
    repo_path = os.environ.get("REPO_PATH", "")

    lines = [
        "You are the developer agent. Execute AI-DLC INCEPTION for "
        f"Jira issue {issue_key}, then delegate CONSTRUCTION to the "
        f"selected WF (default: {workflow}).",
        f"Issue summary: {summary}",
        "Issue description: See workflow-output/jira-issue.json.",
        "IMPORTANT: Working directory is the sandbox repo root.",
        "",
        f"1. Log workflow start via audit-logger MCP "
        f"(issue: {issue_key}, workflow: {workflow}, "
        f"pipeline: {pipeline_id}).",
        "2. Create restore point via git-rollback MCP before changes.",
        f"3. Run AI-DLC INCEPTION against {repo_path}:",
        "   a. Workspace Detection.",
        "   b. Reverse Engineering (if brownfield).",
        "   c. Requirements Analysis (adaptive depth).",
        f"   d. Workflow Planning: classify issue, select WF. "
        f"IMPORTANT: default hint is {workflow} but MUST override if "
        "issue signals: refactor/refactoring -> WF2, "
        "upgrade/dependency -> WF3, bug/fix/crash -> WF4, "
        "document/docs -> WF5. Only use WF1 for new features.",
        "   e. Generate Handoff Artifact at "
        "aidlc-docs/inception/plans/workflow-handoff.md.",
        "   f. Auto-approve INCEPTION gates (CI mode). "
        "Halt if security/compliance violations.",
        "4. Delegate CONSTRUCTION to selected WF:",
        "   a. Apply delegation markers in aidlc-state.md.",
        f"   b. Execute WF against {repo_path} with Handoff Artifact.",
        "   c. WF1: skip req gathering, use INCEPTION artifacts. "
        "WF2-WF5: use Handoff as additional context.",
        f"5. MANDATORY: Generate unit tests for every new/modified "
        f"source file in tests/ under {repo_path}. "
        "Min 80% line coverage. Run tests, verify they pass. "
        "If tests use async/await, add pytest-asyncio to the service requirements.txt.",
        "6. WF-specific steps:",
        "   - WF2: behavior equivalence + performance benchmark "
        "(max 10% degradation).",
        "   - WF4: side-effect analysis on callers of modified code.",
        "   - WF5: onboarding guides + accuracy/completeness review.",
        "7. Add docstrings to new/modified REST endpoints.",
        "8. Generate docs: "
        f"docs/release-notes-{issue_key}.md, docs/CHANGELOG.md, "
        f"docs/openapi.yaml (if REST), docs/architecture.md. "
        f"Place in docs/ under {repo_path}.",
        "9. Generate delta report. Save as "
        "../workflow-output/delta-report.md.",
        "10. Log all events to aidlc-docs/audit.md and "
        "audit-logger MCP (include phase: INCEPTION or CONSTRUCTION).",
        "11. Log workflow_end to audit-logger MCP. "
        "Save all artifacts to workflow-output/.",
    ]

    prompt = "\n".join(lines)

    with open("/tmp/kiro-prompt.txt", "w") as f:
        f.write(prompt)

    print(f"Prompt written ({len(prompt)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
