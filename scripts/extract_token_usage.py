#!/usr/bin/env python3
"""Extract LLM token usage from kiro-cli logs and inject into audit NDJSON.

Parses kiro-cli log files for token count data and appends a token_usage
event to the audit log so that finops-cost-estimator can include LLM costs
in the workflow cost report.

Priority chain (first match wins):
  1. kiro-cli trace log  — actual LLM API token counts (most accurate)
  2. Manual injection    — --input-tokens N --output-tokens N
  3. Compute time        — workflow duration × throughput rate (~40 tok/s)
  4. Audit text          — len(interaction text) / 4 (least accurate)

Usage:
    # Automatic (tries kiro log first, falls back to compute-time estimation):
    python3 scripts/extract_token_usage.py \
        --workflow-id wf1-qwe-12 \
        --audit-log audit/audit.ndjson

    # Explicit kiro log path:
    python3 scripts/extract_token_usage.py \
        --workflow-id wf1-qwe-12 \
        --audit-log audit/audit.ndjson \
        --kiro-log /tmp/kiro-log/kiro-chat.log

    # Manual injection (known values):
    python3 scripts/extract_token_usage.py \
        --workflow-id wf1-qwe-12 \
        --audit-log audit/audit.ndjson \
        --input-tokens 65000 \
        --output-tokens 28000

Environment:
    KIRO_LOG_PATH  — override kiro-cli log path (default: $TMPDIR/kiro-log/kiro-chat.log)

Requires KIRO_LOG_LEVEL=trace during the kiro-cli run for priority 1 to work.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Average chars per token (GPT/Claude family)
CHARS_PER_TOKEN = 4.0


def _parse_kiro_log(log_path: str) -> tuple[int, int]:
    """Parse kiro-cli log for token usage data.

    Looks for JSON-structured log lines containing token count fields.
    kiro-cli logs token usage in several formats depending on version:
      - {"inputTokens": N, "outputTokens": N}
      - {"usage": {"input_tokens": N, "output_tokens": N}}
      - "input_tokens=N output_tokens=N"
    """
    total_input = 0
    total_output = 0
    path = Path(log_path)

    if not path.exists():
        return 0, 0

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Try JSON parse first
            try:
                data = json.loads(line)
                # Format 1: top-level inputTokens/outputTokens
                if "inputTokens" in data:
                    total_input += int(data["inputTokens"])
                    total_output += int(data.get("outputTokens", 0))
                    continue
                # Format 2: nested usage object
                usage = data.get("usage", {})
                if isinstance(usage, dict) and "input_tokens" in usage:
                    total_input += int(usage["input_tokens"])
                    total_output += int(usage.get("output_tokens", 0))
                    continue
                # Format 3: response metadata
                meta = data.get("metadata", data.get("response", {}))
                if isinstance(meta, dict):
                    if "input_tokens" in meta:
                        total_input += int(meta["input_tokens"])
                        total_output += int(meta.get("output_tokens", 0))
                        continue
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            # Try regex on plain text lines
            m_in = re.search(r"input_tokens[=:]\s*(\d+)", line)
            m_out = re.search(r"output_tokens[=:]\s*(\d+)", line)
            if m_in:
                total_input += int(m_in.group(1))
            if m_out:
                total_output += int(m_out.group(1))

    return total_input, total_output


def _estimate_from_audit(audit_path: str, workflow_id: str) -> tuple[int, int]:
    """Estimate token counts from audit log interaction text lengths.

    Uses len(text) / CHARS_PER_TOKEN as a rough approximation.
    This is a fallback when kiro-cli logs are not available.
    """
    total_input_chars = 0
    total_output_chars = 0
    path = Path(audit_path)

    if not path.exists():
        return 0, 0

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            if rec.get("workflow_id") != workflow_id:
                continue
            if rec.get("type") != "interaction":
                continue

            payload = rec.get("payload", {})
            total_input_chars += len(payload.get("input_prompt", ""))
            total_output_chars += len(payload.get("ai_output", ""))

    # If interaction records have minimal text, use a heuristic based on
    # compute time and typical token throughput (~30 tokens/sec output)
    input_tokens = int(total_input_chars / CHARS_PER_TOKEN)
    output_tokens = int(total_output_chars / CHARS_PER_TOKEN)

    return input_tokens, output_tokens
def _estimate_from_compute_time(audit_path: str, workflow_id: str) -> tuple[int, int]:
    """Estimate token counts from workflow duration and LLM throughput rates.

    Uses workflow_start/workflow_end timestamps to compute elapsed time,
    then applies ~40 output tokens/sec and 2.5x input/output ratio.
    More accurate than text-length estimation when interaction records
    contain short summaries.
    """
    OUTPUT_TOKENS_PER_SEC = 40.0
    INPUT_OUTPUT_RATIO = 2.5

    path = Path(audit_path)
    if not path.exists():
        return 0, 0

    start_ts = None
    end_ts = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("workflow_id") != workflow_id:
                continue
            if rec.get("type") != "event":
                continue
            et = rec.get("payload", {}).get("event_type", "")
            if et == "workflow_start":
                start_ts = rec.get("timestamp")
            elif et == "workflow_end":
                end_ts = rec.get("timestamp")

    if not start_ts or not end_ts:
        return 0, 0

    try:
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        s = datetime.strptime(start_ts, fmt).replace(tzinfo=timezone.utc)
        e = datetime.strptime(end_ts, fmt).replace(tzinfo=timezone.utc)
        elapsed = (e - s).total_seconds()
    except ValueError:
        return 0, 0

    if elapsed <= 0:
        return 0, 0

    output_tokens = int(elapsed * OUTPUT_TOKENS_PER_SEC)
    input_tokens = int(output_tokens * INPUT_OUTPUT_RATIO)
    return input_tokens, output_tokens


def _compute_hash(prev_hash: str, content: str) -> str:
    """Compute SHA-256 hash for audit chain."""
    return hashlib.sha256(f"{prev_hash}{content}".encode()).hexdigest()


def _get_last_hash(audit_path: str) -> str:
    """Get the content_hash of the last record in the audit log."""
    last_hash = ""
    path = Path(audit_path)
    if not path.exists():
        return last_hash
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                last_hash = rec.get("content_hash", "")
            except json.JSONDecodeError:
                continue
    return last_hash


def inject_token_usage(
    audit_path: str,
    workflow_id: str,
    input_tokens: int,
    output_tokens: int,
    method: str,
) -> None:
    """Append a token_usage interaction record to the audit NDJSON."""
    prev_hash = _get_last_hash(audit_path)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    record = {
        "id": f"token-usage-{workflow_id}",
        "timestamp": timestamp,
        "type": "interaction",
        "workflow_id": workflow_id,
        "initiator": "finops-token-extractor",
        "payload": {
            "input_prompt": f"[token extraction — {method}]",
            "ai_output": f"input_tokens={input_tokens} output_tokens={output_tokens}",
            "agent_role": "system",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
        "previous_hash": prev_hash,
    }
    content = json.dumps(record, sort_keys=True)
    record["content_hash"] = _compute_hash(prev_hash, content)

    path = Path(audit_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    print(f"Injected token usage: input={input_tokens:,} output={output_tokens:,} method={method}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract and inject LLM token usage")
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--audit-log", default="audit/audit.ndjson")
    parser.add_argument("--kiro-log", default=None,
                        help="Path to kiro-cli log file (checked first)")
    parser.add_argument("--input-tokens", type=int, default=None,
                        help="Manual input token count (overrides all)")
    parser.add_argument("--output-tokens", type=int, default=None,
                        help="Manual output token count (overrides all)")
    args = parser.parse_args()

    input_tokens = 0
    output_tokens = 0
    method = "none"

    # Priority 1: Parse kiro-cli log (most accurate — actual LLM API token counts)
    # Always attempt this first. Requires KIRO_LOG_LEVEL=trace during the run.
    log_path = args.kiro_log or os.environ.get(
        "KIRO_LOG_PATH",
        os.path.join(os.environ.get("TMPDIR", "/tmp"), "kiro-log", "kiro-chat.log"),
    )
    input_tokens, output_tokens = _parse_kiro_log(log_path)
    if input_tokens > 0 or output_tokens > 0:
        method = "kiro-log"
        print(f"[token-extract] Parsed kiro-cli log: {log_path}")
        print(f"[token-extract] input={input_tokens:,} output={output_tokens:,}")

    # Priority 2: Manual override (if kiro log had nothing)
    if method == "none" and args.input_tokens is not None and args.output_tokens is not None:
        input_tokens = args.input_tokens
        output_tokens = args.output_tokens
        method = "manual"
        print(f"[token-extract] Using manual values: input={input_tokens:,} output={output_tokens:,}")

    # Priority 3: Estimate from compute time (fallback)
    # Uses workflow_start/workflow_end timestamps × throughput rate.
    # More accurate than text-length estimation when interaction records
    # contain short summaries rather than full LLM conversation text.
    if method == "none":
        input_tokens, output_tokens = _estimate_from_compute_time(
            args.audit_log, args.workflow_id
        )
        if input_tokens > 0:
            method = "estimated-from-compute-time"
            print(f"[token-extract] Estimated from compute time: input={input_tokens:,} output={output_tokens:,}")

    # Priority 4: Estimate from audit text (last resort)
    if method == "none":
        input_tokens, output_tokens = _estimate_from_audit(
            args.audit_log, args.workflow_id
        )
        if input_tokens > 0 or output_tokens > 0:
            method = "estimated-from-text"
            print(f"[token-extract] Estimated from text: input={input_tokens:,} output={output_tokens:,}")

    if input_tokens == 0 and output_tokens == 0:
        print("[token-extract] WARN: No token data found — skipping injection")
        return 0

    inject_token_usage(
        args.audit_log, args.workflow_id,
        input_tokens, output_tokens, method,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
