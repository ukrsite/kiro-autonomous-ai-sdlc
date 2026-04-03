# Requirements Document

## Introduction

This document defines the requirements for integrating Jira issue tracking with the existing GitLab CI/CD pipeline and Kiro CLI to enable automated, event-driven execution of any configured workflow (WF1–WF5). When a Jira issue transitions to a designated status, a webhook triggers a GitLab pipeline that invokes Kiro CLI in headless mode, routing to the correct workflow based on the project mapping configuration. The pipeline produces workflow-specific output artifacts (code, tests, documentation, refactored modules, upgraded dependencies, bug fixes) and a merge request — all without manual developer intervention.

The integration connects three existing systems (Jira, GitLab CI, Kiro CLI) through a project mapping configuration, a webhook receiver pipeline stage, and a CI workflow driver. It leverages Kiro CLI's native MCP server integrations (jira, gitlab, audit-logger, security-scanner, dependency-scanner, git-rollback) to minimize custom scripting. Instead of a dedicated Python module per pipeline concern, the pipeline delegates Jira retrieval, MR creation, security scanning, and audit logging to `kiro-cli chat --no-interactive` with the developer agent's pre-configured MCP servers.

The simplified pipeline defines 4 stages: `validate`, `execute-workflow`, `checkpoint-gates`, and `finalize`. The `validate` stage performs webhook payload extraction, config lookup, and workflow identifier resolution using minimal shell. The `execute-workflow` stage invokes Kiro CLI to run the workflow specified in the project mapping configuration (WF1 through WF5), passing workflow-appropriate inputs derived from the Jira issue. The `checkpoint-gates` stage evaluates quality results using workflow-specific thresholds via Kiro CLI and its MCP tools. The `finalize` stage creates the branch and merge request, updates Jira status, and logs the audit trail — all via Kiro CLI MCP calls.

## Glossary

- **Jira_Webhook**: An HTTP POST request sent by Jira automation when an issue transitions to a configured status, containing the issue key and event metadata.
- **Webhook_Receiver**: The `validate` stage of the integration pipeline that accepts incoming Jira webhook trigger variables, validates them, and starts the pipeline run with the Jira issue key as a CI variable.
- **Project_Mapping_Configuration**: A YAML configuration file (`config/jira-project-mappings.yml`) that maps Jira project keys to Git repository paths, target branches, workflow identifiers, and default Kiro workflow parameters.
- **Pipeline_Driver**: The GitLab CI pipeline that orchestrates workflow execution across 4 stages, delegating most operations to Kiro CLI with its configured MCP servers.
- **Jira_Trigger_Status**: The Jira issue status (e.g., "Ready for AI Dev") that, when entered, fires the webhook to initiate the integration pipeline.
- **Kiro_CLI**: The AI-powered CLI interface used for workflow execution. Operates in headless mode via `kiro-cli chat --no-interactive`. The developer agent has pre-configured MCP servers for jira, gitlab, audit-logger, security-scanner, dependency-scanner, and git-rollback.
- **Workflow**: One of the five supported end-to-end AI workflows: WF1 (Requirement to Working Software), WF2 (Autonomous Refactoring), WF3 (Periodic Dependency Upgrades), WF4 (Autonomous Bug Fix), or WF5 (Autonomous Documentation). Each workflow has distinct inputs, steps, checkpoint thresholds, and output artifacts.
- **Workflow_Identifier**: A string value in the Project_Mapping_Configuration that specifies which workflow to execute. Valid values: `wf1-requirement-to-software`, `wf2-autonomous-refactoring`, `wf3-dependency-upgrades`, `wf4-bug-fix`, `wf5-documentation`.
- **Merge_Request**: A GitLab merge request created automatically by Kiro CLI via the gitlab MCP server, containing the AI-generated artifacts from the executed workflow.
- **Audit_Logger_MCP**: The existing MCP server that records all AI interactions, decisions, and checkpoint results for traceability. Invoked natively by Kiro CLI.
- **Security_Scanner_MCP**: The existing MCP server that performs code and dependency security scanning. Invoked natively by Kiro CLI.
- **Checkpoint_Gate**: A quality evaluation performed in the `checkpoint-gates` stage that assesses workflow-specific quality criteria (code review, test coverage, security scan) and blocks pipeline progression when criteria are not met. Coverage thresholds vary by workflow.

