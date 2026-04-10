# Requirements Document

## Introduction

This document defines the requirements for the FinOps Workflow Cost Estimation feature. The feature enables FinOps practitioners and engineering teams to estimate the cost of a WF1 (Requirement to Software) or WF2 (Autonomous Refactoring) run before it starts, and to calculate the actual cost after the run completes. Cost dimensions include LLM token consumption, compute time, MCP server tool invocations, and checkpoint execution. Estimates are derived from historical audit data and workflow metadata; actuals are captured from the audit trail produced by the audit-logger MCP. Reports are surfaced as structured artifacts and optionally logged back to the audit trail for traceability.

The feature integrates with the existing audit-logger MCP (`mcp-servers/audit-logger/server.py`) and the NDJSON audit log at `audit/audit.ndjson`. It does not modify any existing workflow behavior — it is a read/compute/report layer on top of the existing infrastructure.

## Glossary

- **Cost_Estimator**: The component that computes a pre-run cost estimate for a WF1 or WF2 run given a set of input parameters.
- **Cost_Calculator**: The component that computes the actual cost of a completed WF1 or WF2 run by reading audit records for that workflow run.
- **Cost_Report**: A structured artifact (JSON + human-readable Markdown) containing cost dimensions, totals, and variance between estimate and actual.
- **Cost_Dimension**: A single measurable cost axis. Defined dimensions: `llm_tokens_input`, `llm_tokens_output`, `compute_time_seconds`, `mcp_tool_invocations`, `checkpoint_executions`.
- **Cost_Model**: A configuration file that maps each Cost_Dimension to a unit price (e.g., USD per 1K tokens, USD per second of compute). Stored at `config/finops-cost-model.yml`.
- **Workflow_Run**: A single execution of WF1 or WF2, identified by a `workflow_id` in the audit log.
- **Pre_Run_Estimate**: A cost projection produced by the Cost_Estimator before a Workflow_Run starts, based on scope inputs and historical baselines.
- **Post_Run_Actuals**: The measured cost of a completed Workflow_Run, computed by the Cost_Calculator from audit records.
- **Variance_Report**: The comparison between Pre_Run_Estimate and Post_Run_Actuals for the same Workflow_Run, expressed as absolute and percentage differences per Cost_Dimension.
- **Historical_Baseline**: Aggregated statistics (mean, p50, p95) per Cost_Dimension computed from past Workflow_Runs of the same type, used to seed Pre_Run_Estimates.
- **Scope_Input**: User-provided parameters that describe the size and complexity of the planned run (e.g., number of files to modify, estimated lines of code, number of checkpoints expected).
- **FinOps_MCP_Server**: A new MCP server (`mcp-servers/finops-cost-estimator/`) that exposes cost estimation and calculation tools to the AI agent.
- **Audit_Logger_MCP**: The existing MCP server at `mcp-servers/audit-logger/server.py` that records workflow events to `audit/audit.ndjson`.
- **WF1_Workflow**: The Requirement to Software workflow. Produces audit records for interactions, checkpoints, and events.
- **WF2_Workflow**: The Autonomous Refactoring workflow. Produces audit records for interactions, checkpoints, and events.

## Requirements

### Requirement 1: Pre-Run Cost Estimation for WF1

**User Story:** As a FinOps practitioner, I want to estimate the cost of a WF1 run before it starts, so that I can budget and approve the run before committing compute and LLM resources.

#### Acceptance Criteria

1. WHEN a user provides Scope_Input for a planned WF1_Workflow run, THE Cost_Estimator SHALL produce a Pre_Run_Estimate covering all five Cost_Dimensions: `llm_tokens_input`, `llm_tokens_output`, `compute_time_seconds`, `mcp_tool_invocations`, and `checkpoint_executions`.
2. THE Cost_Estimator SHALL compute the Pre_Run_Estimate by applying the Cost_Model unit prices to the projected dimension quantities derived from Scope_Input and Historical_Baseline data for WF1_Workflow runs.
3. WHEN no Historical_Baseline exists for WF1_Workflow (zero prior runs), THE Cost_Estimator SHALL use the default baseline values defined in the Cost_Model configuration file and SHALL include a `baseline_source: "default"` field in the Pre_Run_Estimate.
4. WHEN Historical_Baseline data exists for WF1_Workflow, THE Cost_Estimator SHALL use the p50 (median) of each Cost_Dimension from prior runs as the baseline and SHALL include a `baseline_source: "historical"` field and the count of runs used in the Pre_Run_Estimate.
5. THE Pre_Run_Estimate SHALL include a `total_estimated_cost_usd` field that is the sum of all Cost_Dimension costs computed using Cost_Model unit prices.
6. THE Pre_Run_Estimate SHALL include a `confidence_level` field with value `"low"`, `"medium"`, or `"high"` based on the number of historical runs available: fewer than 3 runs yields `"low"`, 3–9 runs yields `"medium"`, 10 or more runs yields `"high"`.
7. THE Cost_Estimator SHALL produce the Pre_Run_Estimate within 5 seconds of receiving the Scope_Input.

