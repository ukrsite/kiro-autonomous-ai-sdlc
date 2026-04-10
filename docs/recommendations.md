# Recommendations for Organizational Rollout

**Project:** Autonomous AI SDLC Prototype
**Version:** 4.0
**Last Updated:** 2026-04-09

---

## Overview

This document provides reusable patterns and guidance for adopting AI-driven SDLC workflows across the organization, based on findings from the prototype. The system has been validated end-to-end: Jira ticket → GitLab CI → kiro-cli → tested code → merge request.

---

## Reusable Patterns

### Pattern 1: Steering Files as Guardrails

**Description:** Use always-on steering files to enforce security, coding standards, and sandbox boundaries without custom framework code.

**When to Use:** Any project using AI-assisted development.

**Implementation:**
- Create `security-rules.md` (always-on) for universal security rules
- Create language-specific steering files with `fileMatch` globs (e.g. `**/*.java`, `**/*.py`)
- Create `manual` steering files for workflow-specific policies (e.g. `checkpoint-enforcement.md`)
- Add `finops-cost-reporting.md` (always-on) to enforce cost reporting at the end of every workflow run

**Observed Effectiveness:** High. Always-on steering files enforced security, coding standards, and cost reporting consistently across all workflows without per-workflow configuration. The AI correctly respected sandbox boundary constraints without requiring enforcement in the workflow skill itself. Language-specific steering correctly scoped rules to relevant file types.

---

### Pattern 2: Skills as Workflow Definitions

**Description:** Encode repeatable AI workflows as Kiro skills with structured steps, checkpoints, and expected outputs. Use natural language SKILL.md files rather than YAML schemas.

**When to Use:** Any repeatable AI-driven process (code generation, refactoring, upgrades, documentation).

**Implementation:**
- One skill per workflow with `SKILL.md`, `references/`, and `scripts/`
- Define explicit checkpoints with pass/fail criteria
- Include rollback instructions for failure cases
- Load shared rule details from `.kiro/aws-aidlc-rule-details/` for consistent cross-workflow behavior
- Scope all file writes to `sandbox_path` from the handoff artifact — never write to the orchestration repo root

**Observed Effectiveness:** High. Skills produced correct, tested code and test files across multiple end-to-end runs. Shared rule loading from `aws-aidlc-rule-details/` ensured consistent error handling, security enforcement, and code generation standards across all five workflows.

---

### Pattern 3: MCP Servers for Infrastructure

**Description:** Lightweight MCP servers provide tool-based access to infrastructure (audit logging, security scanning, dependency analysis, Git operations, cost tracking).

**When to Use:** Any project needing structured tool access for AI agents.

**Implementation:**
- Python MCP servers using the `mcp` SDK with stdio transport
- Configure in agent JSON files under `mcpServers`
- Each server exposes focused, well-defined tools
- Run via stdio in CI (Python direct); use Docker locally
- Use `setup-kiro.sh` to generate environment-specific `mcp.json` — CI and local configs differ in transport but expose identical tools
- Deploy server Docker images to ECR via CI on merge to main

**Current MCP servers:**

| Server | Tools | Used By |
|--------|-------|---------|
| audit-logger | `log_interaction`, `log_checkpoint`, `log_event`, `query_audit` | All WFs |
| security-scanner | `scan_code`, `scan_dependencies`, `get_scan_report` | WF1–WF4 |
| dependency-scanner | `scan_outdated`, `check_compatibility`, `get_upgrade_plan` | WF3 |
| git-rollback | `create_restore_point`, `rollback`, `verify_consistency`, `list_restore_points` | WF1–WF4 |
| finops-cost-estimator | `estimate_workflow_cost`, `calculate_workflow_cost`, `get_cost_report`, `get_historical_baseline` | All WFs |

**Observed Effectiveness:** High. All five MCP servers operated reliably via stdio in CI. The security scanner caught real issues in generated Python code. The audit-logger's SHA-256 hash chain provided verifiable traceability. The finops-cost-estimator produced accurate post-run cost reports by reading the existing audit log — no additional instrumentation was needed in the workflows themselves. Note: avoid defining MCP servers in both agent configs and `mcp.json` — it produces duplicate warnings in CI logs.

