# Implementation Plan: FinOps Workflow Cost Estimation

## Overview

Implement a new FastMCP server (`mcp-servers/finops-cost-estimator/server.py`) that provides
pre-run cost estimation, post-run actual cost calculation, variance reporting, and historical
baseline management for WF1 and WF2 workflow runs. The server reads `audit/audit.ndjson`
directly, writes reports to `reports/finops/`, and logs FinOps events via the existing
audit-logger MCP. All cost configuration lives in `config/finops-cost-model.yml`.

## Tasks

- [x] 1. Create project scaffold and cost model configuration
  - Create `mcp-servers/finops-cost-estimator/` directory with `__init__.py`
  - Create `config/finops-cost-model.yml` with unit prices, defaults for WF1/WF2, and
    per-file scaling factors as specified in the design data model section
  - Create `tests/finops/__init__.py` to establish the test package
  - Create `reports/finops/.gitkeep` so the output directory is tracked
  - _Requirements: 6.1, 6.4_

- [x] 2. Implement cost model loader and validator
  - [x] 2.1 Implement `_load_cost_model(path: str) -> dict` in `server.py`
    - Read and parse `config/finops-cost-model.yml` with PyYAML
    - Validate all required fields are present: `version`, `unit_prices.*`,
      `defaults.wf1.*`, `defaults.wf2.*`, `scaling.wf1_per_file.*`, `scaling.wf2_per_file.*`
    - Validate all unit prices are non-negative numbers
    - Raise `ValueError` with descriptive message identifying the missing/invalid field
    - Cache result at module level; call once at server startup
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 2.2 Write property test for cost model validation (Property 14)
    - **Property 14: Cost_Model validation accepts valid and rejects invalid configs**
    - **Validates: Requirements 6.2, 6.3, 10.4**
    - Use `hypothesis` `st.fixed_dictionaries` to generate valid configs and assert acceptance
    - Use `st.one_of` to inject missing fields or negative prices and assert `ValueError`

  - [x] 2.3 Write unit tests for cost model loader in `tests/finops/test_cost_model_loader.py`
    - Test: valid YAML loads and returns expected dict
    - Test: missing `version` field raises descriptive `ValueError`
    - Test: negative unit price raises descriptive `ValueError`
    - Test: missing file raises error with path in message
    - _Requirements: 6.2, 6.3_

- [x] 3. Implement baseline manager
  - [x] 3.1 Implement `_load_baseline(path: str) -> dict` and `_save_baseline(baseline: dict, path: str)`
    - Load `reports/finops/baselines.json`; return empty structure `{"wf1": {}, "wf2": {}}` if missing
    - On corrupt/unparseable JSON, log warning via audit-logger MCP and return empty structure
    - `_save_baseline` writes atomically (write to temp file, rename)
    - _Requirements: 7.4, 7.5_

  - [x] 3.2 Implement `_update_baseline(baseline: dict, workflow_type: str, actuals: dict) -> dict`
    - Append new actuals record to the in-memory list for the given workflow type
    - Recompute `count`, `mean`, `p50` (via `statistics.median`), and `p95` (via sorted list
      index or `numpy.percentile`) for each Cost_Dimension
    - WF1 and WF2 baseline data sets must remain strictly independent
    - _Requirements: 7.1, 7.2, 7.3, 7.6_

  - [ ]* 3.3 Write property test for baseline order-independence (Property 17)
    - **Property 17: Baseline order-independence**
    - **Validates: Requirements 7.6**
    - Generate a list of actuals records with `st.lists`; shuffle permutations and assert
      identical `p50`/`p95` for all dimensions

  - [ ]* 3.4 Write property test for WF1/WF2 baseline independence (Property 5)
    - **Property 5: WF1 and WF2 baselines are independent**
    - **Validates: Requirements 2.2**
    - Add arbitrary WF1 actuals; assert WF2 baseline stats are unchanged, and vice versa

  - [ ]* 3.5 Write property test for baseline persistence round-trip (Property 16)
    - **Property 16: Baseline persistence round-trip**
    - **Validates: Requirements 7.4**
    - Generate a `HistoricalBaseline` dict; save then load; assert field-for-field equivalence

  - [ ]* 3.6 Write property test for baseline statistics correctness (Property 15)
    - **Property 15: Baseline statistics correctness**
    - **Validates: Requirements 7.2, 7.3**
    - Generate lists of floats; assert computed `p50` equals `statistics.median` and `p95`
      equals the 95th-percentile value

  - [x] 3.7 Write unit tests for baseline manager in `tests/finops/test_baseline_manager.py`
    - Test: missing `baselines.json` returns empty structure without error
    - Test: corrupt JSON falls back to empty structure and logs warning
    - Test: `_update_baseline` increments count and recomputes stats correctly
    - _Requirements: 7.1, 7.2, 7.4, 7.5_