## Requirements

### Requirement 1: Project Mapping Configuration

**User Story:** As a devops engineer, I want a configuration file that maps Jira projects to Git repositories, workflow identifiers, and default workflow parameters, so that the integration knows which repo, branch, and workflow to target for each Jira project.

#### Acceptance Criteria

1. THE Project_Mapping_Configuration SHALL be a YAML file stored at `config/jira-project-mappings.yml` within the repository.
2. THE Project_Mapping_Configuration SHALL define, for each Jira project key, the following fields: Git repository path, target branch, Workflow_Identifier, and Kiro agent role.
3. THE Project_Mapping_Configuration SHALL define the Jira_Trigger_Status value that activates the webhook for each project mapping.
4. WHEN the `validate` stage reads the Project_Mapping_Configuration, THE `validate` stage SHALL verify that all required fields are present and non-empty using a shell or lightweight inline script.
5. IF the Project_Mapping_Configuration contains a Jira project key that is not mapped, THEN THE `validate` stage SHALL reject the pipeline run with a descriptive error message.
6. THE Project_Mapping_Configuration SHALL support multiple Jira project keys mapping to different repositories, branches, and Workflow_Identifiers within the same file.
7. WHERE a default workflow configuration is defined, THE Project_Mapping_Configuration SHALL apply the default values to any project mapping that omits optional fields.
8. THE Project_Mapping_Configuration SHALL accept only valid Workflow_Identifier values: `wf1-requirement-to-software`, `wf2-autonomous-refactoring`, `wf3-dependency-upgrades`, `wf4-bug-fix`, or `wf5-documentation`.
9. IF the Project_Mapping_Configuration contains an unrecognized Workflow_Identifier, THEN THE `validate` stage SHALL reject the pipeline run with a descriptive error message listing the valid workflow identifiers.

### Requirement 2: Jira Webhook Trigger

**User Story:** As a project manager, I want a Jira automation rule that fires a webhook when an issue transitions to "Ready for AI Dev", so that the AI development pipeline starts automatically.

#### Acceptance Criteria

1. WHEN a Jira issue transitions to the Jira_Trigger_Status, THE Jira_Webhook SHALL send an HTTP POST request to the GitLab pipeline trigger API endpoint.
2. THE Jira_Webhook SHALL include the Jira issue key (e.g., "PROJ-123") in the POST request payload.
3. THE Jira_Webhook SHALL include the Jira project key in the POST request payload.
4. THE Jira_Webhook SHALL use an authentication token stored as a GitLab CI/CD variable to authorize the trigger request.
5. IF the Jira_Webhook POST request fails with a non-2xx HTTP response, THEN the Jira automation rule SHALL retry the request up to 2 times with a 30-second delay between attempts.

### Requirement 3: Pipeline Trigger Validation (validate stage)

**User Story:** As a devops engineer, I want the GitLab pipeline to validate the webhook payload, project mapping, and workflow identifier before invoking Kiro CLI, so that only legitimate Jira events with valid configurations initiate pipeline runs.

#### Acceptance Criteria

