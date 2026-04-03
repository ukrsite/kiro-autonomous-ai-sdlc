# Implementation Plan: Autonomous AI SDLC Prototype (Kiro-Native)

## Overview

This plan implements the autonomous AI-driven SDLC prototype using Kiro-native patterns. Instead of building a custom Python workflow engine, the implementation focuses on: steering files (guardrails), skills (one per E2E workflow), hooks (triggers), 4 lightweight MCP servers (audit-logger, security-scanner, dependency-scanner, git-rollback), agent config updates, a multi-language sample application, and property-based tests. Python is used for MCP servers and test infrastructure. Java, Node JS, and Python are used for the sample application modules. Property-based tests use Hypothesis (Python), jqwik (Java), and fast-check (Node JS).

## Tasks

- [x] 1. Steering files for guardrails
  - [x] 1.1 Create always-on security rules steering file
    - Create `.kiro/steering/security-rules.md` with `inclusion: always` front-matter
    - Define rules: no hardcoded secrets, no production access, input validation, dependency security, SQL injection prevention
    - Include pre-merge security scan requirement using security-scanner MCP
    - _Requirements: 4.2, 4.3, 4.7_

  - [x] 1.2 Create always-on coding standards steering file
    - Create `.kiro/steering/coding-standards.md` with `inclusion: always` front-matter
    - Define rules: code review requirements, test coverage thresholds, documentation standards
    - _Requirements: 4.1, 4.2, 4.4_

  - [x] 1.3 Create always-on sandbox boundaries steering file
    - Create `.kiro/steering/sandbox-boundaries.md` with `inclusion: always` front-matter
    - Define absolute restrictions: no production URLs, no production credentials, no production databases, no sensitive data
    - Define allowed resources: sandbox Git repos, local filesystem, configured MCP servers
    - _Requirements: 1.2, 4.7, 7.6_

  - [x] 1.4 Create language-specific guardrail steering files
    - Create `.kiro/steering/java-guardrails.md` with `inclusion: fileMatch`, `globs: ["**/*.java"]`
    - Create `.kiro/steering/nodejs-guardrails.md` with `inclusion: fileMatch`, `globs: ["**/*.js", "**/*.ts"]`
    - Create `.kiro/steering/python-guardrails.md` with `inclusion: fileMatch`, `globs: ["**/*.py"]`
    - Each file defines language-specific coding standards, linting rules, and security patterns
    - _Requirements: 4.1, 4.6_

  - [x] 1.5 Create manual-inclusion checkpoint and merge policy steering files
    - Create `.kiro/steering/checkpoint-enforcement.md` with `inclusion: manual`
    - Define checkpoint pipeline: code review → security scan → test coverage → merge
    - Create `.kiro/steering/merge-policy.md` with `inclusion: manual`
    - Define merge rules: all checkpoints must pass, audit log entry required
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

- [x] 2. MCP Server: Audit Logger
  - [x] 2.1 Scaffold audit-logger MCP server project
    - Create `mcp-servers/audit-logger/` directory
    - Create `mcp-servers/audit-logger/server.py` with MCP server skeleton using `mcp` Python SDK
    - Create `mcp-servers/audit-logger/requirements.txt` with dependencies
    - Define tool schemas: `log_interaction`, `log_checkpoint`, `log_event`, `query_audit`
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 2.2 Implement NDJSON storage with SHA-256 hash chain
    - Implement append-only NDJSON file writes in `server.py`
    - Implement SHA-256 content hashing per record using `hashlib`
    - Implement hash chain: each record's `previous_hash` = prior record's `content_hash`
    - Implement `log_interaction`, `log_checkpoint`, `log_event` tool handlers
    - Ensure records are queryable within 5 seconds of creation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 2.3 Implement audit query and filtering tool
    - Implement `query_audit` tool handler
    - Support filtering by `workflow_type`, `date_from`/`date_to`, `initiator`, `outcome`, `type`
    - Ensure filter returns exactly matching records (no more, no fewer)
    - _Requirements: 5.6_

  - [ ]* 2.4 Write property test: Audit Record Completeness and Tamper Evidence (Property 4)
    - **Property 4: Audit Record Completeness and Tamper Evidence**
    - Use Hypothesis to generate random audit records; assert each has non-empty `initiator`, valid ISO 8601 `timestamp`, `content_hash` == SHA-256 of payload; interaction records have non-empty `input_prompt` and `ai_output`; checkpoint records have `passed` and `validation_details`; `previous_hash` == prior record's `content_hash`
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 4: Audit Record Completeness and Tamper Evidence`
    - Minimum 100 iterations
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

  - [ ]* 2.5 Write property test: Audit Query Filter Correctness (Property 6)
    - **Property 6: Audit Query Filter Correctness**
    - Use Hypothesis to generate random sets of audit records and random filters; assert `query_audit` returns exactly those records matching all filter criteria
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 6: Audit Query Filter Correctness`
    - Minimum 100 iterations
    - **Validates: Requirements 5.6**

