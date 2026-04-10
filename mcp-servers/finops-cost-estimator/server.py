"""FinOps Workflow Cost Estimation MCP Server.

Provides pre-run cost estimation, post-run actual cost calculation,
variance reporting, and historical baseline management for WF1 and WF2 runs.
"""

import json
import os
import statistics
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from mcp.server.fastmcp import FastMCP

COST_MODEL_PATH = os.environ.get("COST_MODEL_PATH", "config/finops-cost-model.yml")
AUDIT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "audit/audit.ndjson")
REPORTS_DIR = os.environ.get("REPORTS_DIR", "reports/finops")
BASELINES_PATH = os.environ.get("BASELINES_PATH", "reports/finops/baselines.json")
AUDIT_LOGGER_SERVER = os.environ.get(
    "AUDIT_LOGGER_SERVER",
    str(Path(__file__).resolve().parent.parent / "audit-logger" / "server.py"),
)

mcp = FastMCP("finops-cost-estimator")

# Module-level cost model cache — loaded once at startup
_COST_MODEL: Optional[dict] = None


def _log_tool_call(tool_name: str, workflow_id: str = "", details: str = "") -> None:
    """Print a structured log line to stderr for CI visibility."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(
        f"[finops-cost-estimator] {timestamp} tool={tool_name} workflow={workflow_id} {details}",
        file=sys.stderr,
        flush=True,
    )

DIMENSIONS = [
    "llm_tokens_input",
    "llm_tokens_output",
    "compute_time_seconds",
    "mcp_tool_invocations",
    "checkpoint_executions",
]


# ---------------------------------------------------------------------------
# Cost Model Loader
# ---------------------------------------------------------------------------

def _load_cost_model(path: str) -> dict:
    """Read and validate config/finops-cost-model.yml.

    Args:
        path: Path to the YAML cost model file.

    Returns:
        Parsed and validated cost model dict.

    Raises:
        ValueError: If the file is missing, unparseable, or contains invalid values.
    """
    p = Path(path)
    if not p.exists():
        raise ValueError(f"Cost model not found at {path}")
    try:
        with open(p, "r", encoding="utf-8") as f:
            model = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid cost model YAML at {path}: {exc}") from exc

    if not isinstance(model, dict):
        raise ValueError(f"Invalid cost model: expected a mapping at {path}")

    # Validate top-level required fields
    for field in ("version", "unit_prices", "defaults", "scaling"):
        if field not in model:
            raise ValueError(f"Invalid cost model: field '{field}' is missing or negative")

    # Validate unit_prices
    up = model.get("unit_prices", {})
    required_prices = [
        "llm_tokens_input_per_1k_usd",
        "llm_tokens_output_per_1k_usd",
        "compute_time_per_second_usd",
        "mcp_tool_invocation_usd",
        "checkpoint_execution_usd",
    ]
    for key in required_prices:
        if key not in up:
            raise ValueError(f"Invalid cost model: field 'unit_prices.{key}' is missing or negative")
        if not isinstance(up[key], (int, float)) or up[key] < 0:
            raise ValueError(f"Invalid cost model: field 'unit_prices.{key}' is missing or negative")

    # Validate defaults.wf1 and defaults.wf2
    defaults = model.get("defaults", {})
    for wf in ("wf1", "wf2", "wf3", "wf4", "wf5"):
        if wf not in defaults:
            raise ValueError(f"Invalid cost model: field 'defaults.{wf}' is missing or negative")
        wf_defaults = defaults[wf]
        for dim in ("llm_tokens_input", "llm_tokens_output", "compute_time_seconds",
                    "mcp_tool_invocations", "checkpoint_executions"):
            if dim not in wf_defaults:
                raise ValueError(
                    f"Invalid cost model: field 'defaults.{wf}.{dim}' is missing or negative"
                )

    # Validate scaling
    scaling = model.get("scaling", {})
    for wf, key in (("wf1", "wf1_per_file"), ("wf2", "wf2_per_file"), ("wf3", "wf3_per_file"), ("wf4", "wf4_per_file"), ("wf5", "wf5_per_file")):
        if key not in scaling:
            raise ValueError(f"Invalid cost model: field 'scaling.{key}' is missing or negative")
        for dim in ("llm_tokens_input", "llm_tokens_output", "compute_time_seconds"):
            if dim not in scaling[key]:
                raise ValueError(
                    f"Invalid cost model: field 'scaling.{key}.{dim}' is missing or negative"
                )

    return model


# ---------------------------------------------------------------------------
# Baseline Manager
# ---------------------------------------------------------------------------

def _empty_baseline() -> dict:
    """Return an empty baseline structure."""
    return {"wf1": {}, "wf2": {}}


def _load_baseline(path: str) -> dict:
    """Load baselines.json; return empty structure if missing or corrupt.

    Args:
        path: Path to baselines.json.

    Returns:
        Baseline dict with 'wf1' and 'wf2' keys.
    """
    p = Path(path)
    if not p.exists():
        return _empty_baseline()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("baseline root is not a dict")
        return data
    except (json.JSONDecodeError, ValueError) as exc:
        print(
            f"WARNING: baselines.json corrupt or unparseable at {path}: {exc}",
            file=sys.stderr,
        )
        return _empty_baseline()


def _save_baseline(baseline: dict, path: str) -> None:
    """Atomically write baseline dict to path.

    Args:
        baseline: The baseline dict to persist.
        path: Destination file path.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(baseline, f)
        os.replace(tmp_path, str(p))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _update_baseline(baseline: dict, workflow_type: str, actuals: dict) -> dict:
    """Append actuals to baseline and recompute statistics.

    Args:
        baseline: Current baseline dict (mutated in place and returned).
        workflow_type: 'wf1' or 'wf2'.
        actuals: PostRunActuals dict containing 'dimensions'.

    Returns:
        Updated baseline dict.
    """
    wf_data = baseline.setdefault(workflow_type, {})
    dimensions = actuals.get("dimensions", {})

    for dim_name, dim_data in dimensions.items():
        actual_qty = dim_data.get("actual_quantity", 0.0)
        dim_entry = wf_data.setdefault(dim_name, {"count": 0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "_values": []})
        dim_entry.setdefault("_values", [])
        dim_entry["_values"].append(actual_qty)
        values = dim_entry["_values"]
        count = len(values)
        dim_entry["count"] = count
        dim_entry["mean"] = sum(values) / count
        dim_entry["p50"] = statistics.median(values)
        sorted_vals = sorted(values)
        # p95: linear interpolation at 95th percentile position
        pos = 0.95 * (count - 1)
        lo = int(pos)
        hi = min(lo + 1, count - 1)
        frac = pos - lo
        dim_entry["p95"] = sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])

    return baseline