### Requirement 2: Pre-Run Cost Estimation for WF2

**User Story:** As a FinOps practitioner, I want to estimate the cost of a WF2 run before it starts, so that I can evaluate whether the refactoring effort is cost-justified before execution.

#### Acceptance Criteria

1. WHEN a user provides Scope_Input for a planned WF2_Workflow run, THE Cost_Estimator SHALL produce a Pre_Run_Estimate covering all five Cost_Dimensions using WF2_Workflow-specific Historical_Baseline data.
2. THE Cost_Estimator SHALL treat WF1_Workflow and WF2_Workflow Historical_Baselines as separate data sets — WF1 history SHALL NOT influence WF2 estimates and vice versa.
3. WHEN Scope_Input includes a `files_to_refactor` count, THE Cost_Estimator SHALL scale the `llm_tokens_input`, `llm_tokens_output`, and `compute_time_seconds` estimates proportionally to that count using the per-file scaling factors defined in the Cost_Model.
4. THE Pre_Run_Estimate for WF2_Workflow SHALL include a `behavior_equivalence_overhead_usd` field representing the additional cost of the behavior equivalence checkpoint, derived from the Cost_Model.
5. THE Pre_Run_Estimate SHALL include a `total_estimated_cost_usd` field and a `confidence_level` field using the same rules as Requirement 1.

### Requirement 3: Post-Run Actual Cost Calculation for WF1 and WF2

**User Story:** As a FinOps practitioner, I want to calculate the actual cost of a completed WF1 or WF2 run, so that I can track real spend and compare it against the pre-run estimate.

#### Acceptance Criteria

1. WHEN a `workflow_id` for a completed Workflow_Run is provided, THE Cost_Calculator SHALL read all audit records for that `workflow_id` from `audit/audit.ndjson` and compute Post_Run_Actuals for all five Cost_Dimensions.
2. THE Cost_Calculator SHALL derive `mcp_tool_invocations` from the count of audit records with `type: "event"` and `payload.event_type: "tool_invocation"` for the given `workflow_id`.
3. THE Cost_Calculator SHALL derive `checkpoint_executions` from the count of audit records with `type: "checkpoint"` for the given `workflow_id`.
4. THE Cost_Calculator SHALL derive `compute_time_seconds` from the elapsed time between the `workflow_start` event timestamp and the `workflow_end` event timestamp for the given `workflow_id`.
5. IF no `workflow_start` or `workflow_end` event exists for the given `workflow_id`, THEN THE Cost_Calculator SHALL return an error indicating the Workflow_Run is incomplete or not found, and SHALL NOT produce partial Post_Run_Actuals.
6. THE Cost_Calculator SHALL apply Cost_Model unit prices to the measured dimension quantities to produce a `total_actual_cost_usd` field.
7. THE Cost_Calculator SHALL produce Post_Run_Actuals within 10 seconds for a Workflow_Run with up to 10,000 audit records.

### Requirement 4: Variance Report Between Estimate and Actuals

**User Story:** As a FinOps practitioner, I want to see the variance between the pre-run estimate and the post-run actuals for the same workflow run, so that I can improve future estimates and identify cost overruns.

#### Acceptance Criteria