- [x] 3. MCP Server: Security Scanner
  - [x] 3.1 Scaffold security-scanner MCP server
    - Create `mcp-servers/security-scanner/` directory
    - Create `mcp-servers/security-scanner/server.py` with MCP server skeleton
    - Create `mcp-servers/security-scanner/requirements.txt`
    - Define tool schemas: `scan_code`, `scan_dependencies`, `get_scan_report`
    - _Requirements: 4.3, 8.6_

  - [x] 3.2 Implement security scanning tools
    - Implement `scan_code` tool: wraps `bandit` (Python), `npm audit` (Node), SpotBugs (Java)
    - Implement `scan_dependencies` tool: wraps `safety` (Python), `npm audit` (Node), OWASP dependency-check (Java)
    - Implement `get_scan_report` tool: retrieves detailed scan results by scan ID
    - Return structured results with severity levels (HIGH, CRITICAL, MEDIUM, LOW)
    - _Requirements: 4.3, 7.2, 8.6_

- [x] 4. MCP Server: Dependency Scanner
  - [x] 4.1 Scaffold dependency-scanner MCP server
    - Create `mcp-servers/dependency-scanner/` directory
    - Create `mcp-servers/dependency-scanner/server.py` with MCP server skeleton
    - Create `mcp-servers/dependency-scanner/requirements.txt`
    - Define tool schemas: `scan_outdated`, `check_compatibility`, `get_upgrade_plan`
    - _Requirements: 10.1, 10.2_

  - [x] 4.2 Implement dependency scanning tools
    - Implement `scan_outdated` tool: wraps `pip-audit`/`pip list --outdated` (Python), `npm outdated` (Node), `mvn versions:display-dependency-updates` (Java)
    - Implement `check_compatibility` tool: checks breaking changes between dependency versions
    - Implement `get_upgrade_plan` tool: generates ordered upgrade plan considering dependency graph
    - _Requirements: 10.1, 10.2, 10.3_

  - [ ]* 4.3 Write property test: Dependency Upgrade Detection (Property 14)
    - **Property 14: Dependency Upgrade Detection**
    - Use Hypothesis to generate random dependency lists with known outdated versions; assert `scan_outdated` identifies all outdated deps; assert `check_compatibility` runs for each; assert code updates generated for breaking changes
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 14: Dependency Upgrade Detection`
    - Minimum 100 iterations
    - **Validates: Requirements 10.1, 10.2, 10.3**

- [x] 5. MCP Server: Git Rollback
  - [x] 5.1 Scaffold git-rollback MCP server
    - Create `mcp-servers/git-rollback/` directory
    - Create `mcp-servers/git-rollback/server.py` with MCP server skeleton
    - Create `mcp-servers/git-rollback/requirements.txt` with `gitpython` dependency
    - Define tool schemas: `create_restore_point`, `rollback`, `verify_consistency`, `list_restore_points`
    - _Requirements: 15.1, 15.2_

  - [x] 5.2 Implement git rollback tools
    - Implement `create_restore_point`: tag current commit, snapshot lockfiles (pom.xml, package-lock.json, requirements.txt)
    - Implement `rollback`: git revert to restore point, restore lockfiles, log to audit-logger MCP
    - Implement `verify_consistency`: run test suite after rollback, report pass/fail counts
    - Implement `list_restore_points`: list available tagged restore points
    - Use `gitpython` for all Git operations
    - _Requirements: 15.1, 15.2, 15.3, 15.4_

  - [ ]* 5.3 Write property test: Rollback Round-Trip (Property 16)
    - **Property 16: Rollback Round-Trip**
    - Use Hypothesis to generate random file changes; create restore point, apply changes, rollback; assert Git repo restored to exact restore point state; assert test suite passes after rollback
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 16: Rollback Round-Trip`
    - Minimum 100 iterations
    - **Validates: Requirements 10.5, 15.1, 15.2, 15.4**