# ---------------------------------------------------------------------------
# Cost Estimator
# ---------------------------------------------------------------------------

def _get_unit_price(cost_model: dict, dimension: str) -> float:
    """Return the unit price for a given dimension."""
    up = cost_model["unit_prices"]
    mapping = {
        "llm_tokens_input": up["llm_tokens_input_per_1k_usd"] / 1000.0,
        "llm_tokens_output": up["llm_tokens_output_per_1k_usd"] / 1000.0,
        "compute_time_seconds": up["compute_time_per_second_usd"],
        "mcp_tool_invocations": up["mcp_tool_invocation_usd"],
        "checkpoint_executions": up["checkpoint_execution_usd"],
    }
    return mapping[dimension]


def _estimate_cost(
    workflow_type: str,
    scope_input: dict,
    cost_model: dict,
    baseline: dict,
) -> dict:
    """Compute a pre-run cost estimate.

    Args:
        workflow_type: 'wf1' or 'wf2'.
        scope_input: Dict with optional keys files_to_modify, files_to_refactor,
                     estimated_checkpoints, estimated_interactions.
        cost_model: Loaded cost model dict.
        baseline: Loaded baseline dict.

    Returns:
        PreRunEstimate dict.

    Raises:
        ValueError: For unknown workflow_type.
    """
    if workflow_type not in ("wf1", "wf2", "wf3", "wf4", "wf5"):
        raise ValueError(f"Unknown workflow_type '{workflow_type}'. Expected 'wf1', 'wf2', 'wf3', 'wf4', or 'wf5'")

    wf_baseline = baseline.get(workflow_type, {})
    run_count = 0
    if wf_baseline:
        # Use the count from the first dimension that has data
        for dim in DIMENSIONS:
            if dim in wf_baseline and wf_baseline[dim].get("count", 0) > 0:
                run_count = wf_baseline[dim]["count"]
                break

    if run_count == 0:
        baseline_source = "default"
        base_quantities = {dim: cost_model["defaults"][workflow_type].get(dim, 0) for dim in DIMENSIONS}
    else:
        baseline_source = "historical"
        base_quantities = {
            dim: wf_baseline[dim]["p50"] if dim in wf_baseline else cost_model["defaults"][workflow_type].get(dim, 0)
            for dim in DIMENSIONS
        }

    # Apply per-file scaling
    scaling = cost_model["scaling"]
    if workflow_type == "wf1":
        files = scope_input.get("files_to_modify", 0) or 0
        per_file = scaling.get("wf1_per_file", {})
    elif workflow_type == "wf2":
        files = scope_input.get("files_to_refactor", 0) or 0
        per_file = scaling.get("wf2_per_file", {})
    else:
        files = scope_input.get("files_to_modify", 0) or scope_input.get("files_to_refactor", 0) or 0
        per_file = scaling.get(f"{workflow_type}_per_file", {})

    scaled_quantities = {}
    for dim in DIMENSIONS:
        base = base_quantities[dim]
        factor = per_file.get(dim, 0)
        scaled_quantities[dim] = base + files * factor

    # Override with explicit scope inputs if provided
    if scope_input.get("estimated_checkpoints") is not None:
        scaled_quantities["checkpoint_executions"] = scope_input["estimated_checkpoints"]

    # Build dimensions output
    dimensions = {}
    total_cost = 0.0
    for dim in DIMENSIONS:
        qty = scaled_quantities[dim]
        price = _get_unit_price(cost_model, dim)
        cost = qty * price
        total_cost += cost
        dimensions[dim] = {
            "estimated_quantity": qty,
            "unit_price_usd": price,
            "estimated_cost_usd": cost,
        }

    # Confidence level
    if run_count < 3:
        confidence_level = "low"
    elif run_count < 10:
        confidence_level = "medium"
    else:
        confidence_level = "high"

    result: dict = {
        "workflow_type": workflow_type,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline_source": baseline_source,
        "baseline_run_count": run_count,
        "confidence_level": confidence_level,
        "dimensions": dimensions,
        "total_estimated_cost_usd": total_cost,
        "cost_model_version": cost_model.get("version", "unknown"),
    }

    # WF2-specific overhead
    if workflow_type == "wf2":
        overhead = cost_model["defaults"]["wf2"].get("behavior_equivalence_overhead_usd", 0.0)
        result["behavior_equivalence_overhead_usd"] = overhead
        result["total_estimated_cost_usd"] += overhead

    return result