- [x] 4. Implement cost estimator
  - [x] 4.1 Implement `_estimate_cost(workflow_type, scope_input, cost_model, baseline) -> dict`
    - Select WF1 or WF2 baseline; fall back to cost model defaults when no history exists
    - Set `baseline_source: "default"` or `"historical"` and `baseline_run_count`
    - Apply per-file scaling: `base_quantity + files * per_file_factor` for
      `llm_tokens_input`, `llm_tokens_output`, `compute_time_seconds`
    - Multiply each dimension quantity by its unit price to produce `estimated_cost_usd`
    - Sum all dimension costs to `total_estimated_cost_usd`
    - Compute `confidence_level`: `"low"` if count < 3, `"medium"` if 3–9, `"high"` if ≥ 10
    - Include `behavior_equivalence_overhead_usd` for WF2 from cost model
    - Raise descriptive error for unknown `workflow_type`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 2.5, 6.5, 6.6_

  - [ ]* 4.2 Write property test for all five dimensions in estimate (Property 1)
    - **Property 1: Estimate contains all five cost dimensions**
    - **Validates: Requirements 1.1, 2.1, 2.4**
    - Use `st.sampled_from(["wf1", "wf2"])` and a `scope_input` strategy; assert all five
      dimension keys present in returned estimate

  - [ ]* 4.3 Write property test for dimension cost equals quantity × unit price (Property 2)
    - **Property 2: Dimension cost equals quantity times unit price**
    - **Validates: Requirements 1.2, 3.6**
    - Generate arbitrary positive quantities and unit prices; assert
      `estimated_cost_usd == quantity * unit_price` within floating-point tolerance

  - [ ]* 4.4 Write property test for total cost equals sum of dimension costs (Property 3)
    - **Property 3: Total cost equals sum of dimension costs**
    - **Validates: Requirements 1.5, 4.4**
    - Assert `total_estimated_cost_usd == sum(dim["estimated_cost_usd"] for dim in dimensions)`

  - [ ]* 4.5 Write property test for confidence level thresholds (Property 4)
    - **Property 4: Confidence level matches run count thresholds**
    - **Validates: Requirements 1.6, 2.5**
    - Use `st.integers(min_value=0)` for run count; assert correct `confidence_level` bucket

  - [ ]* 4.6 Write property test for file count scaling proportionality (Property 6)
    - **Property 6: File count scaling is proportional**
    - **Validates: Requirements 2.3, 6.5, 6.6**
    - Generate `files_to_modify` / `files_to_refactor` values; assert scaled quantity equals
      `base + k * per_file_factor` for each affected dimension

  - [x] 4.7 Write unit tests for cost estimator in `tests/finops/test_cost_estimator.py`
    - Test: WF1 estimate with 3 files produces expected total cost (known inputs → known output)
    - Test: WF2 estimate includes `behavior_equivalence_overhead_usd`
    - Test: zero historical runs → `baseline_source: "default"`, `confidence_level: "low"`
    - Test: 10 historical runs → `baseline_source: "historical"`, `confidence_level: "high"`
    - Test: unknown `workflow_type` returns descriptive error
    - _Requirements: 1.1–1.7, 2.1–2.5_

- [x] 5. Checkpoint — Ensure all estimator and baseline tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement cost calculator
  - [x] 6.1 Implement `_read_audit_records(workflow_id: str, audit_path: str) -> list[dict]`
    - Read `audit/audit.ndjson` line-by-line; parse each JSON line
    - Filter and return only records matching `workflow_id`
    - Return empty list (not error) when file is missing
    - _Requirements: 3.1_

  - [x] 6.2 Implement `_calculate_actuals(workflow_id, audit_records, cost_model) -> dict`
    - Extract `workflow_start` and `workflow_end` event timestamps; compute
      `compute_time_seconds` as elapsed seconds between them
    - Return error dict if either event is missing (per design error table)
    - Count `type == "event"` + `payload.event_type == "tool_invocation"` for
      `mcp_tool_invocations`
    - Count `type == "checkpoint"` records for `checkpoint_executions`
    - Sum `payload.input_tokens` / `payload.output_tokens` from `type == "interaction"`
      records; fall back to `len(field) / 4` when fields absent; set `token_count_method`
    - Apply unit prices; compute `total_actual_cost_usd`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 10.1, 10.2, 10.3_

  - [ ]* 6.3 Write property test for audit record counts matching dimensions (Property 7)
    - **Property 7: Audit record counts match computed dimension values**
    - **Validates: Requirements 3.1, 3.2, 3.3, 10.1**
    - Generate synthetic audit record lists; assert `mcp_tool_invocations`,
      `checkpoint_executions`, and token sums match direct counts of the generated records

  - [ ]* 6.4 Write property test for compute time from timestamps (Property 8)
    - **Property 8: Compute time derived from start and end timestamps**
    - **Validates: Requirements 3.4**
    - Generate pairs of ISO 8601 timestamps; assert `compute_time_seconds` equals
      `(end_ts - start_ts).total_seconds()`

  - [x] 6.5 Write unit tests for cost calculator in `tests/finops/test_cost_calculator.py`
    - Test: known audit records produce expected dimension values and total cost
    - Test: missing `workflow_start` returns error with correct message
    - Test: missing `workflow_end` returns error with correct message
    - Test: interaction records without token fields use char/4 estimate and set
      `token_count_method: "estimated"`
    - Test: interaction records with token fields use them directly and set
      `token_count_method: "recorded"`
    - Test: empty audit log returns error for unknown `workflow_id`
    - _Requirements: 3.1–3.7, 10.1–10.3_

