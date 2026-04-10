# AI-DLC and WF1–WF5 Integration

**Project:** Autonomous AI SDLC Prototype  
**Version:** 2.0  
**Last Updated:** 2026-04-09

---

## Overview

AI-DLC (AI-Driven Development Life Cycle) is a three-phase adaptive methodology that governs the full software development lifecycle. It does not implement code itself — instead, it plans, classifies, and hands off to one of five specialized Construction workflows (WF1–WF5). This document explains how the two layersV connect.

```
User Request
     |
     v
+------------------+
|  AI-DLC INCEPTION |  <-- planning, requirements, WF selection
+------------------+
     |
     | Handoff Artifact
     v
+------------------+
|  WF1 / WF2 / WF3 |  <-- implementation, checkpoints, merge
|  WF4 / WF5       |
+------------------+
     |
     v
+------------------+
|  OPERATIONS      |  <-- placeholder (future)
+------------------+
```

---

## The Three Phases

### INCEPTION (AI-DLC owns this)

AI-DLC runs the INCEPTION phase for every request. It is adaptive — stages execute only when they add value.

| Stage | Always / Conditional | Purpose |
|---|---|---|
| Workspace Detection | Always | Detect brownfield vs greenfield, check for prior state |
| Reverse Engineering | Conditional (brownfield only) | Analyze existing codebase |
| Requirements Analysis | Always | Gather and document functional + non-functional requirements |
| User Stories | Conditional | Create stories and personas when user-facing impact exists |
| Workflow Planning | Always | Classify request, select WF, produce Handoff Artifact |
| Application Design | Conditional | Design new components or service layers |
| Units Generation | Conditional | Decompose into parallel units of work |

INCEPTION ends by producing a **Handoff Artifact** at `aidlc-docs/inception/plans/workflow-handoff.md`. This is the contract between INCEPTION and CONSTRUCTION.

### CONSTRUCTION (WF1–WF5 own this)

AI-DLC delegates all CONSTRUCTION stages to the selected WF. The WF reads the Handoff Artifact and uses `aidlc-docs/inception/requirements/requirements.md` as its authoritative input — no repeated planning.

### OPERATIONS (placeholder)

Reserved for future deployment and monitoring workflows.

---

## The Handoff Artifact

The Handoff Artifact is created at the end of Workflow Planning. It is the single source of truth passed from INCEPTION to CONSTRUCTION.

**Location:** `aidlc-docs/inception/plans/workflow-handoff.md`

**Contents:**
- Selected WF identifier and classification rationale
- Intent analysis summary (clarity, scope, complexity)
- References to requirements and reverse engineering artifacts
- Table of INCEPTION stages completed
- Table of CONSTRUCTION stages delegated to the WF

The selected WF checks for this artifact at startup. If it exists, the WF skips its own requirements gathering and uses the INCEPTION output directly.

---

## WF Classification Rules

Workflow Planning classifies the request and selects a WF based on intent:

| Request Type | Selected WF |
|---|---|
| New feature, enhancement | WF1 — Requirement to Software |
| Refactoring, technical debt | WF2 — Autonomous Refactoring |
| Dependency upgrade, migration | WF3 — Dependency Upgrades |
| Bug fix | WF4 — Bug Fix |
| Documentation | WF5 — Documentation |

The default workflow is `auto` — the AI-DLC classifier selects the WF at runtime based on the request. The user sees the classification and can override it before CONSTRUCTION begins. In CI, the prompt includes override signals: "refactor/refactoring → WF2, upgrade/dependency → WF3, bug/fix/crash → WF4, document/docs → WF5".

---

## WF1 — Requirement to Software

**Skill:** `.kiro/skills/developer-skills/wf1-requirement-to-software/`  
**Use when:** New features or enhancements  
**Coverage threshold:** 80% line coverage on new code

WF1 is the most comprehensive workflow. It maps directly to Kiro's spec-driven development pattern.

**Steps:**
1. Load Handoff Artifact (or accept raw requirement if no INCEPTION ran)
2. Generate `design.md` and `tasks.md` (skips `requirements.md` if INCEPTION provided it)
3. Create git restore point
4. Implement tasks — code, unit tests, inline docs
5. Code Review checkpoint
6. Test Coverage checkpoint (≥80%)
7. Security Scan checkpoint
8. Generate documentation artifacts — 5 mandatory per service:
   - `docs/release-notes-{ISSUE_KEY}.md`
   - `docs/CHANGELOG.md` (append)
   - `docs/openapi.yaml` (if REST endpoints)
   - `docs/architecture.md`
   - `docs/wf1-summary-{ISSUE_KEY}.md` (summary report with checkpoints, files, cost)
9. Merge to target branch
10. Log `workflow_end` to audit-logger
11. Calculate and report workflow cost (finops-cost-estimator MCP)

**Multi-service mode:** When `SERVICE_NAME=all-services`, WF1 inspects and updates all services in the sandbox. Each service gets its own tests, coverage measurement, and doc artifacts.