# ---------------------------------------------------------------------------
# Cost Calculator
# ---------------------------------------------------------------------------

def _read_audit_records(workflow_id: str, audit_path: str) -> list:
    """Read all audit records for a given workflow_id from the NDJSON log.

    Args:
        workflow_id: The workflow identifier to filter by.
        audit_path: Path to the audit NDJSON file.

    Returns:
        List of matching audit record dicts. Empty list if file missing.
    """
    p = Path(audit_path)
    if not p.exists():
        return []
    records = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if record.get("workflow_id") == workflow_id:
                records.append(record)
    return records


def _calculate_actuals(workflow_id: str, audit_records: list, cost_model: dict) -> dict:
    """Compute post-run actuals from audit records.

    Args:
        workflow_id: The workflow identifier.
        audit_records: List of audit records for this workflow.
        cost_model: Loaded cost model dict.

    Returns:
        PostRunActuals dict, or {"error": "..."} on failure.
    """
    if not audit_records:
        return {"error": f"No audit records found for workflow_id '{workflow_id}'"}

    # Find workflow_start and workflow_end timestamps
    start_ts = None
    end_ts = None
    for rec in audit_records:
        if rec.get("type") == "event":
            event_type = rec.get("payload", {}).get("event_type", "")
            if event_type == "workflow_start":
                start_ts = rec.get("timestamp")
            elif event_type == "workflow_end":
                end_ts = rec.get("timestamp")

    if start_ts is None:
        return {"error": f"Workflow '{workflow_id}' has no workflow_start event — run may be incomplete"}
    if end_ts is None:
        return {"error": f"Workflow '{workflow_id}' has no workflow_end event — run may still be in progress"}

    # Compute elapsed seconds
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    start_dt = datetime.strptime(start_ts, fmt).replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end_ts, fmt).replace(tzinfo=timezone.utc)
    compute_time_seconds = (end_dt - start_dt).total_seconds()

    # Count tool invocations
    mcp_tool_invocations = sum(
        1 for rec in audit_records
        if rec.get("type") == "event"
        and rec.get("payload", {}).get("event_type") == "tool_invocation"
    )

    # Count checkpoints
    checkpoint_executions = sum(
        1 for rec in audit_records if rec.get("type") == "checkpoint"
    )

    # Sum tokens from interaction records
    llm_tokens_input = 0.0
    llm_tokens_output = 0.0
    token_count_method = "recorded"
    has_explicit_tokens = False
    for rec in audit_records:
        if rec.get("type") != "interaction":
            continue
        payload = rec.get("payload", {})
        if "input_tokens" in payload and "output_tokens" in payload:
            llm_tokens_input += payload["input_tokens"]
            llm_tokens_output += payload["output_tokens"]
            has_explicit_tokens = True
        else:
            token_count_method = "estimated"
            llm_tokens_input += len(payload.get("input_prompt", "")) / 4.0
            llm_tokens_output += len(payload.get("ai_output", "")) / 4.0

    # Fallback: if no explicit token counts were injected (e.g. from kiro-cli
    # log parsing), always use compute-time-based estimation. Text-based
    # estimation from log_interaction summaries is unreliable — the records
    # contain short descriptions, not the full LLM conversation text.
    # LLM throughput rates are configured in finops-cost-model.yml under
    # scaling.token_estimation.
    token_est = cost_model.get("scaling", {}).get("token_estimation", {})
    output_tps = float(token_est.get("output_tokens_per_second", 40.0))
    io_ratio = float(token_est.get("input_output_ratio", 2.5))

    if not has_explicit_tokens and compute_time_seconds > 0:
        llm_tokens_output = compute_time_seconds * output_tps
        llm_tokens_input = llm_tokens_output * io_ratio
        token_count_method = "estimated-from-compute-time"

    # Build dimensions
    dim_quantities = {
        "llm_tokens_input": llm_tokens_input,
        "llm_tokens_output": llm_tokens_output,
        "compute_time_seconds": compute_time_seconds,
        "mcp_tool_invocations": float(mcp_tool_invocations),
        "checkpoint_executions": float(checkpoint_executions),
    }

    dimensions = {}
    total_cost = 0.0
    for dim in DIMENSIONS:
        qty = dim_quantities[dim]
        price = _get_unit_price(cost_model, dim)
        cost = qty * price
        total_cost += cost
        dimensions[dim] = {
            "actual_quantity": qty,
            "unit_price_usd": price,
            "actual_cost_usd": cost,
        }

    return {
        "workflow_id": workflow_id,
        "workflow_type": None,  # caller fills this in
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token_count_method": token_count_method,
        "dimensions": dimensions,
        "total_actual_cost_usd": total_cost,
        "cost_model_version": cost_model.get("version", "unknown"),
    }


