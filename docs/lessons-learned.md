# Lessons Learned

**Project:** Autonomous AI SDLC Prototype
**Version:** 4.0
**Last Updated:** 2026-04-09

---

## Overview

This document captures challenges, resolutions, and insights from the prototype. Each entry includes context, impact, resolution, and a takeaway for future adoption.

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

**Resolution:** Switched MR description to JSON body via Python subprocess (`scripts/create_mr.py`), moved description to a temp file to avoid YAML escaping issues, added 409 handler that fetches the existing MR URL instead of failing.

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

**Resolution:** The `execute-workflow` stage now pre-creates `sandbox/aidlc-docs/aidlc-state.md` with `silent` verbosity before invoking kiro-cli. This ensures the workflow never defaults to debug mode in CI, regardless of whether a prior state file exists. Pipeline log markers at key stages provide visibility without relying on kiro-cli output.

**Takeaway:** Don't rely on AI tool verbosity for CI observability. Pre-create `aidlc-state.md` with explicit verbosity as part of CI setup. Add pipeline-level log markers at stage boundaries.

---

### Lesson 7: Token Authentication Requires Robust Fallback Logic

**Context:** The `execute-workflow` and `finalize` stages clone `kiro-sandbox` using token-based authentication.

**Challenge:** The original clone script used `eval echo` to iterate token candidates, which silently failed in certain shell environments, leaving the clone unauthenticated.

**Impact:** Clone failures were non-obvious — the script appeared to succeed but the repo was not cloned.

**Resolution:** Replaced with direct `for TOKEN_VAL in "${GL_TOKEN:-}" "${GITLAB_TOKEN:-}" "${CI_JOB_TOKEN:-}"` iteration. Added explicit clone verification (check for `.git` directory) before proceeding. The `.clone-sandbox` YAML anchor is reused across both `execute-workflow` and `finalize` to keep the logic consistent.

**Takeaway:** Shell credential handling is fragile. Use explicit variable expansion, not `eval`. Always verify the result of authentication-dependent operations before proceeding. Use YAML anchors to avoid duplicating clone logic across pipeline stages.

---

### Lesson 8: Jira Workflow Status Names Must Be Exact

**Context:** The `finalize` stage transitions the Jira issue to "In Review" via the Jira REST API.

**Challenge:** The Jira project's workflow did not have a status named exactly "In Review", so the transition lookup returned no results and the transition was silently skipped.

**Impact:** Issues remained in "Ready for AI Dev" status after pipeline completion, breaking the feedback loop for the product owner.

**Resolution:** Treated as low-severity open issue. Workaround: add a comment to the Jira issue with the MR link regardless of transition success. The `on-failure` job also queries available transitions dynamically rather than hardcoding a status name.

**Takeaway:** Never assume Jira status names. Query the available transitions via the API before attempting a transition. Make status transitions non-blocking — a failed transition should not fail the pipeline.

---

### Lesson 9: Cost Visibility Requires Explicit Instrumentation

**Context:** Added the `finops-cost-estimator` MCP server to track LLM token usage, compute time, MCP tool calls, and checkpoint executions per workflow run.

**Challenge:** Without explicit cost tracking, there was no visibility into which workflows were expensive, whether estimates matched actuals, or how costs trended over time. Token counts had to be estimated from prompt/output character counts when the audit records lacked explicit token fields.

**Impact:** Cost overruns were invisible. Teams had no data to justify or optimize AI workflow usage.

**Resolution:** The `finops-cost-estimator` reads the audit log after `workflow_end` to compute actuals, compares against pre-run estimates, and writes reports to `reports/finops/`. The `finops-cost-reporting.md` steering file ensures the agent always surfaces the cost table in its final response. The server is deployed to ECR via a dedicated `deploy:finops-mcp-server` CI job on every merge to main.

**Takeaway:** Instrument cost from day one. The audit log already captures the data needed — compute time from `workflow_start`/`workflow_end` timestamps, tool calls from `tool_invocation` events, checkpoints from checkpoint records. A lightweight post-run calculator on top of the existing audit log is sufficient. Deploy the MCP server image via CI to keep it current.

---

### Lesson 10: MCP Server Setup Script Must Stay in Sync with Server List