1. WHEN the `validate` stage receives a pipeline trigger request, THE `validate` stage SHALL extract the Jira issue key from the trigger variables and store it as the `JIRA_ISSUE_KEY` CI variable.
2. WHEN the `validate` stage receives a pipeline trigger request, THE `validate` stage SHALL extract the Jira project key and store it as the `JIRA_PROJECT_KEY` CI variable.
3. THE `validate` stage SHALL verify that the `JIRA_ISSUE_KEY` variable matches the pattern `[A-Z][A-Z0-9]+-\d+` before proceeding.
4. IF the `JIRA_ISSUE_KEY` variable is missing or does not match the expected pattern, THEN THE `validate` stage SHALL fail the pipeline with a descriptive error message.
5. THE `validate` stage SHALL verify that the `JIRA_PROJECT_KEY` exists in the Project_Mapping_Configuration before proceeding.
6. IF the `JIRA_PROJECT_KEY` is not found in the Project_Mapping_Configuration, THEN THE `validate` stage SHALL fail the pipeline with a descriptive error message.
7. THE `validate` stage SHALL resolve the project configuration (repo_path, target_branch, Workflow_Identifier, agent) and write it to a JSON artifact for downstream stages.
8. THE `validate` stage SHALL resolve the Workflow_Identifier from the project-specific mapping or from the defaults section of the Project_Mapping_Configuration.
9. THE `validate` stage SHALL use only shell commands and a lightweight inline script for validation, with no dependency on a custom Python module.

### Requirement 4: Workflow Execution via Kiro CLI (execute-workflow stage)

**User Story:** As a developer, I want the pipeline to invoke Kiro CLI in headless mode with the Jira issue details and the resolved workflow identifier as input, so that the correct workflow (WF1–WF5) executes automatically using the developer agent's MCP servers.

#### Acceptance Criteria

1. WHEN the `execute-workflow` stage starts, THE Pipeline_Driver SHALL invoke Kiro_CLI in headless mode using `kiro-cli chat --no-interactive` with a prompt that includes the `JIRA_ISSUE_KEY`, the resolved Workflow_Identifier, and the resolved project configuration.
2. THE Kiro_CLI invocation SHALL use the developer agent, which has pre-configured MCP servers for jira, gitlab, audit-logger, security-scanner, dependency-scanner, and git-rollback.
3. THE Kiro_CLI SHALL retrieve the Jira issue details (summary, description, acceptance criteria) natively via the jira MCP server, eliminating the need for a separate Jira retrieval script.
4. WHEN the Workflow_Identifier is `wf1-requirement-to-software`, THE Kiro_CLI SHALL execute the WF1 workflow using the Jira issue description as the natural language requirement input, producing a Kiro spec (requirements, design, tasks), implemented code, unit tests, and documentation.
5. WHEN the Workflow_Identifier is `wf2-autonomous-refactoring`, THE Kiro_CLI SHALL execute the WF2 workflow using the target module path and refactoring goals extracted from the Jira issue, producing refactored code, performance benchmarks, and a delta report.
6. WHEN the Workflow_Identifier is `wf3-dependency-upgrades`, THE Kiro_CLI SHALL execute the WF3 workflow using the project path and upgrade scope extracted from the Jira issue, producing updated dependency files, code updates for breaking changes, and a delta report.
7. WHEN the Workflow_Identifier is `wf4-bug-fix`, THE Kiro_CLI SHALL execute the WF4 workflow using the bug report or failing test reference extracted from the Jira issue, producing a code fix, regression tests, and a side-effect analysis report.
8. WHEN the Workflow_Identifier is `wf5-documentation`, THE Kiro_CLI SHALL execute the WF5 workflow using the target codebase path and documentation types extracted from the Jira issue, producing API documentation, architecture diagrams, and onboarding guides.
9. THE Pipeline_Driver SHALL wrap the Kiro_CLI invocation with the existing `scripts/retry-wrapper.sh` to handle transient failures with up to 3 retries and exponential backoff.
10. IF the Kiro_CLI exit code is non-zero after all retry attempts, THEN THE Pipeline_Driver SHALL fail the pipeline.
11. THE Kiro_CLI SHALL log the workflow execution start and completion events natively via the audit-logger MCP server, including the Jira issue key, Workflow_Identifier, and pipeline ID.
12. THE `execute-workflow` stage SHALL contain a single Kiro_CLI invocation rather than multiple separate scripts for parsing, spec creation, and implementation.

