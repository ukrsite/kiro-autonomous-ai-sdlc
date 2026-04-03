# Lessons Learned

**Project:** Autonomous AI SDLC Prototype
**Version:** 2.0
**Last Updated:** 2026-04-02

---

## Overview

This document captures challenges, resolutions, and insights from the 3-week prototype. Each entry includes context, impact, resolution, and a takeaway for future adoption.

---

## Week 1–2: AgentCore Custom Engine

### Lesson 1: Custom Engines Create Maintenance Overhead

**Context:** Built a custom `AgentCore` Python workflow orchestrator (~5,000 lines) with YAML step definitions, `LLMBackend` protocol, Strands SDK adapter, custom `CostEstimator`, and `BudgetEnforcer`.

**Challenge:** Every new workflow required changes to the engine itself. LLM integration, tool registration, and CI execution all needed custom plumbing. The engine became a dependency that had to be maintained alongside the actual AI workflows.

**Impact:** Significant development time spent on infrastructure rather than workflow logic. Tight coupling between the engine and workflow definitions made iteration slow.

**Resolution:** Migrated entirely to Kiro-native primitives in Week 3. The custom engine was replaced with zero custom infrastructure — skills, steering files, hooks, and MCP servers cover every AgentCore capability.

**Takeaway:** Before building a custom AI orchestration engine, audit whether the target platform already provides the primitives you need. In this case, Kiro's skills, steering, hooks, and agent configs replaced ~5,000 lines of custom Python with declarative configuration files.

---

### Lesson 2: YAML Workflow Definitions Don't Scale Well

**Context:** AgentCore used YAML step definitions to describe workflow logic.

**Challenge:** Complex conditional logic, multi-phase workflows, and adaptive depth were awkward to express in YAML. Debugging failed steps required understanding both the YAML schema and the engine's execution model.

**Impact:** Workflow authoring was slow and error-prone. Non-engineers couldn't contribute workflow definitions.

**Resolution:** Kiro SKILL.md files use natural language with structured sections. The AI model interprets them directly, making workflow logic readable and maintainable without a custom schema.

**Takeaway:** For AI-driven workflows, natural language skill definitions (SKILL.md) are more maintainable than structured YAML schemas. The LLM is the interpreter — lean into that.

---

## Week 3: Kiro Native Migration + CI/CD Pipeline

### Lesson 3: CI Working Directory Is Critical for Multi-Repo Architectures

**Context:** The pipeline clones `kiro-sandbox` into a `sandbox/` subdirectory of the CI workspace, then runs `kiro-cli` to generate code.

**Challenge:** `kiro-cli` was writing files to the CI repo root instead of the sandbox repo. All generated code landed in the wrong repository.

**Impact:** Pipeline runs completed without error but produced no output in the sandbox repo. Took multiple pipeline runs to diagnose.

**Resolution:** Added explicit `cd sandbox/` before `kiro-cli` execution in the `execute-workflow` stage. All file writes now land in the correct repository.

**Takeaway:** In multi-repo CI architectures, always explicitly set the working directory before running AI tools. Never rely on implicit path assumptions. Document the expected working directory in the pipeline YAML as a comment.

---

### Lesson 4: MR Creation via GitLab API Requires Careful Payload Handling

**Context:** The `finalize` stage creates a merge request on `kiro-sandbox` via the GitLab REST API.

**Challenge:** Multiple issues compounded: `--form` flags produced empty `{}` responses, markdown in YAML block scalars caused parse errors, and HTTP 409 (existing MR) was unhandled causing pipeline failures on re-runs.

**Impact:** MR creation failed silently or caused pipeline failures on re-runs of the same issue.

**Resolution:** Switched MR description to JSON body via Python subprocess, moved description to `printf` + temp file to avoid YAML escaping issues, added 409 handler that fetches the existing MR URL instead of failing.

**Takeaway:** GitLab API MR creation is sensitive to payload format. Use JSON body (not form data) for descriptions containing markdown. Always handle 409 idempotently — re-runs of the same issue should succeed, not fail.

---

### Lesson 5: CI Runner Image Must Match All Target Languages

**Context:** The `checkpoint-gates` stage runs tests for Java, Python, and Node.js services.

**Challenge:** The initial CI runner image lacked JVM support. Java tests failed immediately with "no JVM found". Additionally, `$HOME` was undefined in the Dockerfile `ENV` directive, breaking kiro-cli path resolution.

**Impact:** Java checkpoint gate was non-functional for the first several pipeline runs.

**Resolution:** Added OpenJDK 21, Maven 3.9, and Node.js 20 LTS to `docker/kiro-ci/Dockerfile`. Replaced `$HOME` with literal `/root/.local/bin` in ENV.

**Takeaway:** Build the CI runner image to match every language in the sandbox from day one. Validate the image locally against each language's build tool before running it in CI. Avoid shell variable expansion in Dockerfile ENV directives.

---

### Lesson 6: kiro-cli Silent Mode Behavior in CI

**Context:** `kiro-cli` runs headless in CI via `--no-interactive`. The AI-DLC workflow supports `silent` and `debug` verbosity modes configured in `aidlc-docs/aidlc-state.md`.

**Challenge:** When `aidlc-state.md` doesn't exist (first run), the workflow defaults to `debug` mode per the rule file. However, kiro-cli in a non-TTY environment may suppress interactive output regardless of the configured mode, leading to confusion about whether the workflow is running correctly.

**Impact:** Operators monitoring CI logs see minimal output and cannot distinguish between silent mode and a stalled workflow.