- [x] 6. Checkpoint — Ensure all MCP server tests pass
  - Run `pytest tests/ -v` to ensure all MCP server unit and property tests pass. Ask the user if questions arise.

- [x] 7. Configure hooks for triggers
  - [x] 7.1 Create file-based trigger hooks
    - Create `.kiro/hooks/on-code-change.json` with `fileEdited` trigger for `**/*.py`, `**/*.java`, `**/*.js`, `**/*.ts` — action: `askAgent` to run security scan via security-scanner MCP
    - Create `.kiro/hooks/on-new-file.json` with `fileCreated` trigger — action: `askAgent` to run lint and log to audit
    - _Requirements: 6.3_

  - [x] 7.2 Create checkpoint guard hooks
    - Create `.kiro/hooks/checkpoint-guard.json` with `preToolUse` trigger on `git_commit` — action: `askAgent` to verify all checkpoints passed before allowing commit
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

  - [x] 7.3 Create audit logging hooks
    - Create `.kiro/hooks/audit-all-tools.json` with `postToolUse` trigger on `*` — action: `askAgent` to log tool invocation to audit-logger MCP
    - _Requirements: 2.4, 5.1_

  - [x] 7.4 Create manual workflow trigger hooks
    - Create `.kiro/hooks/manual-wf2-refactor.json` with `userTriggered` — action: `askAgent` (developer) to execute WF2 refactoring skill
    - Create `.kiro/hooks/manual-wf3-upgrade.json` with `userTriggered` — action: `askAgent` (developer) to execute WF3 dependency upgrade skill
    - Create `.kiro/hooks/manual-wf4-bugfix.json` with `userTriggered` — action: `askAgent` (developer) to execute WF4 bug fix skill
    - Create `.kiro/hooks/manual-wf5-docs.json` with `userTriggered` — action: `askAgent` (developer) to execute WF5 documentation skill
    - _Requirements: 6.1_

  - [x] 7.5 Create scheduled trigger wrapper script
    - Create `scripts/retry-wrapper.sh` — retry up to 3 times with exponential backoff
    - Create `scripts/cron-triggers.sh` — example crontab entries for nightly dependency scan, weekly documentation update
    - Document cron setup for scheduled triggers using `kiro-cli chat --no-interactive`
    - _Requirements: 6.2, 6.6_

  - [ ]* 7.6 Write property test: Trigger Retry with Exponential Backoff (Property 11)
    - **Property 11: Trigger Retry with Exponential Backoff**
    - Use Hypothesis to generate random failure scenarios; assert retry wrapper retries up to 3 times with exponential backoff; assert failure logged after each attempt; assert marked failed after 3 retries
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 11: Trigger Retry with Exponential Backoff`
    - Minimum 100 iterations
    - **Validates: Requirements 6.6**

- [x] 8. Create skills for each workflow
  - [x] 8.1 Create WF1 skill: Requirement to Working Software
    - Create `skills/developer-skills/wf1-requirement-to-software/SKILL.md` with workflow steps: parse requirement → create Kiro spec → implement tasks → code review checkpoint → test coverage checkpoint → security scan checkpoint → merge → audit log
    - Create `skills/developer-skills/wf1-requirement-to-software/references/checkpoint-criteria.md` with checkpoint pass/fail criteria
    - Create `skills/developer-skills/wf1-requirement-to-software/references/output-format.md` with expected output artifact format
    - Note: WF1 leverages Kiro's built-in spec workflow (requirements → design → tasks)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9_

  - [x] 8.2 Create WF2 skill: Autonomous Refactoring
    - Create `skills/developer-skills/wf2-autonomous-refactoring/SKILL.md` with workflow steps: analyze legacy code → create restore point → apply refactoring → run existing tests → behavior equivalence check → performance benchmark → security scan → generate delta report → audit log
    - Create `skills/developer-skills/wf2-autonomous-refactoring/references/refactoring-patterns.md`
    - Create `skills/developer-skills/wf2-autonomous-refactoring/references/behavior-equivalence.md`
    - Create `skills/developer-skills/wf2-autonomous-refactoring/scripts/run_benchmarks.py`
    - Create `skills/developer-skills/wf2-autonomous-refactoring/scripts/compare_behavior.py`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

  - [x] 8.3 Create WF3 skill: Dependency Upgrades
    - Create `skills/developer-skills/wf3-dependency-upgrades/SKILL.md` with workflow steps: create restore point → scan outdated deps → check compatibility → generate code updates → run full test suite → generate delta report → audit log
    - Create `skills/developer-skills/wf3-dependency-upgrades/references/upgrade-strategy.md`
    - Create `skills/developer-skills/wf3-dependency-upgrades/references/compatibility-checks.md`
    - Create `skills/developer-skills/wf3-dependency-upgrades/scripts/generate_delta_report.py`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_

  - [x] 8.4 Create WF4 skill: Bug Fix (Optional)
    - Create `skills/developer-skills/wf4-bug-fix/SKILL.md` with workflow steps: root cause analysis → generate fix → generate regression tests → side-effect analysis → fix validation checkpoint → audit log
    - Create `skills/developer-skills/wf4-bug-fix/references/root-cause-analysis.md`
    - Create `skills/developer-skills/wf4-bug-fix/scripts/validate_fix.py`
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [x] 8.5 Create WF5 skill: Documentation (Optional)
    - Create `skills/developer-skills/wf5-documentation/SKILL.md` with workflow steps: analyze codebase → generate API docs → generate architecture diagrams → generate onboarding guides → accuracy validation checkpoint → completeness review checkpoint → generate delta report → audit log
    - Create `skills/developer-skills/wf5-documentation/references/doc-standards.md`
    - Create `skills/developer-skills/wf5-documentation/references/completeness-criteria.md`
    - Create `skills/developer-skills/wf5-documentation/scripts/validate_docs.py`
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_

  - [x] 8.6 Create shared delta report generator skill
    - Create `skills/shared-skills/delta-report-generator/SKILL.md` with instructions for generating delta reports
    - Create `skills/shared-skills/delta-report-generator/scripts/generate_delta_report.py` — compares git snapshots, calculates metrics (files modified, lines added/removed, test counts, coverage)
    - _Requirements: 9.5, 10.6, 12.4_

- [x] 9. Update agent configurations
  - [x] 9.1 Update developer agent config
    - Update `agents/developer.json` to add MCP servers: audit-logger, security-scanner, dependency-scanner, git-rollback
    - Update `resources` to include `skill://skills/developer-skills/*/SKILL.md`
    - Ensure all workflow skills are accessible
    - _Requirements: 2.1, 2.3_

  - [x] 9.2 Update devops agent config
    - Update `agents/devops.json` to add MCP servers: audit-logger, security-scanner, git-rollback
    - Update `resources` to include devops-specific skills
    - _Requirements: 2.3_

  - [-]* 9.3 Update solution-architect and product-owner agent configs
    - Update `agents/solution-architect.json` to add audit-logger MCP server
    - Update `agents/product-owner.json` to add audit-logger MCP server
    - _Requirements: 2.3_

  - [ ]* 9.4 Write property test: Workflow Routing Correctness (Property 2)
    - **Property 2: Workflow Routing Correctness**
    - Use Hypothesis to generate random valid workflow IDs and agent roles; assert system routes to correct skill and agent matches requested role based on agent JSON config
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 2: Workflow Routing Correctness`
    - Minimum 100 iterations
    - **Validates: Requirements 2.2, 2.3**

- [x] 10. Checkpoint — Ensure all tests pass
  - Run `pytest tests/ -v` to ensure all tests pass. Ask the user if questions arise.

- [x] 11. Sample application creation
  - [x] 11.1 Create Java module with Maven project
    - Create `sample-app/java-module/` with `pom.xml`, `src/main/java/`, `src/test/java/`
    - Implement a simple REST service or utility library
    - Include baseline unit tests (JUnit 5)
    - Include at least one outdated dependency in `pom.xml` for WF3
    - Include a `legacy/` package with code exhibiting technical debt (long methods, poor naming, code duplication) for WF2
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 11.2 Create Node JS module
    - Create `sample-app/nodejs-module/` with `package.json`, `src/`, `test/`
    - Implement a simple Express API or utility library
    - Include baseline unit tests (Jest)
    - Include at least one outdated dependency in `package.json` for WF3
    - Include a `legacy/` directory with technical debt code for WF2
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 11.3 Create Python module
    - Create `sample-app/python-module/` with `requirements.txt`, `src/`, `tests/`
    - Implement a simple Flask API or utility library
    - Include baseline unit tests (pytest)
    - Include at least one outdated dependency in `requirements.txt` for WF3
    - Include a `legacy/` directory with technical debt code for WF2
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 11.4 Initialize Git repository for sample application
    - Initialize `sample-app/` as a Git repository
    - Create initial commit with all modules
    - Set up `.gitignore` for Java, Node JS, and Python artifacts
    - _Requirements: 3.5_

- [ ] 12. Guardrail configuration and validation property tests
  - [ ]* 12.1 Write property test: Guardrail Configuration Round-Trip (Property 7)
    - **Property 7: Guardrail Configuration Round-Trip**
    - Use Hypothesis to generate random steering file content with rules; write to file, load via parser, inspect active rules; assert same set of rules. Modify file and reload; assert changes reflected.
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 7: Guardrail Configuration Round-Trip`
    - Minimum 100 iterations
    - **Validates: Requirements 4.1, 4.6**

  - [ ]* 12.2 Write property test: Checkpoint Enforcement Before Merge (Property 8)
    - **Property 8: Checkpoint Enforcement Before Merge**
    - Use Hypothesis to generate random workflow executions with varying checkpoint results; assert merge only occurs when ALL required checkpoints pass; assert merge blocked when any checkpoint fails or is missing
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 8: Checkpoint Enforcement Before Merge`
    - Minimum 100 iterations
    - **Validates: Requirements 4.2, 4.3, 4.4, 8.4, 8.5, 8.6**

  - [ ]* 12.3 Write property test: Checkpoint Failure Halts Workflow (Property 9)
    - **Property 9: Checkpoint Failure Halts Workflow**
    - Use Hypothesis to generate random checkpoint failures; assert workflow halts, merge does not occur, failure details logged via audit-logger MCP
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 9: Checkpoint Failure Halts Workflow`
    - Minimum 100 iterations
    - **Validates: Requirements 4.5, 8.8, 9.6, 10.7, 11.5**

  - [ ]* 12.4 Write property test: Sandbox Access Control Enforcement (Property 1)
    - **Property 1: Sandbox Access Control Enforcement**
    - Use Hypothesis to generate random resource paths (some production, some sandbox); assert production resources denied, sandbox resources allowed; assert auth checked before access
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 1: Sandbox Access Control Enforcement`
    - Minimum 100 iterations
    - **Validates: Requirements 1.2, 1.5, 4.7**

- [ ] 13. Workflow-specific property tests
  - [ ]* 13.1 Write property test: Refactoring Behavior Preservation (Property 13)
    - **Property 13: Refactoring Behavior Preservation**
    - Use Hypothesis to generate random test suites and refactoring scenarios; assert all pre-existing tests pass after refactoring; if any fail, assert refactoring rejected and differences reported
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 13: Refactoring Behavior Preservation`
    - Minimum 100 iterations
    - **Validates: Requirements 9.2, 9.3**

  - [ ]* 13.2 Write property test: Workflow Output Artifact Completeness (Property 15)
    - **Property 15: Workflow Output Artifact Completeness**
    - Use Hypothesis to generate random workflow executions for each workflow type; assert output contains all required artifact types per workflow (WF1: code+tests+docs, WF2: refactored code+benchmarks+delta, WF4: fix+regression tests+side-effect, WF5: API docs+diagrams+guides+delta)
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 15: Workflow Output Artifact Completeness`
    - Minimum 100 iterations
    - **Validates: Requirements 8.2, 8.3, 9.4, 9.5, 11.2, 11.3, 11.4, 12.1, 12.2, 12.3, 12.4**

  - [ ]* 13.3 Write property test: Documentation Checkpoint Enforcement (Property 17)
    - **Property 17: Documentation Checkpoint Enforcement**
    - Use Hypothesis to generate random documentation workflow executions; assert accuracy validation and completeness review checkpoints both executed and passed before finalization
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 17: Documentation Checkpoint Enforcement`
    - Minimum 100 iterations
    - **Validates: Requirements 12.5, 12.6**

