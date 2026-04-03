# Architecture Documentation

**Project:** Autonomous AI SDLC Prototype
**Version:** 1.0
**Last Updated:** [Date]

---

## Overview

The prototype implements autonomous AI-driven SDLC workflows using Kiro-native patterns. Instead of custom engines, the architecture maps directly to Kiro primitives: Skills (workflows), Steering files (guardrails), Hooks (triggers), Agent configs (routing), and MCP servers (infrastructure).

---

## Layered Architecture

```
┌─────────────────────────────────────────────────────┐
│              Interface Layer — Kiro CLI              │
│  Interactive | Headless (CI/CD) | .gitlab-ci.yml     │
├─────────────────────────────────────────────────────┤
│        Orchestration Layer — Hooks + Agents          │
│  fileEdited | userTriggered | preToolUse | cron      │
│  developer.json | devops.json | product-owner.json   │
├─────────────────────────────────────────────────────┤
│            Workflow Layer — Skills                    │
│  WF1 (Specs) | WF2 (Refactor) | WF3 (Deps)         │
│  WF4 (Bug Fix) | WF5 (Docs) | Delta Report          │
├─────────────────────────────────────────────────────┤
│     Guardrails Layer — Steering Files + Hooks        │
│  Always-on | fileMatch | Manual | preToolUse         │
├─────────────────────────────────────────────────────┤
│       Infrastructure Layer — MCP Servers + Git       │
│  audit-logger | security-scanner | dependency-scanner│
│  git-rollback | Git Repository | Sandbox             │
└─────────────────────────────────────────────────────┘
```

---

## Component Inventory

### MCP Servers

| Server | Language | Purpose | Tools |
|--------|----------|---------|-------|
| audit-logger | Python | Tamper-evident logging | `log_interaction`, `log_checkpoint`, `log_event`, `query_audit` |
| security-scanner | Python | Code & dependency scanning | `scan_code`, `scan_dependencies`, `get_scan_report` |
| dependency-scanner | Python | Outdated dependency detection | `scan_outdated`, `check_compatibility`, `get_upgrade_plan` |
| git-rollback | Python | Restore points & rollback | `create_restore_point`, `rollback`, `verify_consistency`, `list_restore_points` |

### Skills (Workflows)

| Skill | Directory | Agent | Mandatory |
|-------|-----------|-------|-----------|
| WF1 — Requirement to Software | `skills/developer-skills/wf1-requirement-to-software/` | developer | Yes |
| WF2 — Autonomous Refactoring | `skills/developer-skills/wf2-autonomous-refactoring/` | developer | Yes |
| WF3 — Dependency Upgrades | `skills/developer-skills/wf3-dependency-upgrades/` | developer | Yes |
| WF4 — Bug Fix | `skills/developer-skills/wf4-bug-fix/` | developer | No |
| WF5 — Documentation | `skills/developer-skills/wf5-documentation/` | developer | No |
| Delta Report Generator | `skills/shared-skills/delta-report-generator/` | shared | N/A |

### Agent Configurations

| Agent | Config | MCP Servers | Skills |
|-------|--------|-------------|--------|
| Developer | `agents/developer.json` | All 4 | All workflow skills |
| DevOps | `agents/devops.json` | audit-logger, security-scanner, git-rollback | DevOps skills |
| Product Owner | `agents/product-owner.json` | audit-logger | — |
| Solution Architect | `agents/solution-architect.json` | audit-logger | — |

### Steering Files (Guardrails)

| File | Inclusion | Scope |
|------|-----------|-------|
| `security-rules.md` | always | All interactions |
| `coding-standards.md` | always | All interactions |
| `sandbox-boundaries.md` | always | All interactions |
| `java-guardrails.md` | fileMatch (`**/*.java`) | Java files |
| `nodejs-guardrails.md` | fileMatch (`**/*.js`, `**/*.ts`) | JS/TS files |
| `python-guardrails.md` | fileMatch (`**/*.py`) | Python files |
| `checkpoint-enforcement.md` | manual | Merge operations |
| `merge-policy.md` | manual | Merge operations |

### Hooks (Triggers)

| Hook | Event | Action |
|------|-------|--------|
| `on-code-change` | fileEdited | Security scan |
| `on-new-file` | fileCreated | Lint + audit |
| `checkpoint-guard` | preToolUse (git_commit) | Verify checkpoints |

| `manual-wf2-refactor` | userTriggered | Execute WF2 |
| `manual-wf3-upgrade` | userTriggered | Execute WF3 |
| `manual-wf4-bugfix` | userTriggered | Execute WF4 |
| `manual-wf5-docs` | userTriggered | Execute WF5 |

---

## Data Flow

### Workflow Execution Flow

```
User/Cron → Kiro CLI → Agent Config → Skill (SKILL.md)
  → Steering Files (guardrails applied)
  → MCP Server calls (audit, security, deps, git)
  → Checkpoint validation
  → Output artifacts + audit trail
```

### Audit Data Flow

```
Any Action → audit-logger MCP → audit.ndjson (append-only)
  → SHA-256 hash chain (tamper evidence)
  → query_audit (filtering & search)
```

---

## Sample Application

| Module | Language | Build Tool | Purpose |
|--------|----------|------------|---------|
| `sample-app/java-module/` | Java | Maven | REST utilities, legacy code for WF2, outdated deps for WF3 |
| `sample-app/nodejs-module/` | Node.js | npm | Utility library, legacy code for WF2, outdated deps for WF3 |
| `sample-app/python-module/` | Python | pip/pytest | Calculator utilities, legacy code for WF2, outdated deps for WF3 |

---

## Deployment

- CI/CD: `.gitlab-ci.yml` with stages: lint → test → security → deploy
- Environment: Isolated sandbox, no production access
- Scheduled triggers: Cron + `kiro-cli chat --no-interactive`
- Retry: `scripts/retry-wrapper.sh` (3 retries, exponential backoff)