**Resolution:** Explicitly set verbosity mode to `silent` in `aidlc-state.md` for CI runs. Added pipeline log markers at key stages (workflow start, INCEPTION complete, CONSTRUCTION start, MR created) to provide visibility without relying on kiro-cli output.

**Takeaway:** Don't rely on AI tool verbosity for CI observability. Add explicit pipeline-level log markers at stage boundaries. Configure verbosity mode explicitly rather than relying on defaults.

---

### Lesson 7: Token Authentication Requires Robust Fallback Logic

**Context:** The `execute-workflow` stage clones `kiro-sandbox` using `oauth2:${GL_TOKEN}` authentication.

**Challenge:** The original clone script used `eval echo` to iterate token candidates, which silently failed in certain shell environments, leaving the clone unauthenticated.

**Impact:** Clone failures were non-obvious — the script appeared to succeed but the repo was not cloned.

**Resolution:** Replaced with direct `for TOKEN_VAL in "${GL_TOKEN:-}"...` iteration. Added explicit clone verification (check for `.git` directory) before proceeding.

**Takeaway:** Shell credential handling is fragile. Use explicit variable expansion, not `eval`. Always verify the result of authentication-dependent operations before proceeding.

---

### Lesson 8: Jira Workflow Status Names Must Be Exact

**Context:** The `finalize` stage transitions the Jira issue to "In Review" via the Jira REST API.

**Challenge:** The Jira project's workflow did not have a status named exactly "In Review", so the transition lookup returned no results and the transition was silently skipped.

**Impact:** Issues remained in "Ready for AI Dev" status after pipeline completion, breaking the feedback loop for the product owner.

**Resolution:** Treated as low-severity open issue. Workaround: add a comment to the Jira issue with the MR link regardless of transition success.

**Takeaway:** Never assume Jira status names. Query the available transitions via the API before attempting a transition. Make status transitions non-blocking — a failed transition should not fail the pipeline.

---

## Cross-Cutting Insights

### AI Behavior Patterns
- kiro-cli in headless mode (`--no-interactive`) produces consistent, structured output when given well-defined skill files with explicit checkpoints and expected outputs.
- The AI-DLC INCEPTION phase reliably produces requirements documents and handoff artifacts when the workspace contains sufficient context (existing code, steering files, rule details).
- Verbosity mode significantly affects CI log readability. Silent mode is appropriate for CI; debug mode is valuable during development and troubleshooting.
- The AI correctly respects steering file constraints (sandbox boundaries, security rules) without requiring enforcement in the workflow skill itself.

### Guardrails Effectiveness
- Always-on steering files (`security-rules.md`, `coding-standards.md`, `sandbox-boundaries.md`) provided consistent enforcement without any workflow-specific configuration.
- Language-specific steering files (`java-guardrails.md`, `python-guardrails.md`, `nodejs-guardrails.md`) correctly scoped rules to relevant file types via `fileMatch` globs.
- The `preToolUse` checkpoint-guard hook successfully blocked commits that skipped the review checkpoint in local testing.
- Security scanner MCP (`bandit` + `safety`) caught real issues in generated Python code during prototype runs.

### Workflow Reliability
- WF1 (Requirement to Software) was the most exercised and most reliable workflow. End-to-end runs consistently produced controller, service, model, and test files.
- The two-repository architecture (orchestration repo + sandbox repo) cleanly separated concerns and prevented AI-generated code from polluting the orchestration repo.
- The retry wrapper (`scripts/retry-wrapper.sh` with 3-retry exponential backoff) improved kiro-cli resilience in CI without masking real failures.
- MCP servers (audit-logger, security-scanner, dependency-scanner, git-rollback) operated reliably via stdio transport in CI.

### Team Productivity
- Migrating from AgentCore to Kiro-native primitives reduced the custom codebase from ~5,000 lines to near-zero, dramatically lowering the maintenance burden.
- Steering files as guardrails meant security and coding standards could be updated by editing a markdown file — no code changes, no deployments.
- The Jira → GitLab → kiro-cli → MR pipeline reduced the manual steps for a developer from "write code, write tests, write docs, create MR" to "create a Jira ticket and transition it".

---

## What Worked Well
1. Kiro-native primitives (skills, steering, hooks, MCP servers) replaced the entire custom AgentCore engine with zero custom infrastructure.
2. Always-on steering files enforced security and coding standards consistently across all workflows without per-workflow configuration.
3. The two-repository architecture cleanly separated orchestration from application code, making the sandbox safe to modify autonomously.
4. The AI-DLC INCEPTION + CONSTRUCTION phases produced structured, traceable artifacts (requirements, handoff, code gen plan, audit trail) on every run.
5. SHA-256 hash-chained audit logging provided tamper-evident traceability for all AI actions.

## What Didn't Work
1. kiro-cli working directory assumptions in CI caused silent failures that were difficult to diagnose.
2. GitLab API MR creation was brittle with form-encoded payloads containing markdown — required switching to JSON.
3. Jira status transition names were not validated upfront, causing silent failures in the feedback loop.
4. kiro-cli is authenticated with a personal user account in CI — not suitable for production; a service account is needed.
5. MCP server duplicate warnings in CI (agent config and mcp.json both define servers) added noise to logs without causing failures.

## What We'd Do Differently
1. Validate CI runner image against all target languages before the first pipeline run — don't discover missing JVM in CI.
2. Query Jira available transitions via API before attempting status changes, and make all Jira API calls non-blocking.
3. Set verbosity mode explicitly in `aidlc-state.md` as part of CI setup, rather than relying on defaults.
4. Provision a dedicated CI service account for kiro-cli from the start — personal tokens expire and are not auditable as CI identities.
5. Add explicit working directory verification steps in the pipeline before running AI tools in multi-repo architectures.