**Context:** `scripts/setup-kiro.sh` verifies MCP server files and generates `mcp.json` for both CI (stdio) and local (Docker) environments.

**Challenge:** When `finops-cost-estimator` was added as the fifth MCP server, the `MCP_SERVERS` array in `setup-kiro.sh` was not updated. Step 3 silently skipped verification of the new server, and neither the CI nor local `mcp.json` configs included it — meaning the agent had no cost reporting capability in either environment.

**Impact:** The finops server was deployed but not wired up. Cost reporting was silently absent from all workflow runs until the omission was caught in review.

**Resolution:** Added `finops-cost-estimator` to the `MCP_SERVERS` array and to both the CI stdio and local Docker heredoc blocks in `setup-kiro.sh`. Also added `estimate_workflow_cost` to the `autoApprove` list in `mcp.json` (it was missing, requiring manual approval for pre-run estimates).

**Takeaway:** Treat `setup-kiro.sh` as the single source of truth for MCP server registration. When adding a new MCP server, update the verification array, the CI config block, and the local config block in the same commit. Add a CI lint step that cross-checks the server list against `mcp-servers/` directory contents.

---

## Cross-Cutting Insights

### AI Behavior Patterns
- kiro-cli in headless mode (`--no-interactive`) produces consistent, structured output when given well-defined skill files with explicit checkpoints and expected outputs.
- The AI-DLC INCEPTION phase reliably produces requirements documents and handoff artifacts when the workspace contains sufficient context (existing code, steering files, rule details).
- Verbosity mode significantly affects CI log readability. Silent mode is appropriate for CI; debug mode is valuable during development and troubleshooting.
- The AI correctly respects steering file constraints (sandbox boundaries, security rules) without requiring enforcement in the workflow skill itself.
- Pre-creating `aidlc-state.md` with `silent` verbosity before kiro-cli runs eliminates the debug-mode-on-first-run problem entirely.

### Guardrails Effectiveness
- Always-on steering files (`security-rules.md`, `coding-standards.md`, `sandbox-boundaries.md`, `finops-cost-reporting.md`) provided consistent enforcement without any workflow-specific configuration.
- Language-specific steering files (`java-guardrails.md`, `python-guardrails.md`, `nodejs-guardrails.md`) correctly scoped rules to relevant file types via `fileMatch` globs.
- The `preToolUse` checkpoint-guard hook successfully blocked commits that skipped the review checkpoint in local testing.
- Security scanner MCP (`bandit` + `safety`) caught real issues in generated Python code during prototype runs.

### Workflow Reliability
- WF1 (Requirement to Software) was the most exercised and most reliable workflow. End-to-end runs consistently produced controller, service, model, and test files.
- The two-repository architecture (orchestration repo + sandbox repo) cleanly separated concerns and prevented AI-generated code from polluting the orchestration repo.
- The retry wrapper (`scripts/retry-wrapper.sh` with 3-retry exponential backoff) improved kiro-cli resilience in CI without masking real failures.
- All five MCP servers (audit-logger, security-scanner, dependency-scanner, git-rollback, finops-cost-estimator) operated reliably via stdio transport in CI.
- The `finalize` stage re-clones the sandbox repo fresh (`.git` is excluded from artifacts to reduce size) and overlays the kiro-cli output before committing — this avoids git history corruption from artifact-based workflows.

### Team Productivity
- Migrating from AgentCore to Kiro-native primitives reduced the custom codebase from ~5,000 lines to near-zero, dramatically lowering the maintenance burden.
- Steering files as guardrails meant security and coding standards could be updated by editing a markdown file — no code changes, no deployments.
- The Jira → GitLab → kiro-cli → MR pipeline reduced the manual steps for a developer from "write code, write tests, write docs, create MR" to "create a Jira ticket and transition it".
- The `setup-kiro.sh` dual-mode config generation (CI stdio vs local Docker) eliminated manual `mcp.json` maintenance across environments.

---