- [x] 7. Implement variance calculator
  - [x] 7.1 Implement `_calculate_variance(estimate: dict, actuals: dict) -> dict`
    - For each dimension: compute `variance_usd = actual_cost_usd - estimated_cost_usd`
    - Compute `variance_pct = variance_usd / estimated_cost_usd * 100`
    - Set `overrun: True` when `actual_cost_usd > estimated_cost_usd * 1.2`
    - Sum `total_variance_usd = total_actual_cost_usd - total_estimated_cost_usd`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 7.2 Write property test for variance algebraic correctness (Property 9)
    - **Property 9: Variance report algebraic correctness**
    - **Validates: Requirements 4.1, 4.2, 4.4**
    - Generate arbitrary estimate and actuals dicts; assert all variance formulas hold
      within floating-point tolerance for every dimension and the total

  - [ ]* 7.3 Write property test for overrun flag at 20% threshold (Property 10)
    - **Property 10: Overrun flag when actual exceeds estimate by more than 20%**
    - **Validates: Requirements 4.3**
    - Generate `(estimated, actual)` pairs; assert `overrun == (actual > estimated * 1.2)`

  - [x] 7.4 Write unit tests for variance calculator in `tests/finops/test_variance.py`
    - Test: actuals equal to estimate → all variances zero, no overruns
    - Test: one dimension 25% over estimate → that dimension flagged `overrun: True`
    - Test: one dimension exactly 20% over → `overrun: False` (boundary)
    - Test: one dimension 20.01% over → `overrun: True` (boundary)
    - Test: `total_variance_usd` equals sum of per-dimension `variance_usd`
    - _Requirements: 4.1–4.4_

- [x] 8. Implement report generator
  - [x] 8.1 Implement `_generate_report(cost_report: dict, output_dir: str) -> dict`
    - Produce JSON file at `reports/finops/{workflow_id}_{timestamp}.json`
    - Produce Markdown file at `reports/finops/{workflow_id}_{timestamp}.md`
    - JSON must include all required top-level fields: `workflow_id`, `workflow_type`,
      `generated_at`, `estimate`, `actuals`, `variance`, `variance_available`,
      `cost_model_version`
    - Markdown pre-run report: label "Pre-Run Estimate", omit Actual/Variance columns
    - Markdown post-run report: label "Post-Run Cost Report", include all seven columns
    - Return error dict if `reports/finops/` is not writable
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 8.2 Implement `_pretty_print_report(cost_report: dict) -> str`
    - Accept a `CostReport` dict and return a valid Markdown string
    - _Requirements: 5.6_

  - [ ]* 8.3 Write property test for CostReport JSON schema completeness (Property 11)
    - **Property 11: Cost_Report JSON schema completeness**
    - **Validates: Requirements 5.2, 6.4**
    - Generate arbitrary `CostReport` dicts; assert all eight required top-level keys present
      in the serialized JSON

  - [ ]* 8.4 Write property test for Markdown required columns (Property 12)
    - **Property 12: Markdown rendering contains required columns**
    - **Validates: Requirements 5.3**
    - Generate `CostReport` dicts with both estimate and actuals; assert rendered Markdown
      contains all six column headers

  - [ ]* 8.5 Write property test for serialization round-trip (Property 13)
    - **Property 13: Cost_Report serialization round-trip**
    - **Validates: Requirements 5.7**
    - Serialize → deserialize → serialize; assert the two JSON strings are equivalent
      (order-independent field comparison)

  - [x] 8.6 Write unit tests for report generator in `tests/finops/test_report_generator.py`
    - Test: pre-run-only report omits Actual and Variance columns in Markdown
    - Test: post-run report includes all columns in Markdown
    - Test: `variance_available: false` when no estimate exists
    - Test: JSON output contains `cost_model_version` matching loaded cost model
    - Test: files written to correct paths with `workflow_id` and timestamp in filename
    - _Requirements: 5.1–5.7_