# ---------------------------------------------------------------------------
# Variance Calculator
# ---------------------------------------------------------------------------

def _calculate_variance(estimate: dict, actuals: dict) -> dict:
    """Compute variance between pre-run estimate and post-run actuals.

    Args:
        estimate: PreRunEstimate dict.
        actuals: PostRunActuals dict.

    Returns:
        VarianceReport dict.
    """
    workflow_id = actuals.get("workflow_id", estimate.get("workflow_id", ""))
    est_dims = estimate.get("dimensions", {})
    act_dims = actuals.get("dimensions", {})

    dimensions = {}
    total_variance = 0.0

    for dim in DIMENSIONS:
        est_dim = est_dims.get(dim, {})
        act_dim = act_dims.get(dim, {})
        est_qty = est_dim.get("estimated_quantity", 0.0)
        act_qty = act_dim.get("actual_quantity", 0.0)
        est_cost = est_dim.get("estimated_cost_usd", 0.0)
        act_cost = act_dim.get("actual_cost_usd", 0.0)
        variance_usd = act_cost - est_cost
        variance_pct = (variance_usd / est_cost * 100.0) if est_cost != 0.0 else 0.0
        overrun = act_cost > est_cost * 1.2
        total_variance += variance_usd
        dimensions[dim] = {
            "estimated_quantity": est_qty,
            "actual_quantity": act_qty,
            "estimated_cost_usd": est_cost,
            "actual_cost_usd": act_cost,
            "variance_usd": variance_usd,
            "variance_pct": variance_pct,
            "overrun": overrun,
        }

    return {
        "workflow_id": workflow_id,
        "dimensions": dimensions,
        "total_variance_usd": total_variance,
    }


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------