### Requirement 5: Checkpoint Gates (checkpoint-gates stage)

**User Story:** As a devops engineer, I want the pipeline to evaluate code quality, test coverage, and security scan results using workflow-specific thresholds as a single checkpoint stage, so that quality gates block progression without requiring separate pipeline stages per check.

#### Acceptance Criteria

1. WHEN the `checkpoint-gates` stage runs, THE Pipeline_Driver SHALL invoke Kiro_CLI to perform an automated code review of the AI-generated artifacts for correctness, adherence to project conventions, and absence of security issues.
2. WHEN the `checkpoint-gates` stage runs, THE Pipeline_Driver SHALL execute the test suite against the AI-generated code and measure line coverage on new or modified code.
3. THE `checkpoint-gates` stage SHALL read the Workflow_Identifier from the project configuration artifact produced by the `validate` stage and apply the corresponding coverage threshold.
4. WHEN the Workflow_Identifier is `wf1-requirement-to-software`, THE Pipeline_Driver SHALL require a minimum of 80% line coverage on new code.
5. WHEN the Workflow_Identifier is `wf2-autonomous-refactoring`, THE Pipeline_Driver SHALL require a minimum of 80% line coverage and SHALL verify that all pre-existing tests pass.
6. WHEN the Workflow_Identifier is `wf3-dependency-upgrades`, THE Pipeline_Driver SHALL require a minimum of 70% line coverage and SHALL verify that the full test suite passes after the upgrade.
7. WHEN the Workflow_Identifier is `wf4-bug-fix`, THE Pipeline_Driver SHALL require a minimum of 90% line coverage on the fix and regression tests.
8. WHEN the Workflow_Identifier is `wf5-documentation`, THE Pipeline_Driver SHALL skip the test coverage check, as documentation workflows produce no executable code.
9. IF the measured line coverage is below the workflow-specific threshold, THEN THE Pipeline_Driver SHALL fail the pipeline with a report of the actual coverage percentage and the required threshold.
10. WHEN the `checkpoint-gates` stage runs, THE Pipeline_Driver SHALL invoke Kiro_CLI to run the security-scanner MCP `scan_code` and `scan_dependencies` tools against all AI-generated and modified files.
11. IF the security scan detects any HIGH or CRITICAL vulnerabilities, THEN THE Pipeline_Driver SHALL fail the pipeline with the vulnerability report.
12. THE `checkpoint-gates` stage SHALL log each checkpoint result (code review, test coverage, security scan) to the Audit_Logger_MCP via Kiro_CLI before proceeding or halting.
13. IF the code review identifies blocking issues, THEN THE Pipeline_Driver SHALL fail the pipeline with a descriptive error.
14. THE `checkpoint-gates` stage SHALL consolidate code review, test coverage, and security scan into a single pipeline stage with sequential evaluation, rather than using separate stages per check.

### Requirement 6: Branch Creation, Merge Request, and Finalization (finalize stage)

**User Story:** As a developer, I want the pipeline to push AI-generated artifacts to a feature branch, create a GitLab merge request, update the Jira issue, and log the audit trail — all via Kiro CLI MCP calls — so that the output is ready for review without manual steps or custom scripts.

#### Acceptance Criteria

