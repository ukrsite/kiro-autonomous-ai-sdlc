#!/usr/bin/env python3
"""Generate a WF1 workflow summary report.

Reads the audit log (audit/audit.ndjson), checkpoint results, delta report,
and finops cost data to produce a structured Markdown summary of everything
that happened during a WF1 run.

Usage:
    python3 scripts/generate_wf1_summary.py \
        --workflow-id wf1-add-user-profiles \
        --audit-log audit/audit.ndjson \
        --output workflow-output/wf1-summary.md

Environment variables (optional overrides):
    JIRA_ISSUE_KEY, SANDBOX_PATH, REPO_PATH
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _load_audit_records(audit_path: str, workflow_id: str) -> list[dict]:
    """Load NDJSON audit records filtered by workflow_id."""
    records = []
    path = Path(audit_path)
    if not path.exists():
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("workflow_id") == workflow_id:
                    records.append(rec)
            except json.JSONDecodeError:
                continue
    return records


def _extract_timestamps(records: list[dict]) -> tuple[str, str, float]:
    """Extract start/end timestamps and compute duration."""
    start_ts = end_ts = None
    for rec in records:
        if rec.get("type") == "event":
            et = rec.get("payload", {}).get("event_type", "")
            if et == "workflow_start":
                start_ts = rec.get("timestamp")
            elif et == "workflow_end":
                end_ts = rec.get("timestamp")
    duration_sec = 0.0
    if start_ts and end_ts:
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        try:
            s = datetime.strptime(start_ts, fmt).replace(tzinfo=timezone.utc)
            e = datetime.strptime(end_ts, fmt).replace(tzinfo=timezone.utc)
            duration_sec = (e - s).total_seconds()
        except ValueError:
            pass
    return start_ts or "N/A", end_ts or "N/A", duration_sec


def _format_duration(seconds: float) -> str:
    """Format seconds as Xm Ys."""
    if seconds <= 0:
        return "N/A"
    m = int(seconds) // 60
    s = int(seconds) % 60
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _extract_checkpoints(records: list[dict]) -> list[dict]:
    """Extract checkpoint records with pass/fail status."""
    checkpoints = []
    for rec in records:
        if rec.get("type") != "checkpoint":
            continue
        payload = rec.get("payload", {})
        checkpoints.append({
            "checkpoint_id": payload.get("checkpoint_id", "unknown"),
            "passed": payload.get("passed", False),
            "details": payload.get("validation_details", ""),
            "metrics": payload.get("metrics", {}),
            "timestamp": rec.get("timestamp", ""),
        })
    return checkpoints


def _extract_interactions(records: list[dict]) -> int:
    """Count interaction records."""
    return sum(1 for r in records if r.get("type") == "interaction")


def _extract_events(records: list[dict]) -> list[dict]:
    """Extract event records with type and details."""
    events = []
    for rec in records:
        if rec.get("type") != "event":
            continue
        payload = rec.get("payload", {})
        events.append({
            "event_type": payload.get("event_type", ""),
            "details": payload.get("details", {}),
            "timestamp": rec.get("timestamp", ""),
        })
    return events


def _extract_files_changed(records: list[dict]) -> list[str]:
    """Extract file paths from delta report or code-generation events."""
    files = set()
    for rec in records:
        if rec.get("type") != "event":
            continue
        payload = rec.get("payload", {})
        details = payload.get("details", {})
        if not isinstance(details, dict):
            continue
        # From delta report events
        for change in details.get("changes", []):
            if isinstance(change, dict) and "file_path" in change:
                files.add(change["file_path"])
        # From code-generation events
        for f in details.get("files_created", []):
            files.add(f)
        for f in details.get("files_modified", []):
            files.add(f)
    return sorted(files)


def _load_delta_report(output_dir: str) -> dict | None:
    """Load delta report from workflow output directory."""
    for name in ("delta-report.json", "delta-report.md"):
        path = Path(output_dir) / name
        if path.exists() and name.endswith(".json"):
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return None


def _load_finops_report(reports_dir: str, workflow_id: str) -> dict | None:
    """Load the finops cost report for this workflow."""
    rdir = Path(reports_dir)
    if not rdir.exists():
        return None
    # Look for {workflow_id}_*.json files
    for p in sorted(rdir.glob(f"{workflow_id}_*.json"), reverse=True):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
    return None


def generate_summary(
    workflow_id: str,
    records: list[dict],
    delta_report: dict | None,
    finops_report: dict | None,
    issue_key: str,
    sandbox_path: str,
) -> str:
    """Generate the full Markdown summary report."""
    start_ts, end_ts, duration_sec = _extract_timestamps(records)
    checkpoints = _extract_checkpoints(records)
    interactions = _extract_interactions(records)
    events = _extract_events(records)
    files_changed = _extract_files_changed(records)

    lines: list[str] = []

    # Header
    lines.append(f"# WF1 Summary Report — {issue_key or workflow_id}")
    lines.append("")
    lines.append(f"**Workflow ID:** `{workflow_id}`")
    lines.append(f"**Issue:** {issue_key or 'N/A'}")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"**Sandbox Path:** `{sandbox_path}`")
    lines.append("")

    # Timeline
    lines.append("## Timeline")
    lines.append("")
    lines.append("| Phase | Timestamp |")
    lines.append("|-------|-----------|")
    lines.append(f"| Workflow Start | {start_ts} |")
    lines.append(f"| Workflow End | {end_ts} |")
    lines.append(f"| Duration | {_format_duration(duration_sec)} |")
    lines.append("")

    # Audit summary
    lines.append("## Audit Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Records | {len(records)} |")
    lines.append(f"| Interactions | {interactions} |")
    lines.append(f"| Checkpoints | {len(checkpoints)} |")
    lines.append(f"| Events | {len(events)} |")
    lines.append("")

    # Checkpoints
    lines.append("## Checkpoint Results")
    lines.append("")
    if checkpoints:
        lines.append("| Checkpoint | Status | Details |")
        lines.append("|------------|--------|---------|")
        for cp in checkpoints:
            status = "✅ PASS" if cp["passed"] else "❌ FAIL"
            details = cp["details"][:80] if cp["details"] else ""
            lines.append(f"| {cp['checkpoint_id']} | {status} | {details} |")
        lines.append("")
        all_passed = all(cp["passed"] for cp in checkpoints)
        lines.append(f"**Overall:** {'✅ All checkpoints passed' if all_passed else '❌ One or more checkpoints failed'}")
    else:
        lines.append("No checkpoint records found in audit log.")
    lines.append("")

    # Test coverage (from checkpoint metrics)
    coverage_data = None
    for cp in checkpoints:
        if cp["checkpoint_id"] in ("test_coverage", "coverage"):
            coverage_data = cp.get("metrics", {})
            break
    if coverage_data:
        lines.append("## Test Coverage")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for k, v in coverage_data.items():
            label = k.replace("_", " ").title()
            if isinstance(v, float):
                lines.append(f"| {label} | {v:.1f}% |")
            else:
                lines.append(f"| {label} | {v} |")
        lines.append("")

    # Files changed
    lines.append("## Files Changed")
    lines.append("")
    if files_changed:
        src_files = [f for f in files_changed if "/test" not in f.lower()]
        test_files = [f for f in files_changed if "/test" in f.lower()]
        doc_files = [f for f in files_changed if "/docs/" in f.lower() or f.endswith(".md")]
        lines.append(f"**Total:** {len(files_changed)} files")
        lines.append(f"  — Source: {len(src_files)}, Tests: {len(test_files)}, Docs: {len(doc_files)}")
        lines.append("")
        for f in files_changed:
            lines.append(f"- `{f}`")
    else:
        lines.append("No file change data available in audit log.")
        lines.append("(File list is populated from delta report or code-generation events.)")
    lines.append("")

    # Delta report metrics
    if delta_report:
        metrics = delta_report.get("metrics", {})
        lines.append("## Delta Report")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Files Modified | {metrics.get('files_modified', 'N/A')} |")
        lines.append(f"| Lines Added | +{metrics.get('lines_added', 'N/A')} |")
        lines.append(f"| Lines Removed | -{metrics.get('lines_removed', 'N/A')} |")
        lines.append(f"| Tests Added | {metrics.get('tests_added', 'N/A')} |")
        lines.append(f"| Tests Passed | {metrics.get('tests_passed', 'N/A')} |")
        lines.append(f"| Tests Failed | {metrics.get('tests_failed', 'N/A')} |")
        cov_before = metrics.get("coverage_before")
        cov_after = metrics.get("coverage_after")
        if cov_before is not None and cov_after is not None:
            lines.append(f"| Coverage Before | {cov_before:.1f}% |")
            lines.append(f"| Coverage After | {cov_after:.1f}% |")
        lines.append("")

    # FinOps cost
    lines.append("## FinOps Cost Summary")
    lines.append("")
    if finops_report:
        actuals = finops_report.get("actuals", finops_report)
        token_method = actuals.get("token_count_method", "unknown")
        lines.append(f"**Token counting:** {token_method}")
        lines.append("")
        dims = actuals.get("dimensions", {})
        label_map = {
            "llm_tokens_input": "LLM Input Tokens",
            "llm_tokens_output": "LLM Output Tokens",
            "compute_time_seconds": "Compute Time",
            "mcp_tool_invocations": "MCP Tool Calls",
            "checkpoint_executions": "Checkpoints",
        }
        lines.append("| Dimension | Quantity | Unit Price | Cost |")
        lines.append("|-----------|----------|------------|------|")
        for dim_key, label in label_map.items():
            d = dims.get(dim_key, {})
            qty = d.get("actual_quantity", 0)
            price = d.get("unit_price_usd", 0)
            cost = d.get("actual_cost_usd", 0)
            # Format quantity
            if "tokens" in dim_key:
                qty_str = f"{int(qty):,} tokens"
                price_str = f"${price:.3f} / 1K tokens"
            elif dim_key == "compute_time_seconds":
                qty_str = _format_duration(qty)
                price_str = f"${price:.5f} / sec"
            elif dim_key == "mcp_tool_invocations":
                qty_str = str(int(qty))
                price_str = f"${price:.4f} / call"
            else:
                qty_str = str(int(qty))
                price_str = f"${price:.3f} / checkpoint"
            cost_str = f"${cost:.6f}"
            lines.append(f"| {label} | {qty_str} | {price_str} | {cost_str} |")
        total = actuals.get("total_actual_cost_usd", 0)
        lines.append(f"| **Total** | | | **${total:.2f}** |")
        lines.append("")
        # Variance if available
        variance = finops_report.get("variance")
        if variance:
            total_var = variance.get("total_variance_usd", 0)
            direction = "over" if total_var > 0 else "under"
            lines.append(f"**Estimate vs Actual:** ${abs(total_var):.4f} {direction} estimate")
            lines.append("")
    else:
        lines.append("No FinOps cost report found.")
        lines.append("Ensure `calculate_workflow_cost` was called after `workflow_end`.")
    lines.append("")

    # MCP server usage
    lines.append("## MCP Server Usage")
    lines.append("")
    mcp_servers = {
        "audit-logger": False,
        "security-scanner": False,
        "git-rollback": False,
        "finops-cost-estimator": False,
    }
    for rec in records:
        if rec.get("type") == "interaction":
            mcp_servers["audit-logger"] = True
        if rec.get("type") == "checkpoint":
            mcp_servers["audit-logger"] = True
            payload = rec.get("payload", {})
            cid = payload.get("checkpoint_id", "")
            if "security" in cid:
                mcp_servers["security-scanner"] = True
        if rec.get("type") == "event":
            et = rec.get("payload", {}).get("event_type", "")
            mcp_servers["audit-logger"] = True
            if "restore_point" in et or "rollback" in et:
                mcp_servers["git-rollback"] = True
            if "cost" in et or "finops" in et:
                mcp_servers["finops-cost-estimator"] = True
            details = rec.get("payload", {}).get("details", {})
            if isinstance(details, dict) and "restore_point" in str(details):
                mcp_servers["git-rollback"] = True
    lines.append("| Server | Status |")
    lines.append("|--------|--------|")
    for server, used in mcp_servers.items():
        status = "✅ Used" if used else "⚠️ Not detected"
        lines.append(f"| {server} | {status} |")
    lines.append("")

    # Event timeline
    lines.append("## Event Timeline")
    lines.append("")
    if events:
        lines.append("| Timestamp | Event |")
        lines.append("|-----------|-------|")
        for ev in events:
            ts = ev["timestamp"] or ""
            lines.append(f"| {ts} | {ev['event_type']} |")
    else:
        lines.append("No events recorded.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate WF1 summary report")
    parser.add_argument("--workflow-id", required=True, help="Workflow ID")
    parser.add_argument("--audit-log", default="audit/audit.ndjson",
                        help="Path to audit NDJSON log")
    parser.add_argument("--output-dir", default="workflow-output",
                        help="Directory containing delta report and other outputs")
    parser.add_argument("--reports-dir", default="reports/finops",
                        help="Directory containing finops reports")
    parser.add_argument("--output", default=None,
                        help="Output file path (stdout if omitted)")
    args = parser.parse_args()

    issue_key = os.environ.get("JIRA_ISSUE_KEY", "")
    sandbox_path = os.environ.get("SANDBOX_PATH", "")

    records = _load_audit_records(args.audit_log, args.workflow_id)
    delta_report = _load_delta_report(args.output_dir)
    finops_report = _load_finops_report(args.reports_dir, args.workflow_id)

    summary = generate_summary(
        workflow_id=args.workflow_id,
        records=records,
        delta_report=delta_report,
        finops_report=finops_report,
        issue_key=issue_key,
        sandbox_path=sandbox_path,
    )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(summary, encoding="utf-8")
        print(f"Summary written to {args.output} ({len(summary)} chars)")
    else:
        print(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