---

### Pattern 4: Hook-Based Checkpoint Enforcement

**Description:** Use `preToolUse` hooks to enforce validation gates before critical operations (commits, merges, deployments).

**When to Use:** Any project requiring quality gates on AI-generated output.

**Implementation:**
- `preToolUse` hook on `git_commit` to verify all checkpoints passed
- `postToolUse` hook on `*` for universal audit logging
- `fileEdited` hooks for real-time security scanning on code changes

**Observed Effectiveness:** High. The `preToolUse` checkpoint guard reliably blocked commits when checkpoints had not passed. The hook-based approach requires zero changes to the workflow skills — enforcement is orthogonal to implementation.

---

### Pattern 5: Append-Only Audit Logging

**Description:** Append-only NDJSON with SHA-256 hash chains provides verifiable audit trails for all AI actions.

**When to Use:** Any environment requiring traceability and compliance for AI-generated changes.

**Implementation:**
- NDJSON format for simple append and query
- SHA-256 hash chain linking each record to its predecessor
- Structured record types: `interaction`, `checkpoint`, `event`
- Log `workflow_start`, `inception_complete`, `construction_start`, `code-generation`, `security-scan`, `workflow_end` events at minimum
- The finops-cost-estimator reads this log post-run — no separate cost instrumentation needed

**Observed Effectiveness:** High. The audit-logger MCP produced complete, queryable audit trails on every pipeline run. The hash chain provides tamper evidence. The NDJSON format is simple to parse and append without risk of overwriting existing records.

---

### Pattern 6: Two-Repository Architecture

**Description:** Separate the AI orchestration configuration (skills, steering, hooks, MCP servers, pipeline) from the application code that the AI modifies.

**When to Use:** Any project where AI generates or modifies application code in CI.

**Implementation:**
- Orchestration repo: skills, steering, hooks, agent configs, MCP servers, CI pipeline
- Sandbox repo: application services that receive AI-generated code
- CI pipeline clones the sandbox repo, runs kiro-cli inside it, then pushes the branch and creates an MR
- Always set working directory explicitly before running AI tools
- Exclude `.git` from sandbox artifacts (reduces size); re-clone fresh in `finalize` and overlay changes

**Observed Effectiveness:** High. The separation cleanly prevented AI-generated code from polluting the orchestration repo. It also enables the same orchestration repo to target multiple sandbox services (java-api, python-processor, node-gateway) via configuration. The re-clone-and-overlay pattern in `finalize` avoids git history corruption from artifact-based workflows.

---

### Pattern 7: Retry Wrapper for AI Tool Resilience

**Description:** Wrap kiro-cli invocations in a retry script with exponential backoff to handle transient failures in CI.

**When to Use:** Any CI pipeline running AI tools that may experience transient failures (network, rate limits, model timeouts).

**Observed Effectiveness:** High. Retry logic recovered from transient kiro-cli failures without manual intervention.

---

### Pattern 8: FinOps Cost Tracking via Audit Log

**Description:** Derive per-run cost actuals from the existing audit log rather than adding instrumentation to each workflow. A post-run MCP tool reads `workflow_start`/`workflow_end` timestamps, tool invocation events, and checkpoint records to compute cost across five dimensions.

**When to Use:** Any project that needs cost visibility for AI workflow runs.

**Implementation:**
- Deploy `finops-cost-estimator` MCP server with `config/finops-cost-model.yml` for unit prices
- Add `finops-cost-reporting.md` as an always-on steering file — the agent calls `calculate_workflow_cost` automatically after every run
- Pre-run estimates via `estimate_workflow_cost` use historical p50 baselines once enough runs accumulate
- Reports written to `reports/finops/` as JSON + Markdown for archiving and review
- Deploy the server Docker image to ECR via a dedicated CI job (`deploy:finops-mcp-server`) on merge to main
- Add `estimate_workflow_cost` to `autoApprove` in `mcp.json` — without it, pre-run estimates require manual approval