1. WHEN the `finalize` stage runs after all checkpoint gates pass, THE Pipeline_Driver SHALL invoke Kiro_CLI to create a Git branch named `workflow/{WORKFLOW}/{JIRA_ISSUE_KEY_LOWER}` (e.g., `workflow/wf1-requirement-to-software/proj-123`).
2. THE Kiro_CLI SHALL commit all AI-generated artifacts (code, tests, documentation, dependency files, or other workflow-specific outputs) to the feature branch and push the feature branch to the GitLab remote repository.
3. WHEN the feature branch is pushed, THE Kiro_CLI SHALL create a Merge_Request via the gitlab MCP server targeting the branch specified in the Project_Mapping_Configuration.
4. THE Merge_Request SHALL include the Jira issue key in the title (e.g., "PROJ-123: [issue summary]").
5. THE Merge_Request SHALL include a description containing the original Jira issue summary, a link to the Jira issue, the Workflow_Identifier that was executed, and a summary of the AI-generated changes.
6. WHEN the Merge_Request is created successfully, THE Kiro_CLI SHALL transition the Jira issue status to "In Review" via the jira MCP server.
7. THE Kiro_CLI SHALL add a comment to the Jira issue containing the pipeline URL and merge request link via the jira MCP server.
8. THE Kiro_CLI SHALL log the complete workflow execution summary to the Audit_Logger_MCP, including the Workflow_Identifier, per-checkpoint outcomes, and artifact references (branch name, Merge_Request URL).
9. THE `finalize` stage SHALL delegate all Git operations, MR creation, Jira updates, and audit logging to Kiro_CLI MCP calls, with no custom Python scripts.

### Requirement 7: Jira Issue Status Updates

**User Story:** As a project manager, I want the Jira issue status to be updated automatically based on the pipeline outcome, so that the team has visibility into the AI development progress without checking GitLab.

#### Acceptance Criteria

1. WHEN the Pipeline_Driver completes workflow execution successfully and a Merge_Request is created, THE Kiro_CLI SHALL transition the Jira issue status to "In Review" via the jira MCP server.
2. IF the Pipeline_Driver fails at any stage, THEN THE Pipeline_Driver SHALL invoke Kiro_CLI to transition the Jira issue status to "AI Dev Failed" via the jira MCP server.
3. WHEN the Jira issue status is updated, THE Kiro_CLI SHALL add a comment to the Jira issue containing the pipeline URL and outcome details via the jira MCP server.
4. IF the Jira issue status update fails, THEN THE Kiro_CLI SHALL log the failure to the Audit_Logger_MCP and continue without blocking the pipeline.

### Requirement 8: Security and Authentication

**User Story:** As a devops engineer, I want all credentials and tokens used by the integration to be stored securely and never hardcoded, so that the integration follows security best practices.

#### Acceptance Criteria

1. THE Pipeline_Driver SHALL retrieve the Jira API authentication token from a GitLab CI/CD masked variable named `JIRA_API_TOKEN`.
2. THE Pipeline_Driver SHALL retrieve the GitLab pipeline trigger token from a GitLab CI/CD masked variable named `GITLAB_TRIGGER_TOKEN`.
3. THE Webhook_Receiver SHALL validate the trigger token on every incoming request before starting a pipeline.
4. IF the trigger token validation fails, THEN THE Webhook_Receiver SHALL reject the request.
5. THE Kiro_CLI SHALL sanitize all Jira issue content before using it as prompt input to prevent injection of malicious prompts or commands.
6. THE integration SHALL store no credentials, tokens, or secrets in source code, configuration files, or pipeline logs.

### Requirement 9: Pipeline Observability and Audit Trail

**User Story:** As a team lead, I want full observability of every Jira-triggered pipeline run, so that the team can trace any AI-generated change back to the originating Jira issue and review the complete execution history.

#### Acceptance Criteria

1. THE Kiro_CLI SHALL log a workflow start event to the Audit_Logger_MCP containing the Jira issue key, project key, Workflow_Identifier, pipeline ID, trigger timestamp, and initiator.
2. THE Kiro_CLI SHALL log a workflow end event to the Audit_Logger_MCP containing the outcome (success or failure), Workflow_Identifier, duration, and references to generated artifacts (branch name, Merge_Request URL).
3. WHEN a checkpoint is evaluated during the `checkpoint-gates` stage, THE Kiro_CLI SHALL log the checkpoint result to the Audit_Logger_MCP, including the workflow-specific threshold that was applied.
4. THE Audit_Logger_MCP records for Jira-triggered workflows SHALL include the `JIRA_ISSUE_KEY` in the `workflow_run_id` field to enable tracing from audit records back to the originating Jira issue.
5. THE Pipeline_Driver SHALL output a pipeline summary as a GitLab CI job artifact containing the Jira issue key, Workflow_Identifier, branch name, Merge_Request URL, and checkpoint results.