1. WHEN a Pre_Run_Estimate and Post_Run_Actuals exist for the same Workflow_Run, THE Cost_Report SHALL include a Variance_Report section comparing each Cost_Dimension's estimated vs. actual quantity and cost.
2. THE Variance_Report SHALL express variance as both an absolute difference (`actual - estimate`) and a percentage difference (`(actual - estimate) / estimate * 100`) per Cost_Dimension.
3. WHEN any Cost_Dimension's actual cost exceeds the estimate by more than 20%, THE Variance_Report SHALL flag that dimension with `overrun: true`.
4. THE Variance_Report SHALL include a `total_variance_usd` field equal to `total_actual_cost_usd - total_estimated_cost_usd`.
5. IF no Pre_Run_Estimate exists for a given Workflow_Run, THEN THE Cost_Report SHALL produce Post_Run_Actuals only, with the Variance_Report section omitted and a `variance_available: false` field set.

### Requirement 5: Cost Report Output Format

**User Story:** As a FinOps practitioner, I want cost reports in both machine-readable and human-readable formats, so that I can integrate them into dashboards and share them with stakeholders.

#### Acceptance Criteria

1. THE Cost_Report SHALL be produced in two formats: a JSON file and a Markdown file, both written to `reports/finops/` with filenames including the `workflow_id` and a timestamp.
2. THE Cost_Report JSON SHALL conform to a defined schema with fields: `workflow_id`, `workflow_type`, `generated_at`, `estimate` (nullable), `actuals` (nullable), `variance` (nullable), `cost_model_version`.
3. THE Cost_Report Markdown SHALL include a human-readable summary table of Cost_Dimensions with columns: Dimension, Estimated Quantity, Actual Quantity, Estimated Cost (USD), Actual Cost (USD), Variance (USD), Variance (%).
4. WHEN only a Pre_Run_Estimate is available (pre-run report), THE Cost_Report Markdown SHALL clearly label the report as "Pre-Run Estimate" and omit the Actual and Variance columns.
5. WHEN both estimate and actuals are available (post-run report), THE Cost_Report Markdown SHALL label the report as "Post-Run Cost Report" and include all columns.
6. THE Cost_Report Pretty_Printer SHALL format Cost_Report JSON objects back into valid Markdown reports.
7. FOR ALL valid Cost_Report JSON objects, serializing then deserializing then serializing SHALL produce an equivalent object (round-trip property).

### Requirement 6: Cost Model Configuration

**User Story:** As a FinOps administrator, I want to configure unit prices and scaling factors in a central configuration file, so that I can update pricing without modifying code.

#### Acceptance Criteria

1. THE Cost_Model SHALL be stored as a YAML file at `config/finops-cost-model.yml` and SHALL define unit prices for each Cost_Dimension and default baseline values for WF1_Workflow and WF2_Workflow.
2. WHEN the Cost_Model file is loaded, THE FinOps_MCP_Server SHALL validate that all required fields are present and that all unit prices are non-negative numbers.
3. IF the Cost_Model file is missing or contains invalid values, THEN THE FinOps_MCP_Server SHALL return a descriptive error identifying the missing or invalid field and SHALL NOT produce any estimates or actuals.
4. THE Cost_Model SHALL include a `version` field. THE Cost_Report SHALL record the `cost_model_version` used at report generation time so that reports remain reproducible when the Cost_Model is updated.
5. WHERE a `wf1_per_file_scaling` factor is defined in the Cost_Model, THE Cost_Estimator SHALL apply it to scale WF1_Workflow estimates when `files_to_modify` is provided in Scope_Input.
6. WHERE a `wf2_per_file_scaling` factor is defined in the Cost_Model, THE Cost_Estimator SHALL apply it to scale WF2_Workflow estimates when `files_to_refactor` is provided in Scope_Input.

### Requirement 7: Historical Baseline Computation

**User Story:** As a FinOps practitioner, I want the system to automatically build historical baselines from past workflow runs, so that estimates improve over time without manual calibration.

#### Acceptance Criteria

1. THE Cost_Calculator SHALL update the Historical_Baseline for the relevant workflow type (WF1 or WF2) after computing Post_Run_Actuals for a completed Workflow_Run.
2. THE Historical_Baseline SHALL store, per Cost_Dimension per workflow type: count of runs, mean, p50 (median), and p95 values.
3. WHEN the Historical_Baseline is updated, THE new p50 and p95 values SHALL be recomputed from all available Post_Run_Actuals records for that workflow type.
4. THE Historical_Baseline SHALL be persisted to `reports/finops/baselines.json` so that it survives process restarts.
5. IF the `baselines.json` file is corrupt or unparseable, THEN THE FinOps_MCP_Server SHALL fall back to Cost_Model default baseline values and SHALL log a warning event via the Audit_Logger_MCP.
6. FOR ALL sequences of Post_Run_Actuals records added to the Historical_Baseline in any order, THE resulting p50 and p95 values SHALL be identical (order-independence property).