**Observed Effectiveness:** High. Zero workflow changes were needed — the cost estimator reads the audit log that already existed. The steering file handles surfacing the cost table in the agent's final response. Historical baselines improve estimate accuracy over time.

---

### Pattern 9: Environment-Aware MCP Config Generation

**Description:** Auto-generate environment-specific `mcp.json` rather than maintaining separate configs manually. CI uses stdio transport (Python direct); local uses Docker transport. Both expose identical tools.

**When to Use:** Any project where MCP servers need to run in both CI (Kubernetes pods, no Docker daemon) and local development (Docker available).

**Implementation:**
- `setup-kiro.sh` detects `$CI` environment variable and writes the appropriate transport config
- CI config: `"command": "python3", "args": ["/path/to/server.py"]` pointing to local paths
- Local config: `"command": "docker", "args": ["run", ...]` with volume mounts for data directories
- The `MCP_SERVERS` array in the script is the authoritative list — adding a server here automatically includes it in both configs
- Run `setup-kiro.sh` as part of `before_script` in every CI job that needs MCP access

**Observed Effectiveness:** High. Eliminated a whole class of "works locally, fails in CI" MCP configuration issues. When a new server was added without updating the script, it was caught in review rather than discovered through silent CI failures.

---

### Pattern 10: Multi-Service Pipeline Runs

**Description:** Support `SERVICE_NAME=all-services` to inspect and update all sandbox services in a single pipeline run, with per-service test isolation in checkpoint gates.

**When to Use:** Cross-cutting features that affect multiple services (e.g., adding config endpoints to all services).

**Implementation:**
- Add `all-services` entry to `jira-project-mappings.yml` with `repo_path: services`
- Validate stage sets `multi_service: true` and passes individual `service_paths` list
- `build_kiro_prompt.py` generates a multi-service scope instruction for the agent
- Python-tests iterates per service directory; Java/Node tests detect project files automatically
- Each service gets its own test run, coverage measurement, and doc artifacts

**Observed Effectiveness:** High. The agent correctly inspected all 3 services, added endpoints to each, generated per-service tests (34 total), and produced 5 doc artifacts per service — all in a single ~7 minute pipeline run.

---

### Pattern 11: Mandatory Documentation via Checkbox Enforcement

**Description:** Use `- [ ]` checkbox items with "MANDATORY" language to force AI agents to produce all required artifacts, rather than bullet lists that are treated as suggestions.

**When to Use:** Any workflow step where the agent must produce specific output files.

**Implementation:**
- List each artifact as a checkbox item with explicit file path and template reference
- Include "MANDATORY — do not skip any" in the step description
- Reference templates from `references/output-templates.md` for consistent format
- The CI prompt mirrors the same "MANDATORY: Generate ALL" language

**Observed Effectiveness:** High. Before this change, the agent only generated 1 of 5 doc artifacts. After switching to checkboxes with mandatory language, all 5 artifacts are consistently produced.

---

### Pattern 12: Rate-Limit Aware Retry for AI Tools

**Description:** Differentiate between transient errors (short backoff) and rate limits (long cooldown) in retry logic for AI tool invocations.

**When to Use:** Any CI pipeline running AI tools that may hit platform rate limits.

**Implementation:**
- Capture command output to a temp file for analysis
- Grep for rate-limit signals: "rate limit", "quota exceeded", "429", "throttle"
- Apply 60s minimum cooldown on rate limit (vs 15s for transient errors)
- Cap max backoff at 300s to avoid excessive waits
- Log retry events for debugging

**Observed Effectiveness:** High. Recovered from Kiro platform rate limits that previously caused pipeline failures after 3 quick retries.

---

## Rollout Guidance

### Phase 1: Pilot (1–2 Teams)
- Deploy sandbox environment with steering files and audit logging
- Start with WF1 (Requirement to Software) — lowest risk, highest visibility
- Use the two-repository architecture from day one — don't mix orchestration and application code
- Provision a dedicated CI service account for kiro-cli (not a personal token)
- Deploy all MCP server images to ECR via CI on merge to main
- Establish baseline metrics for comparison, including cost per run via finops-cost-estimator

