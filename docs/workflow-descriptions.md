# E2E Workflow Descriptions

**Project:** Autonomous AI SDLC Prototype
**Version:** 2.0
**Last Updated:** 2026-04-09

---

## Overview

This document describes each end-to-end AI workflow implemented in the prototype, including inputs, outputs, checkpoints, and operational notes.

For a full explanation of how AI-DLC INCEPTION selects and hands off to these workflows, see [docs/aidlc-wf-integration.md](aidlc-wf-integration.md).

---

## WF1: Requirement to Working Software

**Status:** Mandatory
**Skill:** `skills/developer-skills/wf1-requirement-to-software/`

### Purpose
Transforms a natural language requirement into merged, tested, documented code.

### Input
- Natural language requirement or user story

### Workflow Steps
1. Start workflow — log `workflow_start` to audit-logger MCP
2. Parse requirement (from Handoff Artifact or raw input)
3. Create Kiro spec (design → tasks; skip requirements if INCEPTION provided them)
4. Create restore point (git-rollback MCP)
5. Implement tasks — code + unit tests (≥80% coverage) + inline docs
6. Code review checkpoint
7. Test coverage checkpoint (≥80%)
8. Security scan checkpoint
9. Generate documentation — 5 mandatory artifacts per service:
   - `docs/release-notes-{ISSUE_KEY}.md`
   - `docs/CHANGELOG.md` (append)
   - `docs/openapi.yaml` (if REST endpoints)
   - `docs/architecture.md`
   - `docs/wf1-summary-{ISSUE_KEY}.md` (summary report)
10. Merge to target branch
11. Log `workflow_end` to audit-logger MCP
12. Calculate and report workflow cost (finops-cost-estimator MCP)

### Output Artifacts
- Implemented code
- Unit tests
- Feature documentation
- Audit trail
- Cost report (`reports/finops/`)

### Checkpoints
| Checkpoint | Tool | Pass Criteria |
|-----------|------|---------------|
| Code Review | Manual / steering | Correctness, conventions, no security issues |
| Test Coverage | pytest / mvn / npm | ≥80% line coverage on new code |
| Security Scan | security-scanner MCP | No HIGH/CRITICAL vulnerabilities |

---

## WF2: Autonomous Refactoring

**Status:** Mandatory
**Skill:** `skills/developer-skills/wf2-autonomous-refactoring/`

### Purpose
Refactors legacy code while preserving behavior, reducing technical debt.

### Input
- Target module path + refactoring goals

### Workflow Steps
1. Analyze legacy code
2. Create restore point (git-rollback MCP)
3. Apply refactoring
4. Run existing tests
5. Behavior equivalence check
6. Performance benchmark
7. Security scan
8. Generate delta report
9. Log to audit

### Output Artifacts
- Refactored code
- Performance benchmarks (before/after)
- Delta report
- Audit trail
- Cost report (`reports/finops/`)

### Checkpoints
| Checkpoint | Tool | Pass Criteria |
|-----------|------|---------------|
| Existing Tests | pytest / mvn / npm | All pre-existing tests pass |
| Behavior Equivalence | compare_behavior.py | No behavioral differences |
| Performance | run_benchmarks.py | No degradation beyond threshold |
| Security Scan | security-scanner MCP | No new vulnerabilities |

---

## WF3: Periodic Dependency Upgrades

**Status:** Mandatory
**Skill:** `skills/developer-skills/wf3-dependency-upgrades/`

### Purpose
Upgrades outdated third-party dependencies with automated compatibility checking.

### Input
- Project path + scope (all / security / major / minor)

### Workflow Steps
1. Create restore point
2. Scan outdated dependencies (dependency-scanner MCP)
3. Check compatibility
4. Generate code updates for breaking changes
5. Run full test suite
6. Generate delta report
7. Log to audit

### Output Artifacts
- Updated dependency files
- Code updates for breaking changes
- Delta report
- Restore point ID
- Audit trail

### Checkpoints
| Checkpoint | Tool | Pass Criteria |
|-----------|------|---------------|
| Compatibility | dependency-scanner MCP | No unresolved breaking changes |
| Test Suite | pytest / mvn / npm | Full suite passes (≥70% coverage) |
| Security | security-scanner MCP | No new CVEs introduced |