def _pretty_print_report(cost_report: dict) -> str:
    """Render a CostReport dict as a Markdown string.

    Args:
        cost_report: CostReport dict.

    Returns:
        Markdown-formatted string.
    """
    workflow_id = cost_report.get("workflow_id", "unknown")
    workflow_type = cost_report.get("workflow_type", "unknown")
    generated_at = cost_report.get("generated_at", "")
    estimate = cost_report.get("estimate")
    actuals = cost_report.get("actuals")
    variance = cost_report.get("variance")
    variance_available = cost_report.get("variance_available", False)
    cost_model_version = cost_report.get("cost_model_version", "unknown")

    has_actuals = actuals is not None and variance_available

    if has_actuals:
        title = "Post-Run Cost Report"
    else:
        title = "Pre-Run Estimate"

    lines = [
        f"# {title}",
        "",
        f"**Workflow ID**: {workflow_id}  ",
        f"**Workflow Type**: {workflow_type}  ",
        f"**Generated At**: {generated_at}  ",
        f"**Cost Model Version**: {cost_model_version}  ",
        "",
    ]

    if has_actuals:
        lines.append("| Dimension | Estimated Quantity | Actual Quantity | Estimated Cost (USD) | Actual Cost (USD) | Variance (USD) | Variance (%) |")
        lines.append("|---|---|---|---|---|---|---|")
        for dim in DIMENSIONS:
            v = variance["dimensions"].get(dim, {}) if variance else {}
            e = estimate["dimensions"].get(dim, {}) if estimate else {}
            a = actuals["dimensions"].get(dim, {}) if actuals else {}
            lines.append(
                f"| {dim} "
                f"| {e.get('estimated_quantity', 'N/A'):.2f} "
                f"| {a.get('actual_quantity', 0.0):.2f} "
                f"| {e.get('estimated_cost_usd', 0.0):.6f} "
                f"| {a.get('actual_cost_usd', 0.0):.6f} "
                f"| {v.get('variance_usd', 0.0):.6f} "
                f"| {v.get('variance_pct', 0.0):.2f}% |"
            )
        if variance:
            lines.append("")
            lines.append(f"**Total Variance (USD)**: {variance.get('total_variance_usd', 0.0):.6f}")
    else:
        lines.append("| Dimension | Estimated Quantity | Estimated Cost (USD) |")
        lines.append("|---|---|---|")
        src = estimate or {}
        for dim in DIMENSIONS:
            d = src.get("dimensions", {}).get(dim, {})
            lines.append(
                f"| {dim} "
                f"| {d.get('estimated_quantity', 0.0):.2f} "
                f"| {d.get('estimated_cost_usd', 0.0):.6f} |"
            )
        if estimate:
            lines.append("")
            lines.append(f"**Total Estimated Cost (USD)**: {estimate.get('total_estimated_cost_usd', 0.0):.6f}")
            lines.append(f"**Confidence Level**: {estimate.get('confidence_level', 'unknown')}")

    return "\n".join(lines) + "\n"