### Phase 2: Expand Workflows (3–4 Teams)
- Add WF2 (Refactoring) and WF3 (Dependency Upgrades)
- Tune guardrail thresholds based on pilot feedback
- Train teams on skill authoring and steering file configuration
- Integrate Jira automation rules for trigger-based pipeline execution
- Review finops baselines after 10+ runs to validate estimate accuracy

### Phase 3: Organization-Wide
- Enable optional workflows (WF4, WF5) based on demand
- Integrate with existing CI/CD pipelines using the validated GitLab pipeline as a template
- Establish governance model for steering file management (who can modify security-rules.md, etc.)
- Replace personal kiro-cli tokens with org-managed service accounts
- Set cost budgets per workflow type using finops baselines as reference

---

## Risk Mitigations

| Risk | Mitigation | Priority | Status |
|------|-----------|----------|--------|
| AI generates insecure code | Always-on security steering + preToolUse checkpoint + bandit/safety in CI | Critical | Implemented |
| AI accesses production systems | Sandbox boundary steering + network isolation | Critical | Implemented |
| Audit log tampering | SHA-256 hash chain + append-only NDJSON storage | High | Implemented |
| Workflow failures block development | Git-based restore points + rollback MCP + retry wrapper | High | Implemented |
| Over-reliance on AI output | Mandatory code review checkpoint + human MR review | Medium | Implemented |
| CI service account expiry | Dedicated service account (not personal token) | Medium | Open — personal token in use |
| AI tool writes to wrong repository | Explicit working directory + post-clone verification | High | Implemented |
| Jira transition failures break pipeline | Non-blocking Jira API calls + fallback comment | Low | Implemented |
| New MCP server omitted from setup script | CI lint step cross-checking `MCP_SERVERS` array vs `mcp-servers/` directory | Medium | Open — manual review only |
| MCP server image out of date | `deploy:finops-mcp-server` CI job builds and pushes on merge to main | Medium | Implemented (finops); partial for others |

---

## Metrics to Track

| Metric | Purpose | Target | Observed |
|--------|---------|--------|----------|
| Workflow success rate | Reliability | >80% | ~85% (3 validated E2E runs) |
| Checkpoint pass rate | Quality | >90% | Not yet measured at scale |
| Mean time to rollback | Recovery | <5 minutes | <2 minutes (git-rollback MCP) |
| Security issues caught | Safety | 100% HIGH/CRITICAL blocked | Bandit/safety blocking confirmed |
| Developer satisfaction | Adoption | Positive trend | Not yet measured |
| Pipeline duration (Jira → MR) | Efficiency | <15 minutes | ~10–12 minutes observed |
| Cost per workflow run | FinOps | Tracked per run | ~$0.50–$1.50 (WF1, varies by scope) |
| Estimate vs actual variance | FinOps accuracy | <20% variance | Baseline accumulating |

---

## Known Gaps for Production Readiness

1. kiro-cli is authenticated with a personal user account — a dedicated CI service account is required for stable, auditable CI execution.
2. Jira status transition names are not validated before use — add a pre-flight check that queries available transitions and fails fast with a clear error if the target status doesn't exist.
3. No alerting on pipeline failure — the `on-failure` stage transitions Jira to "AI Dev Failed" but does not notify the team via Slack or email.
4. Coverage thresholds are enforced per-workflow in steering files and now validated in CI for Java, Python, and Node.js.
5. No automated check that `setup-kiro.sh`'s `MCP_SERVERS` array matches the actual `mcp-servers/` directory — new servers can be silently omitted from generated configs.
6. Only `finops-cost-estimator` has a dedicated CI deploy job — the other four MCP server images require manual builds and pushes to ECR.
7. Docker MCP images become stale after code changes — must rebuild locally after modifying `server.py`. No automatic rebuild trigger.
8. LLM token counts are estimated from compute time, not exact — kiro-cli doesn't expose token usage to MCP servers. Accuracy depends on the 40 tok/s throughput assumption.
9. Helm chart version can race with semantic-release — the helm job needs `needs: [release]` in the sandbox CI to ensure it picks up the new version.