## What Worked Well
1. Kiro-native primitives (skills, steering, hooks, MCP servers) replaced the entire custom AgentCore engine with zero custom infrastructure.
2. Always-on steering files enforced security and coding standards consistently across all workflows without per-workflow configuration.
3. The two-repository architecture cleanly separated orchestration from application code, making the sandbox safe to modify autonomously.
4. The AI-DLC INCEPTION + CONSTRUCTION phases produced structured, traceable artifacts (requirements, handoff, code gen plan, audit trail) on every run.
5. SHA-256 hash-chained audit logging provided tamper-evident traceability for all AI actions.
6. The `finops-cost-estimator` MCP server provided per-run cost breakdowns with zero workflow changes — it reads the existing audit log and the steering file handles surfacing the result.
7. `setup-kiro.sh` generating environment-specific `mcp.json` (CI stdio vs local Docker) eliminated a whole class of "works locally, fails in CI" MCP configuration bugs.

## What Didn't Work
1. kiro-cli working directory assumptions in CI caused silent failures that were difficult to diagnose.
2. GitLab API MR creation was brittle with form-encoded payloads containing markdown — required switching to JSON via `scripts/create_mr.py`.
3. Jira status transition names were not validated upfront, causing silent failures in the feedback loop.
4. kiro-cli is authenticated with a personal user account in CI — not suitable for production; a service account is needed.
5. MCP server configuration was duplicated between agent JSON files and `mcp.json`, adding noise to CI logs.
6. Adding a new MCP server without updating `setup-kiro.sh` caused silent omission from generated configs — the server was deployed but not wired up.

## What We'd Do Differently
1. Validate CI runner image against all target languages before the first pipeline run — don't discover missing JVM in CI.
2. Query Jira available transitions via API before attempting status changes, and make all Jira API calls non-blocking.
3. Pre-create `aidlc-state.md` with `silent` verbosity as part of CI setup from day one — don't rely on defaults.
4. Provision a dedicated CI service account for kiro-cli from the start — personal tokens expire and are not auditable as CI identities.
5. Add a CI lint step that cross-checks `setup-kiro.sh`'s `MCP_SERVERS` array against the actual `mcp-servers/` directory — catch omissions automatically.
6. Deploy all MCP server Docker images via CI on merge to main — don't rely on manual image builds.
7. Define MCP servers in one place from the start — duplicating between agent configs and `mcp.json` causes warnings and confusion about which config is authoritative.
8. Add Node.js checkpoint gate from day one — not just Java and Python. Missing language gates are silent coverage gaps.
9. Use compute-time-based token estimation as the default — text-length estimation from audit log summaries is unreliable (produces ~100 tokens for a 7-minute run).

---

## Week 4: CI Hardening + FinOps + Multi-Service (April 3-9)

### Lesson 11: Shell Metacharacters in Jira Descriptions Break CI

**Context:** Jira issue descriptions containing parentheses, asterisks, and `{code}` blocks were passed directly into shell commands in `.gitlab-ci-workflow.yml`.

**Challenge:** Shell metacharacters in the description caused parse errors and command failures in the `execute-workflow` stage.

**Impact:** Pipeline failures on any Jira issue with formatted descriptions — which is most real-world issues.

**Resolution:** Extracted the prompt builder to `scripts/build_kiro_prompt.py` and MR creation to `scripts/create_mr.py`. Both are standalone Python scripts called from clean YAML — no shell interpolation of user input.

**Takeaway:** Never embed user-provided text (Jira descriptions, issue summaries) directly in shell commands. Extract to standalone scripts that read from files or environment variables.

---

### Lesson 12: MCP Server Duplication Causes Silent Failures

**Context:** The 5 custom MCP servers were defined in both agent JSON configs (using `${workspaceFolder}` paths) and `.kiro/settings/mcp.json` (using resolved absolute paths from `setup-kiro.sh`).

**Challenge:** kiro-cli loaded both, producing duplicate warnings. Worse, the agent config versions used `${workspaceFolder}` which kiro-cli can't resolve — Docker got a literal string as the volume mount path, containers crashed on init, and all 5 servers showed "connection closed: initialize response".

**Impact:** All MCP servers failed to load in kiro-cli. Audit logging, security scanning, cost reporting — all unavailable.

**Resolution:** Removed the 5 custom servers from all agent configs. They're now defined exclusively in `mcp.json` (generated by `setup-kiro.sh` with resolved paths). Agent configs retain only Docker-only servers (confluence, gitlab, jira).