---

## WF4: Autonomous Bug Investigation and Fix (Optional)

**Status:** Optional
**Skill:** `skills/developer-skills/wf4-bug-fix/`

### Purpose
Investigates bug reports, identifies root causes, generates fixes and regression tests.

### Input
- Bug report or failing test reference + target module

### Workflow Steps
1. Root cause analysis
2. Generate code fix
3. Generate regression tests
4. Side-effect analysis
5. Fix validation checkpoint
6. Log to audit

### Output Artifacts
- Code fix
- Regression tests
- Side-effect analysis report
- Audit trail

### Checkpoints
| Checkpoint | Tool | Pass Criteria |
|-----------|------|---------------|
| Fix Validation | validate_fix.py | Fix resolves bug, no regressions |
| Test Coverage | pytest / mvn / npm | ≥90% on fix + regression tests |
| Side-Effect | Test suite | No new failures introduced |

---

## WF5: Autonomous Documentation Update (Optional)

**Status:** Optional
**Skill:** `skills/developer-skills/wf5-documentation/`

### Purpose
Generates comprehensive documentation from an existing codebase.

### Input
- Target codebase path + doc types (api / architecture / onboarding)

### Workflow Steps
1. Analyze codebase
2. Generate API documentation
3. Generate architecture diagrams
4. Generate onboarding guides
5. Accuracy validation checkpoint
6. Completeness review checkpoint
7. Generate delta report
8. Log to audit

### Output Artifacts
- API documentation
- Architecture diagrams
- Onboarding guides
- Delta report
- Audit trail

### Checkpoints
| Checkpoint | Tool | Pass Criteria |
|-----------|------|---------------|
| Accuracy | validate_docs.py | Documentation matches code |
| Completeness | completeness-criteria.md | All public interfaces documented |

---

## FinOps: Workflow Cost Reporting

**MCP Server:** `mcp-servers/finops-cost-estimator/`
**Config:** `config/finops-cost-model.yml`
**Reports:** `reports/finops/`

### Purpose
Tracks the cost of every workflow run across five dimensions: LLM token usage, compute time, MCP tool calls, and checkpoint executions.

### Tools

| Tool | When | Description |
|------|------|-------------|
| `estimate_workflow_cost` | Before run | Pre-run estimate based on scope (files to modify, checkpoints) |
| `calculate_workflow_cost` | After run | Post-run actuals computed from the audit log |
| `get_cost_report` | On demand | Retrieve stored report as JSON or Markdown |
| `get_historical_baseline` | On demand | p50/p95 statistics from past runs |

### Cost Dimensions

| Dimension | Unit Price |
|-----------|-----------|
| LLM Input Tokens | $0.003 / 1K tokens |
| LLM Output Tokens | $0.015 / 1K tokens |
| Compute Time | $0.00005 / second |
| MCP Tool Calls | $0.0001 / call |
| Checkpoints | $0.001 / checkpoint |

Prices are defined in `config/finops-cost-model.yml` and can be updated without code changes.

### Automatic Reporting

The `finops-cost-reporting.md` steering file instructs the agent to call `calculate_workflow_cost` at the end of every workflow run and include a formatted cost table in its final response. Reports are also written to `reports/finops/` as `{workflow_id}_{timestamp}.json` and `.md`.

### Token Estimation

LLM token counts are estimated using a priority chain:
1. kiro-cli trace log (actual API counts) — requires `KIRO_LOG_LEVEL=trace`
2. Manual injection via `scripts/extract_token_usage.py`
3. Compute-time estimation (duration × 40 tok/s output × 2.5 input ratio)

Token estimation rates are configurable in `config/finops-cost-model.yml` under `scaling.token_estimation`.

### Baseline Learning

After each completed run, actuals are appended to `reports/finops/baselines.json`. Subsequent estimates use the p50 of historical runs instead of static defaults, improving accuracy over time. Confidence level is reported as `low` (<3 runs), `medium` (<10 runs), or `high` (≥10 runs).