**Checkpoints (all must pass before merge):**

| Checkpoint | Pass Criteria |
|---|---|
| Code Review | Correctness, conventions, no dead code, no security issues |
| Test Coverage | ≥80% line coverage; all tests pass |
| Security Scan | No HIGH or CRITICAL findings from security-scanner MCP |

**MCP dependencies:** audit-logger, security-scanner, git-rollback, finops-cost-estimator

---

## WF2 — Autonomous Refactoring

**Skill:** `.kiro/skills/developer-skills/wf2-autonomous-refactoring/`  
**Use when:** Reducing technical debt, modernizing code patterns  
**Coverage threshold:** 80% line coverage; all pre-existing tests must pass

WF2 refactors legacy code while guaranteeing behavioral equivalence. It never changes public API signatures unless explicitly requested.

**Steps:**
1. Analyze legacy code — identify smells, duplication, complexity
2. Create git restore point
3. Apply refactoring (extract method, rename, simplify conditionals, DRY)
4. Run existing tests — all must pass, zero failures
5. Behavior Equivalence checkpoint — compare original vs refactored outputs
6. Performance Benchmark checkpoint — max 10% degradation tolerance
7. Security Scan checkpoint
8. Generate documentation artifacts
9. Generate delta report (before/after metrics, patterns applied)
10. Log `workflow_end` to audit-logger

**Checkpoints:**

| Checkpoint | Pass Criteria |
|---|---|
| Existing Tests | All pre-existing tests pass (zero failures) |
| Test Coverage | ≥80% maintained |
| Behavior Equivalence | Identical outputs for identical inputs |
| Performance | No degradation beyond 10% threshold |
| Security Scan | No new HIGH or CRITICAL vulnerabilities |

**MCP dependencies:** audit-logger, security-scanner, git-rollback, finops-cost-estimator

---

## WF3 — Dependency Upgrades

**Skill:** `.kiro/skills/developer-skills/wf3-dependency-upgrades/`  
**Use when:** Periodic dependency maintenance, security patching, migrations  
**Coverage threshold:** 70% line coverage; full test suite must pass

WF3 scans for outdated dependencies, checks compatibility, applies upgrades, and resolves breaking changes automatically.

**Steps:**
1. Create git restore point (snapshots lockfiles: `pom.xml`, `package-lock.json`, `requirements.txt`)
2. Scan outdated dependencies via dependency-scanner MCP (`scope`: all / security / major / minor)
3. Check compatibility and generate ordered upgrade plan
4. Generate code updates for breaking changes (import changes, API call updates, type fixes)
5. Run full test suite (≥70% coverage)
6. Security Scan checkpoint — no new CVEs introduced
7. Generate documentation artifacts
8. Generate delta report (old vs new versions, breaking changes resolved, test results)
9. Log `workflow_end` to audit-logger

**Checkpoints:**

| Checkpoint | Pass Criteria |
|---|---|
| Test Suite | All tests pass; ≥70% coverage |
| Security Scan | No new HIGH or CRITICAL CVEs introduced |
| Compatibility | All breaking changes resolved |

**Upgrade priority order:** security patches → minor/patch → major versions

**MCP dependencies:** dependency-scanner, git-rollback, security-scanner, audit-logger, finops-cost-estimator

---

## WF4 — Bug Fix

**Skill:** `.kiro/skills/developer-skills/wf4-bug-fix/`  
**Use when:** Investigating and resolving defects  
**Coverage threshold:** 90% line coverage on fix and regression tests

WF4 performs structured root cause analysis before writing any code, then validates the fix with side-effect analysis to prevent regressions.

**Steps:**
1. Root cause analysis — reproduce bug, trace execution, document root cause
2. Create git restore point
3. Generate minimal fix — only the change needed to resolve the defect
4. Generate regression tests — must fail without fix, pass with fix
5. Run full test suite (existing + regression, ≥90% coverage)
6. Side-Effect Analysis checkpoint — verify no new defects in callers/dependents
7. Security Scan checkpoint
8. Fix Validation checkpoint — final gate combining all prior results
9. Generate documentation artifacts (release notes with root cause summary)
10. Log `workflow_end` to audit-logger

**Checkpoints:**

| Checkpoint | Pass Criteria |
|---|---|
| Existing Tests | All pre-existing tests pass (zero regressions) |
| Regression Tests | All new regression tests pass |
| Test Coverage | ≥90% on fix and regression tests |
| Side-Effect Analysis | No new defects introduced |
| Security Scan | No new HIGH or CRITICAL vulnerabilities |

**MCP dependencies:** audit-logger, security-scanner, git-rollback, finops-cost-estimator

---

## WF5 — Documentation

**Skill:** `.kiro/skills/developer-skills/wf5-documentation/`  
**Use when:** Generating or updating project documentation  
**Coverage threshold:** None (no code coverage required)

