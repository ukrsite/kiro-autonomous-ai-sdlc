# Autonomous AI SDLC — KIRO CLI

An autonomous AI-driven Software Development Lifecycle built on [Kiro](https://kiro.dev). The system connects Jira issue tracking with GitLab CI and Kiro CLI to deliver end-to-end automated software development — from a Jira ticket to a merge request with tested, documented code.

## Quick Start (5 minutes)

![Demo](docs/gifs/demo2x.gif)

### Step 1: Generate a requirement with Kiro

```bash
# Clone the sandbox project (where AI-generated code will land)
git clone git@gitlab.internal.ericsson.com:san-tools-technology-platform/genai-innovation/ai-streams/developer/kiro-sandbox.git

# Clone this project (orchestration)
git clone git@gitlab.internal.ericsson.com:san-tools-technology-platform/genai-innovation/ai-streams/developer/kiro-autonomous-ai-sdlc.git
cd kiro-autonomous-ai-sdlc

# Authenticate Docker CLI with AWS ECR registry using IAM credentials
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 905418281081.dkr.ecr.us-east-1.amazonaws.com

# Generate MCP server config with resolved paths (required for kiro-cli/ide)
bash scripts/setup-kiro.sh

# Open kiro-cli 
kiro-cli
```

In Kiro chat, ask:

> Using AI-DLC, as a Product Owner I want to add a REST API endpoint that returns user profiles for the java-api service in the kiro-sandbox repository (../kiro-sandbox/services/python-processor)

Kiro will run the AI-DLC INCEPTION phase — workspace detection, requirements analysis, workflow planning — and produce a structured requirements document at `aidlc-docs/inception/requirements/requirements.md`.

You can run the full INCEPTION → CONSTRUCTION cycle locally (requires Java, Python, Node.js installed on your machine), or create a Jira issue and let the CI pipeline handle it.

### Step 2: Create a Jira issue

1. Go to [Jira AI-DLC](https://test.genai-innovation.ericsson.net/jira-ai-dlc/)
   - User/pass: `***` / `***`
2. Create a new issue in the `QWE` project
3. Paste the generated requirement into the issue description
4. Set the `SERVICE_NAME` custom field to the target service (e.g. `java-api`, `python-processor`, `node-gateway`)
5. Transition the issue status to **"Ready for AI Dev"** — this fires the webhook and triggers the pipeline automatically

### Step 3: Review the CI pipeline

Go to the pipelines view and watch the stages run:

[kiro-autonomous-ai-sdlc → Pipelines](https://gitlab.internal.ericsson.com/san-tools-technology-platform/genai-innovation/ai-streams/developer/kiro-autonomous-ai-sdlc/-/pipelines)

```
validate → execute-workflow → checkpoint-gates → finalize
```

- `validate` — resolves service config from the Jira project key
- `execute-workflow` — runs AI-DLC INCEPTION + CONSTRUCTION via kiro-cli inside the sandbox
- `checkpoint-gates` — tests, security scan, and code review run in parallel
- `finalize` — pushes branch `ai/{ISSUE_KEY}` to kiro-sandbox, creates MR, transitions Jira to "In Review"

### Step 4: Review the MR

Once the pipeline completes, the merge request is ready for human review:

[kiro-sandbox → Merge Requests](https://gitlab.internal.ericsson.com/san-tools-technology-platform/genai-innovation/ai-streams/developer/kiro-sandbox/-/merge_requests)

The MR contains implemented code, tests, documentation, and a full audit trail.

### Step 5: Run and Deploy

Once the MR is merged, run the sandbox locally and deploy via CI.

**Run the sandbox locally:**

```bash
cd kiro-sandbox
docker compose up --build
```

This starts all three services and a Swagger UI aggregator. Once healthy:

| Service | URL | Description |
|---|---|---|
| node-gateway | `http://localhost:3000` | API gateway (proxies to java-api and python-processor) |
| node-gateway docs | `http://localhost:3000/api-docs` | Swagger UI for gateway endpoints |
| java-api | `http://localhost:8080` | User management REST API |
| python-processor | `http://localhost:5000` | Data processing and reports |
| Aggregated docs | `http://localhost:8888` | Single entry point for all service API docs |

To stop: `docker compose down`. To rebuild after code changes: `docker compose up --build`.

**Deploy python-processor via CI to AWS EKS:**

The pipeline triggers automatically when files under `services/python-processor/` change on push.

No manual steps needed — merge to `main` for a production release, push to any other branch for a hash-tagged pre-release build.

# Python-processor UI
https://test.genai-innovation.ericsson.net/python-processor/docs

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Jira (Trigger)                        │
│  Issue transitions to "Ready for AI Dev" → webhook fires     │
├──────────────────────────────────────────────────────────────┤
│                    GitLab CI Pipeline                         │
│  validate → execute-workflow → checkpoint-gates → finalize   │
├──────────────────────────────────────────────────────────────┤
│                     Kiro CLI + Agents                         │
│  developer.json | devops.json                                │
│  AI-DLC: INCEPTION (plan) → CONSTRUCTION (build)             │
├──────────────────────────────────────────────────────────────┤
│                    Workflow Skills (WF1-WF5)                  │
│  WF1 New Feature | WF2 Refactor | WF3 Deps | WF4 Bug Fix    │
├──────────────────────────────────────────────────────────────┤
│                   Guardrails (Steering Files)                 │
│  security-rules | coding-standards | sandbox-boundaries      │
│  java-guardrails | python-guardrails | nodejs-guardrails     │
├──────────────────────────────────────────────────────────────┤
│                   MCP Servers (Infrastructure)                │
│  audit-logger | security-scanner | dependency-scanner        │
│  git-rollback | finops-cost-estimator                        │
├──────────────────────────────────────────────────────────────┤
│                    Sandbox Repository                         │
│  kiro-sandbox.git (services/java-api, python-processor,      │
│  node-gateway) — all code changes land here                  │
└──────────────────────────────────────────────────────────────┘
```

Two repositories are involved:

| Repository | Purpose |
|---|---|
| `kiro-autonomous-ai-sdlc` | Orchestration — pipeline, agents, skills, steering, MCP servers |
| `kiro-sandbox` | Application code — the services that get modified by the AI |


## How It Works

### AI-DLC Lifecycle

Every request goes through two phases:

```
INCEPTION (what to build)          CONSTRUCTION (how to build it)
├── Workspace Detection            ├── Code Generation
├── Reverse Engineering            ├── Build and Test
├── Requirements Analysis          └── Documentation
├── Workflow Planning
└── Handoff Artifact
```

INCEPTION analyzes the request, gathers requirements, and selects the right workflow (WF1-WF5). CONSTRUCTION executes the selected workflow to generate code, tests, and docs.

### Pipeline Flow

When a Jira issue transitions to "Ready for AI Dev":

1. **validate** — Resolves the Jira project key against `config/jira-project-mappings.yml`, determines the target service, workflow, and coverage threshold
2. **execute-workflow** — Clones `kiro-sandbox.git` into `sandbox/`, runs `kiro-cli` inside it to execute AI-DLC (INCEPTION + CONSTRUCTION). Code and docs are written directly to the sandbox repo
3. **checkpoint-gates** — Four parallel jobs:
   - `java-tests` — `mvn verify` + JaCoCo coverage (skips if no `pom.xml`)
   - `python-tests` — `pytest --cov` with per-file coverage on changed code
   - `security-scan` — `bandit` + `safety` (blocks on HIGH/CRITICAL)
   - `review` — AI-assisted code review via kiro-cli
4. **finalize** — Pushes branch `ai/{ISSUE_KEY}` to kiro-sandbox, creates MR via GitLab API, transitions Jira to "In Review"

### Workflows

| Workflow | Trigger | Coverage |
|---|---|---|
| WF1 — Requirement to Software | New feature or enhancement | 80% |
| WF2 — Autonomous Refactoring | Technical debt, code modernization | 80% |
| WF3 — Dependency Upgrades | Outdated or vulnerable dependencies | 70% |
| WF4 — Bug Fix | Bug report or failing test | 90% |
| WF5 — Documentation | Docs-only changes | N/A |

Each workflow loads shared rules from `.kiro/aws-aidlc-rule-details/` for consistent behavior: verbosity mode, error handling, overconfidence prevention, content validation, depth levels, code generation rules, and security baseline enforcement.

## Service Configuration

`config/jira-project-mappings.yml` maps Jira projects to sandbox services:

```yaml
sandbox_repo: https://gitlab.internal.ericsson.com/.../kiro-sandbox.git

defaults:
  workflow: wf1-requirement-to-software
  agent: developer
  trigger_status: "Ready for AI Dev"

projects:
  QWE:
    default_service: java-api
    services:
      java-api:
        repo_path: services/java-api
        target_branch: main
      python-processor:
        repo_path: services/python-processor
        target_branch: main
      node-gateway:
        repo_path: services/node-gateway
        target_branch: main
```

Set the `SERVICE_NAME` custom field on the Jira issue to target a specific service. If empty, `default_service` is used.

## Jira Automation Setup

The pipeline is triggered by a Jira Automation rule that fires when an issue transitions to "Ready for AI Dev".

**Trigger**: When issue transitioned → To status: "Ready for AI Dev"

**Action**: Send web request (POST, `application/x-www-form-urlencoded`):

```
URL: https://gitlab.internal.ericsson.com/api/v4/projects/115173/trigger/pipeline

Body:
token=<PIPELINE_TRIGGER_TOKEN>&ref=feat/kiro-autonomous-ai-sdlc-cicd&variables[JIRA_ISSUE_KEY]={{issue.key}}&variables[JIRA_SUMMARY]={{issue.summary}}&variables[JIRA_DESCRIPTION]={{issue.description}}&variables[JIRA_PROJECT_KEY]={{issue.project.key}}&variables[SERVICE_NAME]={{issue.SERVICE_NAME}}
```

### Required CI/CD Variables

| Variable | Description |
|---|---|
| `GL_TOKEN` | GitLab token with `api`, `read_repository`, `write_repository` on kiro-sandbox |
| `JIRA_ETEAM_TOKEN` | Jira PAT for REST API (transitions, comments) |
| `PIPELINE_TRIGGER_TOKEN` | GitLab pipeline trigger token |

### Manual Trigger (for testing)

```bash
curl -X POST \
  "https://gitlab.internal.ericsson.com/api/v4/projects/115173/trigger/pipeline" \
  -F "token=<TRIGGER_TOKEN>" \
  -F "ref=feat/kiro-autonomous-ai-sdlc-cicd" \
  -F "variables[JIRA_ISSUE_KEY]=QWE-4" \
  -F "variables[JIRA_SUMMARY]=Add user search endpoint" \
  -F "variables[JIRA_PROJECT_KEY]=QWE" \
  -F "variables[SERVICE_NAME]=java-api"
```

## MCP Servers

| Server | Purpose |
|---|---|
| `audit-logger` | Tamper-evident logging with SHA-256 hash chain |
| `security-scanner` | Static analysis (bandit) and dependency CVE scanning (safety) |
| `dependency-scanner` | Outdated dependency detection and upgrade planning |
| `git-rollback` | Git restore points and safe rollback |
| `finops-cost-estimator` | Pre-run cost estimation and post-run actual cost reporting for WF1/WF2 |

All servers run via stdio in CI. Locally, they use the Python virtual environment.

### FinOps Cost Reporting

At the end of every workflow run, the agent automatically calls `calculate_workflow_cost` and includes a cost breakdown in its final response:

```
## 💰 Workflow Cost Summary

Workflow: wf1-requirement-to-software
Token counting: recorded

| Dimension        | Quantity      | Unit Price          | Cost      |
|------------------|---------------|---------------------|-----------|
| LLM Input Tokens | 65,432 tokens | $0.003 / 1K tokens  | $0.196296 |
| LLM Output Tokens| 28,100 tokens | $0.015 / 1K tokens  | $0.421500 |
| Compute Time     | 5m 29s        | $0.00005 / sec      | $0.016450 |
| MCP Tool Calls   | 47            | $0.0001 / call      | $0.004700 |
| Checkpoints      | 9             | $0.001 / checkpoint | $0.009000 |
| Total            |               |                     | $0.65     |
```

Cost reports are written to `reports/finops/` as JSON and Markdown. Unit prices are configured in `config/finops-cost-model.yml`. Historical baselines are maintained per workflow type to improve estimate accuracy over time.

## Guardrails

Steering files enforce safety and quality rules automatically:

| File | When | What |
|---|---|---|
| `security-rules.md` | Always | No hardcoded secrets, input validation, dependency scanning |
| `coding-standards.md` | Always | Code review, coverage thresholds, documentation standards |
| `sandbox-boundaries.md` | Always | No production access, sandbox-only resources |
| `java-guardrails.md` | `*.java` files | Java/Spring conventions |
| `python-guardrails.md` | `*.py` files | Python/FastAPI conventions |
| `nodejs-guardrails.md` | `*.js`, `*.ts` files | Node.js/TypeScript conventions |

## Verbosity Mode

The workflow supports `silent` and `debug` output modes, configured in `aidlc-docs/aidlc-state.md`:

- `silent` — Only shows questions, approvals, errors, and results. Suppresses phase diagrams, stage announcements, and verbose completions.
- `debug` — Full output (default).

Switch at any time by telling Kiro: "switch to silent mode" or "switch to debug mode".

## Local Development

### Orchestration Repo Setup

```bash
# Clone and setup
git clone https://gitlab.internal.ericsson.com/.../kiro-autonomous-ai-sdlc.git
cd kiro-autonomous-ai-sdlc
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/setup-kiro.sh

# Run tests
pytest tests/

# Use an agent
kiro-cli agent swap developer
```

## CI Runner Image

The `docker/kiro-ci/Dockerfile` builds the CI runner image with Python 3.12, OpenJDK 21, Maven, Node.js 20, and kiro-cli. Rebuild after changes:

```bash
cd docker/kiro-ci
docker build -t <registry>/genai-kiro-ci:latest .
docker push <registry>/genai-kiro-ci:latest
```

## Project Structure

```
kiro-autonomous-ai-sdlc/
├── .kiro/
│   ├── aws-aidlc-rule-details/    # AI-DLC rule files (common, construction, inception, extensions)
│   ├── skills/developer-skills/   # WF1-WF5 workflow skills
│   ├── steering/                  # Guardrail steering files
│   └── settings/mcp.json         # MCP server config (auto-generated by setup-kiro.sh)
├── agents/                        # Agent configs (developer.json, devops.json)
├── config/
│   ├── jira-project-mappings.yml  # Jira project → service mapping
│   └── finops-cost-model.yml      # Unit prices and scaling factors for cost estimation
├── mcp-servers/                   # Custom MCP server implementations
├── reports/finops/                # Auto-generated cost reports (JSON + Markdown)
├── scripts/                       # Setup, validation, and utility scripts
├── docker/kiro-ci/               # CI runner Dockerfile
├── .gitlab-ci.yml                # Main CI pipeline
└── .gitlab-ci-workflow.yml       # Jira-triggered AI workflow pipeline
```

## Documentation

- `docs/architecture-documentation.md` — System architecture
- `docs/workflow-descriptions.md` — Workflow details
- `docs/guardrail-configurations.md` — Steering and hook configs
- `docs/audit-log-samples.md` — Audit record examples
- `docs/aidlc-wf-integration.md` — AI-DLC workflow integration guide

## License

Internal use only.