- [x] 9. Checkpoint — Ensure all calculator, variance, and report tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement audit logger client
  - [x] 10.1 Implement `_log_finops_event(event_type: str, payload: dict) -> None`
    - Call the audit-logger MCP's `log_event` tool via subprocess (same pattern as sibling
      MCP servers); pass `workflow_id`, `event_type`, and relevant cost fields
    - On subprocess failure or unavailability, log warning to stderr and continue —
      audit logging is best-effort
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 10.2 Write unit tests for audit logger client in `tests/finops/test_server_tools.py`
    - Test: `_log_finops_event` calls subprocess with correct arguments
    - Test: subprocess failure does not raise — warning logged to stderr
    - _Requirements: 8.1, 8.4, 8.5_

- [x] 11. Implement FinOps MCP server tools and wire all components
  - [x] 11.1 Implement `estimate_workflow_cost` MCP tool
    - Accept `workflow_type`, `scope_input`, optional `workflow_id`
    - Load cost model and baseline; call `_estimate_cost`
    - If `workflow_id` provided, persist estimate to `reports/finops/{workflow_id}_estimate.json`
      for later variance comparison
    - Call `_log_finops_event("cost_estimate_produced", ...)` with required fields
    - Return `PreRunEstimate` dict or `{"error": "..."}` on failure
    - _Requirements: 9.1, 9.5, 9.6, 8.1_

  - [x] 11.2 Implement `calculate_workflow_cost` MCP tool
    - Accept `workflow_id`
    - Read audit records via `_read_audit_records`; call `_calculate_actuals`
    - Load stored estimate (if any) and call `_calculate_variance`
    - Call `_update_baseline` and persist updated baseline
    - Call `_log_finops_event` for `cost_actuals_computed` and (if variance) `cost_variance_reported`
    - Return combined result dict or `{"error": "..."}` on failure
    - _Requirements: 9.2, 9.5, 9.6, 8.2, 8.3, 7.1_

  - [x] 11.3 Implement `get_cost_report` MCP tool
    - Accept `workflow_id` and `format` (`"json"` or `"markdown"`)
    - Load stored report files from `reports/finops/`; return content in requested format
    - Return `{"error": "..."}` if no report exists for the given `workflow_id`
    - _Requirements: 9.3, 9.5, 9.6_

  - [x] 11.4 Implement `get_historical_baseline` MCP tool
    - Accept `workflow_type`; load and return baseline stats for that type
    - Return `{"error": "..."}` for unknown `workflow_type`
    - _Requirements: 9.4, 9.5, 9.6_

  - [x] 11.5 Add `if __name__ == "__main__": mcp.run()` entry point
    - Confirm stdio transport consistent with all other MCP servers
    - _Requirements: 9.6_

  - [ ]* 11.6 Write property test for audit event produced per operation (Property 18)
    - **Property 18: Every FinOps operation produces a corresponding audit event**
    - **Validates: Requirements 8.1, 8.2, 8.3**
    - Mock `_log_finops_event`; call each tool; assert mock called with correct `event_type`
      and required payload fields

  - [ ]* 11.7 Write property test for audit append-only invariant (Property 19)
    - **Property 19: Audit append-only invariant**
    - **Validates: Requirements 8.5**
    - Record line count of `audit/audit.ndjson` before each FinOps tool call; assert count
      is non-decreasing and no existing lines are modified after the call

  - [x] 11.8 Write integration tests for MCP tool interface in `tests/finops/test_server_tools.py`
    - Test: `estimate_workflow_cost` with unknown `workflow_type` returns descriptive error
    - Test: `calculate_workflow_cost` with unknown `workflow_id` returns descriptive error
    - Test: `get_cost_report` with `format: "markdown"` returns string containing Markdown table
    - Test: `get_historical_baseline` with `"wf1"` returns dict with all five dimension keys
    - _Requirements: 9.1–9.6_

- [x] 12. Final checkpoint — Ensure all tests pass and coverage meets threshold
  - Run `pytest tests/finops/ --cov=mcp-servers/finops-cost-estimator --cov-report=term-missing`
  - Verify ≥ 80% line coverage on all new code in `mcp-servers/finops-cost-estimator/`
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `@settings(max_examples=100)` minimum
- Each property test must include a comment: `# Feature: finops-workflow-cost-estimation, Property N: <title>`
- All tool functions return `{"error": "..."}` dicts rather than raising exceptions,
  consistent with the existing MCP server pattern
- The server reads `audit/audit.ndjson` directly (file I/O); the audit-logger MCP is only
  used for writing new FinOps events
- Coverage target: 80% line coverage on `mcp-servers/finops-cost-estimator/` (WF1 threshold)