- [ ] 14. Integration property tests
  - [ ]* 14.1 Write property test: Universal Audit Logging (Property 5)
    - **Property 5: Universal Audit Logging**
    - Use Hypothesis to generate random system actions (interactions, checkpoints, triggers, pipeline events, rollbacks); assert audit-logger MCP contains corresponding record with timestamp within action's execution window
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 5: Universal Audit Logging`
    - Minimum 100 iterations
    - **Validates: Requirements 2.4, 4.5, 6.5, 7.5, 8.9, 9.7, 10.8, 11.6, 12.7, 15.3**

  - [ ]* 14.2 Write property test: Trigger Routing and Parameter Passing (Property 10)
    - **Property 10: Trigger Routing and Parameter Passing**
    - Use Hypothesis to generate random trigger configurations (manual, scheduled, event-based); assert correct workflow initiated with all configured parameters
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 10: Trigger Routing and Parameter Passing`
    - Minimum 100 iterations
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

  - [ ]* 14.3 Write property test: Headless Mode Structured Output (Property 3)
    - **Property 3: Headless Mode Structured Output**
    - Use Hypothesis to generate random valid workflow parameters; assert headless mode output is parseable structured text; assert exit code matches workflow outcome
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 3: Headless Mode Structured Output`
    - Minimum 100 iterations
    - **Validates: Requirements 2.6, 2.7, 2.8**

  - [ ]* 14.4 Write property test: Pipeline Stage Enforcement (Property 12)
    - **Property 12: Pipeline Stage Enforcement**
    - Use Hypothesis to generate random pipeline executions with varying stage outcomes; assert stages execute in order; assert failed stage prevents subsequent stages; assert team notified on failure
    - Tag: `Feature: autonomous-ai-sdlc-prototype, Property 12: Pipeline Stage Enforcement`
    - Minimum 100 iterations
    - **Validates: Requirements 7.1, 7.2, 7.3**

- [x] 15. Checkpoint — Ensure all tests pass
  - Run `pytest tests/ -v` to ensure all property and unit tests pass. Ask the user if questions arise.

- [x] 16. CI/CD pipeline configuration
  - [x] 16.1 Create .gitlab-ci.yml pipeline
    - Create `.gitlab-ci.yml` with stages: lint, test, security, deploy
    - Lint stage: `ruff check mcp-servers/`, `mypy mcp-servers/`
    - Test stage: `pytest tests/`, `cd sample-app/java-module && mvn test`, `cd sample-app/nodejs-module && npm test`, `cd sample-app/python-module && pytest`
    - Security stage: `bandit -r mcp-servers/`, `safety check`
    - Deploy stage: deploy to sandbox (main branch only)
    - Configure notifications on failure
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.6_

  - [x] 16.2 Create sandbox environment provisioning scripts
    - Create `scripts/setup-sandbox.sh` — install Python 3.11+, Java, Node JS, Git
    - Create `scripts/install-mcp-servers.sh` — install MCP server dependencies
    - Create `scripts/setup-kiro.sh` — install Kiro CLI, configure agents, verify setup
    - Ensure no access to production systems or credentials
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6_

- [x] 17. Weekly reporting and documentation templates
  - [x] 17.1 Create weekly report template and storage
    - Create `reports/` directory in project repository
    - Create `reports/weekly-report-template.md` with sections: accomplishments, demonstrations, challenges/resolutions, next-week plan, risks/blockers
    - _Requirements: 13.1, 13.4_

  - [x] 17.2 Create consolidation document templates
    - Create `docs/` directory for final documentation package
    - Create templates for: workflow descriptions, guardrail configurations, audit log samples, architecture documentation, lessons learned, recommendations, comparative analysis
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [x] 18. Final checkpoint — Ensure all tests pass
  - Run `pytest tests/ -v` and verify all sample app tests pass (`mvn test`, `npm test`, `pytest`). Ask the user if questions arise.

## Notes

- Tasks marked with `*` are property-based test tasks (optional for faster MVP)
- Each task references specific requirements for traceability
- Checkpoints at tasks 6, 10, 15, and 18 ensure incremental validation
- Property-based tests (17 total) validate universal correctness properties using Hypothesis (Python primary), jqwik (Java sample module), and fast-check (Node JS sample module)
- Custom code is limited to 4 MCP servers + sample app + test infrastructure + scripts
- No custom Python CLI, workflow engine, trigger engine, or guardrails framework needed
- Key Kiro-native patterns used: Skills (workflows), Steering files (guardrails), Hooks (triggers), Agent configs (routing), MCP servers (infrastructure)
- Key Python libraries for MCP servers: `mcp` (MCP SDK), `hashlib` (SHA-256), `gitpython` (Git ops), `hypothesis` (PBT), `pytest` (testing)
