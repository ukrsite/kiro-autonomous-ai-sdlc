# Guardrail Configurations

**Project:** Autonomous AI SDLC Prototype
**Version:** 2.0
**Last Updated:** 2026-04-09

---

## Overview

This document describes the guardrails framework implemented via Kiro steering files and hooks. Guardrails enforce quality, security, and safety standards across all AI workflows without custom framework code.

---

## Steering Files

### Always-On Steering (Applied to Every Interaction)

| File | Purpose | Key Rules |
|------|---------|-----------|
| `security-rules.md` | Security enforcement | No hardcoded secrets, input validation, dependency scanning, SQL injection prevention |
| `coding-standards.md` | Code quality | Review requirements, coverage thresholds, documentation standards, no dead code |
| `sandbox-boundaries.md` | Isolation enforcement | No production access, no external URLs, no PII |
| `finops-cost-reporting.md` | Cost reporting | Call `calculate_workflow_cost` after every workflow run, include cost table in final response |

### Language-Specific Steering (Applied by File Type)

| File | Globs | Key Rules |
|------|-------|-----------|
| `java-guardrails.md` | `**/*.java` | Java coding standards, Maven conventions, JUnit patterns |
| `nodejs-guardrails.md` | `**/*.js`, `**/*.ts` | Node.js standards, npm security, Jest patterns |
| `python-guardrails.md` | `**/*.py` | Python standards, ruff compliance, pytest patterns |

### Manual-Inclusion Steering (Activated Per Workflow)

| File | Purpose | When Used |
|------|---------|-----------|
| `checkpoint-enforcement.md` | Checkpoint pipeline definition | Before any merge operation |
| `merge-policy.md` | Merge rules and requirements | During code integration |

---

## Hook-Based Guardrails

| Hook | Trigger | Action | Purpose |
|------|---------|--------|---------|
| `on-code-change` | `fileEdited` on code files | Run security scan | Catch vulnerabilities early |
| `on-new-file` | `fileCreated` | Lint + audit log | Enforce standards on new code |
| `checkpoint-guard` | `preToolUse` on git_commit | Verify all checkpoints | Block unvalidated merges |


---

## Checkpoint Pipeline

The checkpoint pipeline enforces this sequence before any merge:

```
Code Review → Security Scan → Test Coverage → Merge
```

Each checkpoint must pass. If any fails:
1. Workflow halts
2. Failure details logged to audit-logger MCP
3. Merge is blocked
4. Rollback available via git-rollback MCP

---

## Configuration Management

Guardrails are configurable without code changes:
- **Add a rule:** Edit the relevant steering file markdown
- **Add a language:** Create a new `fileMatch` steering file with appropriate globs
- **Modify thresholds:** Update values in `coding-standards.md`
- **Disable a guardrail:** Remove or rename the steering file

---

## Coverage Thresholds by Workflow

| Workflow | Minimum Coverage | Scope |
|----------|-----------------|-------|
| WF1 — Requirement to Software | 80% | New code |
| WF2 — Autonomous Refactoring | 80% | All code; pre-existing tests must pass |
| WF3 — Dependency Upgrades | 70% | Full suite post-upgrade |
| WF4 — Bug Fix | 90% | Fix + regression tests |
| WF5 — Documentation | N/A | No code coverage required |

---

## FinOps Cost Reporting

The `finops-cost-reporting.md` steering file (always-on) instructs the agent to call `calculate_workflow_cost` from the finops-cost-estimator MCP server at the end of every workflow run.

**Trigger:** After the `workflow_end` event is logged to audit-logger.

**Output:** A formatted cost table included in the agent's final response, plus JSON and Markdown reports written to `reports/finops/`.

**Cost model:** `config/finops-cost-model.yml` — unit prices and per-file scaling factors. Update this file to adjust pricing without code changes.

**Dimensions tracked:**

| Dimension | Unit |
|-----------|------|
| LLM Input Tokens | per 1K tokens |
| LLM Output Tokens | per 1K tokens |
| Compute Time | per second |
| MCP Tool Calls | per invocation |
| Checkpoints | per execution |

This is best-effort — a cost reporting failure never blocks or delays the workflow response.
