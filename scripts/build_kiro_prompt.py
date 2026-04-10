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
    multi_service = os.environ.get("MULTI_SERVICE", "")
    service_paths = os.environ.get("SERVICE_PATHS", "")

    # Multi-service mode: inspect all services under the repo_path
    if multi_service == "true" and service_paths:
        svc_list = service_paths.split(",")
        scope_line = (
            "IMPORTANT: This is a MULTI-SERVICE run. "
            "The sandbox repository is cloned at sandbox/. "
            "You MUST inspect and apply changes to ALL of these services: "
            + ", ".join(f"sandbox/{s}" for s in svc_list)
            + ". Analyze the requirement against each service and update "
            "whichever ones need changes. Generate tests and docs for each."
        )
    else:
        scope_line = (
            f"IMPORTANT: The sandbox repository is cloned at sandbox/. "
            f"All code changes MUST target sandbox/{repo_path}. "
            "Working directory is the project root (NOT sandbox/)."
        )

    lines = [
        "You are the developer agent. Execute AI-DLC INCEPTION for "
        f"Jira issue {issue_key}, then delegate CONSTRUCTION to the "
        f"selected WF (default: {workflow}).",
        f"Issue summary: {summary}",
        "Issue description: See workflow-output/jira-issue.json.",
        scope_line,
        "",
        f"1. Log workflow start via audit-logger MCP "
        f"(issue: {issue_key}, workflow: {workflow}, "
        f"pipeline: {pipeline_id}).",
        "2. Create restore point via git-rollback MCP before changes.",
        f"3. Run AI-DLC INCEPTION against sandbox/{repo_path}:",
        "   a. Workspace Detection.",
        "   b. Reverse Engineering (if brownfield).",
        "   c. Requirements Analysis (adaptive depth).",
        f"   d. Workflow Planning: classify issue, select WF. "
        f"IMPORTANT: default hint is {workflow} but MUST override if "
        "issue signals: refactor/refactoring -> WF2, "
        "upgrade/dependency -> WF3, bug/fix/crash -> WF4, "
        "document/docs -> WF5. Only use WF1 for new features.",
        "   e. Generate Handoff Artifact at "
        "sandbox/aidlc-docs/inception/plans/workflow-handoff.md.",
        "   f. Auto-approve INCEPTION gates (CI mode). "
        "Halt if security/compliance violations.",
        "4. Delegate CONSTRUCTION to selected WF:",
        "   a. Apply delegation markers in aidlc-state.md.",
        f"   b. Execute WF against sandbox/{repo_path} with Handoff Artifact.",
        "   c. WF1: skip req gathering, use INCEPTION artifacts. "
        "WF2-WF5: use Handoff as additional context.",
        f"5. MANDATORY: Generate unit tests for every new/modified "
        f"source file in tests/ under sandbox/{repo_path}. "
        "Min 80% line coverage. Run tests, verify they pass. "
        "If tests use async/await, add pytest-asyncio to the service requirements.txt.",
        "6. WF-specific steps:",
        "   - WF2: behavior equivalence + performance benchmark "
        "(max 10% degradation).",
        "   - WF4: side-effect analysis on callers of modified code.",
        "   - WF5: onboarding guides + accuracy/completeness review.",
        "7. Add docstrings to new/modified REST endpoints.",
        "9. MANDATORY: Generate ALL of these docs in docs/ under "
        f"sandbox/{repo_path}: "
        f"(a) docs/release-notes-{issue_key}.md, "
        "(b) docs/CHANGELOG.md (append), "
        "(c) docs/openapi.yaml (if REST endpoints), "
        "(d) docs/architecture.md (Mermaid diagram), "
        f"(e) docs/wf1-summary-{issue_key}.md (WF1 summary report "
        "using template from references/output-templates.md). "
        "Do NOT skip any artifact.",
        "10. Generate delta report. Save as "
        "workflow-output/delta-report.md.",
        "11. Log all events to sandbox/aidlc-docs/audit.md and "
        "audit-logger MCP (include phase: INCEPTION or CONSTRUCTION).",
        "12. Log workflow_end to audit-logger MCP. "
        "Save all artifacts to workflow-output/.",
    ]

    prompt = "\n".join(lines)

    with open("/tmp/kiro-prompt.txt", "w") as f:
        f.write(prompt)

    print(f"Prompt written ({len(prompt)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
