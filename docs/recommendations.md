# Recommendations for Organizational Rollout

**Project:** Autonomous AI SDLC Prototype
**Version:** 2.0
**Last Updated:** 2026-04-02

---

## Overview

This document provides reusable patterns and guidance for adopting AI-driven SDLC workflows across the organization, based on findings from the 3-week prototype. The system has been validated end-to-end: Jira ticket → GitLab CI → kiro-cli → tested code → merge request.

---

## Reusable Patterns

### Pattern 1: Steering Files as Guardrails

**Description:** Use always-on steering files to enforce security, coding standards, and sandbox boundaries without custom framework code.

**When to Use:** Any project using AI-assisted development.

**Implementation:**
- Create `security-rules.md` (always-on) for universal security rules
- Create language-specific steering files with `fileMatch` globs (e.g. `**/*.java`, `**/*.py`)
- Create `manual` steering files for workflow-specific policies (e.g. `checkpoint-enforcement.md`)

**Observed Effectiveness:** High. Always-on steering files enforced security and coding standards consistently across all workflows without per-workflow configuration. The AI correctly respected sandbox boundary constraints without requiring enforcement in the workflow skill itself. Language-specific steering correctly scoped rules to relevant file types.

---

### Pattern 2: Skills as Workflow Definitions

**Description:** Encode repeatable AI workflows as Kiro skills with structured steps, checkpoints, and expected outputs. Use natural language SKILL.md files rather than YAML schemas.

**When to Use:** Any repeatable AI-driven process (code generation, refactoring, upgrades, documentation).

**Implementation:**
- One skill per workflow with `SKILL.md`, `references/`, and `scripts/`
- Define explicit checkpoints with pass/fail criteria
- Include rollback instructions for failure cases
- Load shared rule details from `.kiro/aws-aidlc-rule-details/` for consistent cross-workflow behavior

**Observed Effectiveness:** High. WF1 (Requirement to Software) consistently produced controller, service, model, and test files across multiple end-to-end runs. Shared rule loading from `aws-aidlc-rule-details/` ensured consistent error handling, security enforcement, and code generation standards across all five workflows.

---

### Pattern 3: MCP Servers for Infrastructure

**Description:** Lightweight MCP servers provide tool-based access to infrastructure (audit logging, security scanning, dependency analysis, Git operations).

**When to Use:** When AI agents need structured access to external tools or services.

**Implementation:**
- Python MCP servers using the `mcp` SDK with stdio transport
- Configure in agent JSON files under `mcpServers`
- Each server exposes focused, well-defined tools
- Run via stdio in CI; use Python virtual environment locally

**Observed Effectiveness:** High. All four MCP servers (audit-logger, security-scanner, dependency-scanner, git-rollback) operated reliably via stdio in CI. The security scanner caught real issues in generated Python code. The audit-logger's SHA-256 hash chain provided verifiable traceability. Note: avoid defining MCP servers in both agent configs and `mcp.json` — it produces duplicate warnings in CI logs.

---

### Pattern 4: Hook-Based Checkpoint Enforcement

**Description:** Use `preToolUse` hooks to enforce validation gates before critical operations (commits, merges, deployments).

**When to Use:** Any project requiring quality gates on AI-generated output.

**Implementation:**
- `preToolUse` hook on `git_commit` to verify all checkpoints passed
- `postToolUse` hook on `*` for universal audit logging
- `fileEdited` hooks for real-time security scanning on code changes

**Observed Effectiveness:** High in local testing. The `preToolUse` checkpoint-guard hook successfully blocked commits that skipped the review checkpoint. In CI, checkpoint enforcement is handled by the parallel `checkpoint-gates` pipeline stage (java-tests, python-tests, security-scan, review) which blocks the `finalize` stage if any gate fails.

---

### Pattern 5: Tamper-Evident Audit Logging

**Description:** Append-only NDJSON with SHA-256 hash chains provides verifiable audit trails for all AI actions.

**When to Use:** Any environment requiring traceability and compliance for AI-generated changes.

**Implementation:**
- NDJSON format for simple append and query
- SHA-256 hash chain linking each record to its predecessor
- Structured record types: `interaction`, `checkpoint`, `event`
- Log `workflow_start`, `inception_complete`, `construction_start`, `code-generation`, `security-scan`, `workflow_end` events at minimum

**Observed Effectiveness:** High. The audit-logger MCP produced complete, queryable audit trails on every pipeline run. The hash chain provides tamper evidence. The NDJSON format is simple to parse and append without risk of overwriting existing records.

---

### Pattern 6: Two-Repository Architecture

**Description:** Separate the AI orchestration configuration (skills, steering, hooks, MCP servers, pipeline) from the application code that the AI modifies.

**When to Use:** Any autonomous AI development system that modifies application code in CI.

**Implementation:**
- Orchestration repo: skills, steering, hooks, agent configs, MCP servers, CI pipeline
- Sandbox repo: application services that receive AI-generated code
- CI pipeline clones the sandbox repo, runs kiro-cli inside it, then pushes the branch and creates an MR
- Always set working directory explicitly before running AI tools

**Observed Effectiveness:** High. The separation cleanly prevented AI-generated code from polluting the orchestration repo. It also enables the same orchestration repo to target multiple sandbox services (java-api, python-processor, node-gateway) via configuration.

---

### Pattern 7: Retry Wrapper for AI Tool Resilience

**Description:** Wrap kiro-cli invocations in a retry script with exponential backoff to handle transient failures in CI.

**When to Use:** Any CI pipeline running AI tools that may experience transient failures (network, rate limits, model timeouts).

**Implementation:**
- Shell script with configurable retry count (default: 3) and exponential backoff
- Log each attempt with timestamp and exit code
- Fail the pipeline only after all retries are exhausted

**Observed Effectiveness:** Medium-High. The retry wrapper improved pipeline reliability without masking real failures. Transient kiro-cli failures (network timeouts, model unavailability) recovered on retry in most cases.

---

## Rollout Guidance

### Phase 1: Pilot (1–2 Teams)
- Deploy sandbox environment with steering files and audit logging
- Start with WF1 (Requirement to Software) — lowest risk, highest visibility
- Use the two-repository architecture from day one — don't mix orchestration and application code
- Provision a dedicated CI service account for kiro-cli (not a personal token)
- Establish baseline metrics for comparison

### Phase 2: Expand Workflows (3–4 Teams)
- Add WF2 (Refactoring) and WF3 (Dependency Upgrades)
- Tune guardrail thresholds based on pilot feedback
- Train teams on skill authoring and steering file configuration
- Integrate Jira automation rules for trigger-based pipeline execution

### Phase 3: Organization-Wide
- Enable optional workflows (WF4, WF5) based on demand
- Integrate with existing CI/CD pipelines using the validated GitLab pipeline as a template
- Establish governance model for steering file management (who can modify security-rules.md, etc.)
- Replace personal kiro-cli tokens with org-managed service accounts

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

---

## Known Gaps for Production Readiness

1. kiro-cli is authenticated with a personal user account — a dedicated CI service account is required for stable, auditable CI execution.
2. MCP server configuration is duplicated between agent JSON files and `mcp.json` — consolidate to one source of truth to eliminate duplicate warnings.
3. Jira status transition names are not validated before use — add a pre-flight check that queries available transitions and fails fast with a clear error if the target status doesn't exist.
4. No alerting on pipeline failure — the `on-failure` stage transitions Jira to "AI Dev Failed" but does not notify the team via Slack or email.
5. Coverage thresholds are enforced per-workflow in steering files but not yet validated automatically in CI for all languages — Node.js coverage gate is not yet implemented.