### Requirement 10: Error Handling and Recovery

**User Story:** As a devops engineer, I want robust error handling at every stage of the integration pipeline, so that failures are contained, reported, and recoverable.

#### Acceptance Criteria

1. IF the `validate` stage fails (invalid issue key, unmapped project, invalid Workflow_Identifier, or config error), THEN THE Pipeline_Driver SHALL fail the pipeline with a descriptive error message.
2. IF the Kiro_CLI workflow execution fails after all retry attempts in the `execute-workflow` stage, THEN THE Pipeline_Driver SHALL invoke Kiro_CLI to update the Jira issue status to "AI Dev Failed" via the jira MCP server and fail the pipeline.
3. IF any checkpoint gate fails in the `checkpoint-gates` stage, THEN THE Pipeline_Driver SHALL invoke Kiro_CLI to update the Jira issue status to "AI Dev Failed" via the jira MCP server and fail the pipeline.
4. IF the Merge_Request creation fails in the `finalize` stage, THEN THE Kiro_CLI SHALL log the failure to the Audit_Logger_MCP and update the Jira issue with a comment describing the partial completion.
5. THE Pipeline_Driver SHALL implement a timeout of 30 minutes for the complete pipeline execution, after which the pipeline is terminated.
6. WHEN a pipeline fails, THE Pipeline_Driver SHALL ensure no partial or broken code remains on the target branch by operating exclusively on the `workflow/{WORKFLOW}/{JIRA_ISSUE_KEY_LOWER}` feature branch.

### Requirement 11: Simplified Pipeline Stage Structure

**User Story:** As a devops engineer, I want the integration pipeline to use the minimum number of stages needed, delegating operations to Kiro CLI MCP servers instead of custom scripts, so that the pipeline is maintainable, auditable, workflow-agnostic, and easy to extend to new workflows.

#### Acceptance Criteria

1. THE Pipeline_Driver SHALL define exactly 4 ordered stages: `validate`, `execute-workflow`, `checkpoint-gates`, and `finalize`.
2. THE Pipeline_Driver stages SHALL execute in the order listed in criterion 1, with each stage starting only after the preceding stage completes successfully.
3. THE `validate` stage SHALL perform webhook payload extraction, issue key pattern validation, Workflow_Identifier resolution, and project configuration lookup using only shell commands and a lightweight inline script.
4. THE `execute-workflow` stage SHALL contain a single `kiro-cli chat --no-interactive` invocation that receives the Workflow_Identifier and Jira issue key, then executes the corresponding workflow as one unified operation.
5. THE `checkpoint-gates` stage SHALL evaluate code review, test coverage (using workflow-specific thresholds), and security scan results sequentially within a single pipeline job, using Kiro_CLI with its MCP servers.
6. THE `finalize` stage SHALL perform branch creation, merge request creation, Jira status update, and audit logging via a single `kiro-cli chat --no-interactive` invocation using the gitlab, jira, and audit-logger MCP servers.
7. THE Pipeline_Driver SHALL pass artifacts between stages using GitLab CI artifact dependencies.
8. IF any stage fails, THEN THE Pipeline_Driver SHALL halt execution and skip all subsequent stages.
9. THE Pipeline_Driver SHALL define the stage sequence independently from the existing repository pipeline stages (`lint`, `test`, `security`, `deploy`), using a dedicated `.gitlab-ci-workflow.yml` configuration included conditionally via `rules`.
10. THE Pipeline_Driver SHALL require no custom Python module (no `scripts/wf1_pipeline/` package) — all Jira, GitLab, security, and audit operations SHALL be performed by Kiro_CLI via its configured MCP servers.