**Takeaway:** Define each MCP server in exactly one place. For servers that need environment-specific paths, use a config generator (`setup-kiro.sh`) as the single source of truth. Never use IDE-only variables (`${workspaceFolder}`) in configs that kiro-cli reads.

---

### Lesson 13: Multi-Service Runs Need Per-Service Test Isolation

**Context:** Added `all-services` mode to run WF1 across java-api, python-processor, and node-gateway in a single pipeline.

**Challenge:** The python-tests checkpoint gate ran `pytest` from `sandbox/services/` (the parent directory), measuring coverage across all Python files. Pre-existing untested endpoints in `main.py` dragged overall coverage to 46%, failing the 80% threshold — even though new code had 96% coverage.

**Impact:** Pipeline failed on coverage despite the new code being well-tested.

**Resolution:** Updated python-tests to detect multi-service mode and iterate per Python service directory. Each service runs its own `pytest --cov=src` independently, so coverage is measured per-service, not across the monorepo.

**Takeaway:** Multi-service CI gates must test each service in isolation. Running a single test command across all services conflates coverage metrics and produces false failures.

---

### Lesson 14: LLM Token Counts Are Not Available via MCP

**Context:** The `finops-cost-estimator` reads `input_tokens`/`output_tokens` from audit log `interaction` records to compute LLM costs.

**Challenge:** kiro-cli doesn't expose token usage to MCP servers. The `log_interaction` calls from the agent pass short summary text, not the full LLM conversation. Text-based estimation (`len(text) / 4`) produced ~133 tokens for a 7-minute run — clearly wrong.

**Impact:** LLM token costs showed near-zero in every cost report, making the FinOps data misleading.

**Resolution:** Three-tier approach: (1) Set `KIRO_LOG_LEVEL=trace` in CI and parse kiro-cli logs for actual token counts via `scripts/extract_token_usage.py`. (2) Compute-time estimation fallback: duration × 40 tok/s output × 2.5 input ratio. (3) The finops server always uses compute-time estimation when no explicit tokens are injected. A 7-minute run now shows ~34,000 input / ~13,600 output tokens ($0.30 LLM cost) instead of 133/122 ($0.002).

**Takeaway:** Don't rely on MCP interaction records for token counts — they contain summaries, not full conversations. Use the LLM platform's own logs or compute-time estimation as the primary source.

---

### Lesson 15: Rate Limits Require Longer Backoff Than Transient Errors

**Context:** kiro-cli hit the Kiro platform rate limit during a long WF1 run ("Request quota exceeded. Please wait a moment and try again.").

**Challenge:** The original retry wrapper (3 retries, 10s backoff) was designed for transient network errors. Rate limits persist longer — 10-20 seconds isn't enough.

**Impact:** The workflow failed after 3 retries, wasting the entire run.

**Resolution:** Updated `retry-wrapper.sh` to 5 retries with rate-limit detection. When output contains "rate limit", "quota exceeded", "429", or "throttle", a 60s minimum cooldown is applied before retry. Max backoff capped at 300s.

**Takeaway:** Differentiate between transient errors (short backoff) and rate limits (long cooldown). Grep the command output for rate-limit signals and apply a separate, longer delay.

---

### Lesson 16: Mandatory Doc Artifacts Need Explicit Enforcement

**Context:** WF1 step 9 listed 5 documentation artifacts (release notes, CHANGELOG, OpenAPI, architecture, summary) as bullet points with a "see other skill" reference.

**Challenge:** The agent only generated `CHANGELOG.md` and skipped the other 4 artifacts. The instruction wasn't explicit enough — bullet lists are treated as suggestions, not requirements.

**Impact:** Missing release notes, OpenAPI specs, and architecture diagrams on every run.

**Resolution:** Changed step 9 to use `- [ ]` checkbox items with "MANDATORY — do not skip any" language. Each artifact has an explicit file path and template reference. The CI prompt also says "MANDATORY: Generate ALL of these docs" and "Do NOT skip any artifact."

**Takeaway:** For AI agents, bullet lists are suggestions. Checkboxes with "MANDATORY" language are requirements. Be explicit about what must be produced — don't rely on "see other skill" references.