WF5 analyzes an existing codebase and generates API docs, architecture diagrams, and onboarding guides. It validates accuracy against the actual code before finalizing.

**Steps:**
1. Analyze codebase — scan public interfaces, module structure, existing docs
2. Generate API documentation (all public functions, classes, methods, examples)
3. Generate architecture diagrams (Mermaid: component, interaction, data flow, layer)
4. Generate onboarding guides (setup, environment, navigation, conventions)
5. Accuracy Validation checkpoint — API signatures match code, examples compile, references resolve
6. Completeness Review checkpoint — all public interfaces and major components covered
7. Generate delta report (new sections, outdated content, gaps)
8. Log `workflow_end` to audit-logger

**Checkpoints:**

| Checkpoint | Pass Criteria |
|---|---|
| Accuracy Validation | Docs match actual code; examples are valid; references resolve |
| Completeness Review | All requested doc types fully covered |

**MCP dependencies:** audit-logger, finops-cost-estimator

---

## Shared Infrastructure

All five workflows share the same MCP server infrastructure:

| MCP Server | Tools | Used By |
|---|---|---|
| audit-logger | `log_interaction`, `log_checkpoint`, `log_event`, `query_audit` | All WFs |
| security-scanner | `scan_code`, `scan_dependencies`, `get_scan_report` | WF1, WF2, WF3, WF4 |
| dependency-scanner | `scan_outdated`, `check_compatibility`, `get_upgrade_plan` | WF3 |
| git-rollback | `create_restore_point`, `rollback`, `verify_consistency`, `list_restore_points` | WF1, WF2, WF3, WF4 |
| finops-cost-estimator | `estimate_workflow_cost`, `calculate_workflow_cost`, `get_cost_report`, `get_historical_baseline` | All WFs |

Every workflow logs a `workflow_end` event to audit-logger at completion, creating a tamper-evident SHA-256 hash chain across the full session. The finops-cost-estimator reads this event to compute post-run actuals and writes a cost report to `reports/finops/`.

---

## Checkpoint Enforcement

Security rules (`security-rules.md`) require that before any merge:

1. `security-scanner` MCP `scan_code` runs on all modified files
2. Any HIGH or CRITICAL finding **blocks** the merge
3. Results are logged via `audit-logger` MCP `log_checkpoint`

Coverage thresholds are enforced per workflow:

| WF | Minimum Coverage |
|---|---|
| WF1 | 80% on new code |
| WF2 | 80%; all pre-existing tests pass |
| WF3 | 70%; full test suite passes |
| WF4 | 90% on fix + regression tests |
| WF5 | None |

If any checkpoint fails, the WF halts, reports the failure, and uses `git-rollback` MCP to restore the pre-change state (WF1–WF4).

---

## Rollback Strategy

WF1, WF2, WF3, and WF4 all create a restore point before making changes:

```
create_restore_point()  →  make changes  →  checkpoints
                                                 |
                                         pass: merge + log
                                         fail: rollback() + log
```

Restore points snapshot both the git commit and lockfiles. `verify_consistency` can be called post-rollback to confirm the test suite is green.

---

## Audit Trail

Every action across INCEPTION and all WFs is logged to `audit/audit.ndjson` via the audit-logger MCP. The log is append-only with a SHA-256 hash chain for tamper evidence.

Key event types:

| Event Type | When |
|---|---|
| `workflow_start` | WF begins execution |
| `workflow_end` | WF completes (pass or fail) |
| `checkpoint_passed` | A quality gate passes |
| `checkpoint_failed` | A quality gate fails — merge blocked |
| `rollback` | Git restore point activated |

Query the audit log with `query_audit` filtering by `workflow_id`, `record_type`, `outcome`, or date range.

---

## Directory Structure

```
aidlc-docs/                          # AI-DLC INCEPTION artifacts
├── audit.md                         # Human-readable audit log
├── aidlc-state.md                   # Workflow state tracking
└── inception/
    ├── requirements/
    │   └── requirements.md          # Authoritative input for WFs
    └── plans/
        ├── execution-plan.md        # Stage execution plan
        └── workflow-handoff.md      # INCEPTION → CONSTRUCTION contract

.kiro/skills/developer-skills/       # WF skill definitions
├── wf1-requirement-to-software/SKILL.md
├── wf2-autonomous-refactoring/SKILL.md
├── wf3-dependency-upgrades/SKILL.md
├── wf4-bug-fix/SKILL.md
└── wf5-documentation/SKILL.md

audit/
└── audit.ndjson                     # Tamper-evident audit log (append-only)
```

---

## Related Documentation

| Document | Description |
|---|---|
| `docs/ai-dlc.md` | AI-DLC setup, platform configuration, and quick start |
| `docs/architecture-documentation.md` | Full system architecture and component inventory |
| `docs/workflow-descriptions.md` | E2E workflow descriptions with inputs and outputs |
| `docs/guardrail-configurations.md` | Steering files and hook configurations |