def _generate_report(cost_report: dict, output_dir: str) -> dict:
    """Write JSON and Markdown report files to output_dir.

    Args:
        cost_report: CostReport dict.
        output_dir: Directory to write reports into.

    Returns:
        Dict with 'json_path' and 'md_path', or {"error": "..."} on failure.
    """
    out = Path(output_dir)
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"error": f"reports/finops/ not writable: {exc}"}

    workflow_id = cost_report.get("workflow_id", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"{workflow_id}_{timestamp}"
    json_path = out / f"{base}.json"
    md_path = out / f"{base}.md"

    try:
        json_path.write_text(json.dumps(cost_report, indent=2), encoding="utf-8")
        md_path.write_text(_pretty_print_report(cost_report), encoding="utf-8")
    except OSError as exc:
        return {"error": f"Failed to write report: {exc}"}

    return {"json_path": str(json_path), "md_path": str(md_path)}


# ---------------------------------------------------------------------------
# Audit Logger Client
# ---------------------------------------------------------------------------

def _log_finops_event(event_type: str, payload: dict) -> None:
    """Log a FinOps event via the audit-logger MCP server (best-effort).

    Calls the audit-logger server as a subprocess. On any failure, logs a
    warning to stderr and continues — audit logging is non-blocking.

    Args:
        event_type: The event type string (e.g. 'cost_estimate_produced').
        payload: Dict of event details to include.
    """
    workflow_id = payload.get("workflow_id", "finops-cost-estimator")
    try:
        cmd = [
            sys.executable,
            AUDIT_LOGGER_SERVER,
        ]
        input_data = json.dumps({
            "method": "log_event",
            "params": {
                "workflow_id": workflow_id,
                "event_type": event_type,
                "initiator": "finops-cost-estimator",
                "details": payload,
            },
        })
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            print(
                f"WARNING: audit-logger returned non-zero exit code for event '{event_type}': {result.stderr}",
                file=sys.stderr,
            )
    except Exception as exc:
        print(
            f"WARNING: Failed to log FinOps event '{event_type}' via audit-logger: {exc}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def estimate_workflow_cost(
    workflow_type: str,
    scope_input: dict,
    workflow_id: Optional[str] = None,
) -> dict:
    """Produce a pre-run cost estimate for a WF1 or WF2 workflow run.

    Args:
        workflow_type: 'wf1' or 'wf2'.
        scope_input: Dict with optional keys: files_to_modify, files_to_refactor,
                     estimated_checkpoints, estimated_interactions.
        workflow_id: Optional identifier; if provided, estimate is persisted for
                     later variance comparison.

    Returns:
        PreRunEstimate dict, or {"error": "..."} on failure.
    """
    global _COST_MODEL
    try:
        if _COST_MODEL is None:
            _COST_MODEL = _load_cost_model(COST_MODEL_PATH)
    except ValueError as exc:
        return {"error": str(exc)}

    try:
        baseline = _load_baseline(BASELINES_PATH)
        estimate = _estimate_cost(workflow_type, scope_input, _COST_MODEL, baseline)
    except ValueError as exc:
        return {"error": str(exc)}

    if workflow_id:
        estimate["workflow_id"] = workflow_id
        out = Path(REPORTS_DIR)
        out.mkdir(parents=True, exist_ok=True)
        est_path = out / f"{workflow_id}_estimate.json"
        est_path.write_text(json.dumps(estimate), encoding="utf-8")

    _log_finops_event("cost_estimate_produced", {
        "workflow_id": workflow_id or "",
        "workflow_type": workflow_type,
        "total_estimated_cost_usd": estimate.get("total_estimated_cost_usd"),
        "confidence_level": estimate.get("confidence_level"),
        "cost_model_version": estimate.get("cost_model_version"),
    })

    _log_tool_call("estimate_workflow_cost", workflow_id or "", f"type={workflow_type} total=${estimate.get('total_estimated_cost_usd', 0):.6f} confidence={estimate.get('confidence_level')}")
    return estimate


@mcp.tool()
def calculate_workflow_cost(workflow_id: str) -> dict:
    """Compute post-run actuals for a completed workflow run.

    Args:
        workflow_id: The workflow identifier to look up in the audit log.

    Returns:
        Dict with 'actuals' and optionally 'variance', or {"error": "..."}.
    """
    global _COST_MODEL
    try:
        if _COST_MODEL is None:
            _COST_MODEL = _load_cost_model(COST_MODEL_PATH)
    except ValueError as exc:
        return {"error": str(exc)}

    records = _read_audit_records(workflow_id, AUDIT_LOG_PATH)
    actuals = _calculate_actuals(workflow_id, records, _COST_MODEL)
    if "error" in actuals:
        return actuals

    # Determine workflow_type from audit records
    workflow_type = None
    for rec in records:
        if rec.get("type") == "event":
            details = rec.get("payload", {}).get("details", {})
            if isinstance(details, dict) and "workflow_type" in details:
                workflow_type = details["workflow_type"]
                break
    actuals["workflow_type"] = workflow_type

    # Update baseline
    if workflow_type:
        baseline = _load_baseline(BASELINES_PATH)
        _update_baseline(baseline, workflow_type, actuals)
        _save_baseline(baseline, BASELINES_PATH)

    # Load stored estimate for variance
    est_path = Path(REPORTS_DIR) / f"{workflow_id}_estimate.json"
    result: dict = {"actuals": actuals}
    if est_path.exists():
        try:
            estimate = json.loads(est_path.read_text(encoding="utf-8"))
            variance = _calculate_variance(estimate, actuals)
            result["variance"] = variance
            _log_finops_event("cost_variance_reported", {
                "workflow_id": workflow_id,
                "total_variance_usd": variance.get("total_variance_usd"),
                "overrun_dimensions": [
                    d for d, v in variance.get("dimensions", {}).items() if v.get("overrun")
                ],
            })
        except (json.JSONDecodeError, KeyError):
            pass

    _log_finops_event("cost_actuals_computed", {
        "workflow_id": workflow_id,
        "workflow_type": workflow_type or "",
        "total_actual_cost_usd": actuals.get("total_actual_cost_usd"),
        "cost_model_version": actuals.get("cost_model_version"),
    })

    _log_tool_call("calculate_workflow_cost", workflow_id, f"total=${actuals.get('total_actual_cost_usd', 0):.6f} records={len(records)}")
    return result


@mcp.tool()
def get_cost_report(workflow_id: str, format: str = "json") -> dict:
    """Retrieve a stored cost report for a workflow run.

    Args:
        workflow_id: The workflow identifier.
        format: 'json' or 'markdown'.

    Returns:
        Dict with 'content' key, or {"error": "..."} if not found.
    """
    out = Path(REPORTS_DIR)
    # Find the most recent report file for this workflow_id
    matches = sorted(out.glob(f"{workflow_id}_*.json")) if out.exists() else []
    # Exclude the estimate file
    report_files = [f for f in matches if not f.name.endswith("_estimate.json")]

    if not report_files:
        return {"error": f"No report found for workflow_id '{workflow_id}'"}

    latest = report_files[-1]
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"error": f"Failed to read report: {exc}"}

    if format == "markdown":
        md_path = latest.with_suffix(".md")
        if md_path.exists():
            _log_tool_call("get_cost_report", workflow_id, "format=markdown")
            return {"content": md_path.read_text(encoding="utf-8")}
        _log_tool_call("get_cost_report", workflow_id, "format=markdown(generated)")
        return {"content": _pretty_print_report(data)}

    _log_tool_call("get_cost_report", workflow_id, "format=json")
    return {"content": json.dumps(data, indent=2)}


@mcp.tool()
def get_historical_baseline(workflow_type: str) -> dict:
    """Return historical baseline statistics for a workflow type.

    Args:
        workflow_type: 'wf1' or 'wf2'.

    Returns:
        HistoricalBaseline dict for the given type, or {"error": "..."}.
    """
    if workflow_type not in ("wf1", "wf2", "wf3", "wf4", "wf5"):
        return {"error": f"Unknown workflow_type '{workflow_type}'. Expected 'wf1', 'wf2', 'wf3', 'wf4', or 'wf5'"}

    baseline = _load_baseline(BASELINES_PATH)
    _log_tool_call("get_historical_baseline", "", f"type={workflow_type}")
    return baseline.get(workflow_type, {})


if __name__ == "__main__":
    # Load cost model at startup; fail fast if config is invalid
    try:
        _COST_MODEL = _load_cost_model(COST_MODEL_PATH)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    mcp.run()