### Requirement 8: Audit Trail Integration

**User Story:** As a FinOps practitioner, I want cost estimates and actuals to be recorded in the audit trail, so that I have a tamper-evident record of all cost events for compliance and retrospective analysis.

#### Acceptance Criteria

1. WHEN a Pre_Run_Estimate is produced, THE FinOps_MCP_Server SHALL log a `cost_estimate_produced` event to the Audit_Logger_MCP including the `workflow_id`, `workflow_type`, `total_estimated_cost_usd`, `confidence_level`, and `cost_model_version`.
2. WHEN Post_Run_Actuals are computed, THE FinOps_MCP_Server SHALL log a `cost_actuals_computed` event to the Audit_Logger_MCP including the `workflow_id`, `workflow_type`, `total_actual_cost_usd`, and `cost_model_version`.
3. WHEN a Variance_Report is generated, THE FinOps_MCP_Server SHALL log a `cost_variance_reported` event to the Audit_Logger_MCP including the `workflow_id`, `total_variance_usd`, and any Cost_Dimensions flagged with `overrun: true`.
4. THE audit events logged by the FinOps_MCP_Server SHALL use the existing `log_event` tool of the Audit_Logger_MCP and SHALL be queryable via the existing `query_audit` tool using `workflow_type` and `record_type` filters.
5. THE FinOps_MCP_Server SHALL NOT modify, delete, or rewrite any existing audit records — it SHALL only append new records via the Audit_Logger_MCP.

### Requirement 9: FinOps MCP Server Tool Interface

**User Story:** As a developer integrating the FinOps capability into the AI agent, I want a well-defined MCP tool interface, so that the agent can invoke cost estimation and calculation as standard tool calls.

#### Acceptance Criteria

1. THE FinOps_MCP_Server SHALL expose a `estimate_workflow_cost` tool that accepts `workflow_type` (`"wf1"` or `"wf2"`), `scope_input` (object), and optional `workflow_id` (string) parameters and returns a Pre_Run_Estimate object.
2. THE FinOps_MCP_Server SHALL expose a `calculate_workflow_cost` tool that accepts `workflow_id` (string) and returns Post_Run_Actuals and, if a Pre_Run_Estimate exists for that `workflow_id`, a Variance_Report.
3. THE FinOps_MCP_Server SHALL expose a `get_cost_report` tool that accepts `workflow_id` (string) and `format` (`"json"` or `"markdown"`) and returns the Cost_Report in the requested format.
4. THE FinOps_MCP_Server SHALL expose a `get_historical_baseline` tool that accepts `workflow_type` (`"wf1"` or `"wf2"`) and returns the current Historical_Baseline statistics for that workflow type.
5. IF an unknown `workflow_type` value is passed to any tool, THEN THE FinOps_MCP_Server SHALL return a descriptive error and SHALL NOT produce any output.
6. THE FinOps_MCP_Server SHALL run via stdio transport, consistent with all other MCP servers in the project.

### Requirement 10: LLM Token Dimension Tracking

**User Story:** As a FinOps practitioner, I want LLM token consumption tracked as a first-class cost dimension, so that I can understand and optimize the largest cost driver in AI workflow runs.

#### Acceptance Criteria

1. THE Cost_Calculator SHALL derive `llm_tokens_input` and `llm_tokens_output` from audit records of type `"interaction"` for the given `workflow_id`, summing the token counts recorded in `payload.input_tokens` and `payload.output_tokens` fields respectively.
2. WHEN audit interaction records do not contain explicit token count fields, THE Cost_Calculator SHALL estimate token counts using a character-to-token ratio of 4 characters per token applied to `payload.input_prompt` and `payload.ai_output` field lengths, and SHALL set `token_count_method: "estimated"` in the Post_Run_Actuals.
3. WHEN audit interaction records contain explicit token count fields, THE Cost_Calculator SHALL use those values directly and SHALL set `token_count_method: "recorded"` in the Post_Run_Actuals.
4. THE Cost_Model SHALL define separate unit prices for `llm_tokens_input` and `llm_tokens_output` to reflect typical asymmetric pricing of LLM APIs (output tokens are generally more expensive than input tokens).
