# Autonomous AI SDLC — KIRO CLI

An autonomous AI-driven Software Development Lifecycle built on [Kiro](https://kiro.dev). The system connects Jira issue tracking with GitLab CI and Kiro CLI to deliver end-to-end automated software development — from a Jira ticket to a merge request with tested, documented code.

## Quick Start (5 minutes)

### Step 1: Generate a requirement with Kiro

```bash
# Clone this project
git clone https://gitlab.internal.ericsson.com/.../kiro-autonomous-ai-sdlc.git
cd kiro-autonomous-ai-sdlc

# Open in use kiro-cli (or Kiro IDE)
kiro-cli
```

In Kiro chat, ask:

> Using AI-DLC, as a Product Owner I want to add a REST API endpoint that returns user profiles for the java-api service in the kiro-sandbox repository.

Kiro will run the AI-DLC INCEPTION phase — workspace detection, requirements analysis, workflow planning — and produce a structured requirements document at `aidlc-docs/inception/requirements/requirements.md`.

### Step 2: Create a Jira issue

1. Go to [Jira AI-DLC](https://test.genai-innovation.ericsson.net/jira-ai-dlc/)
2. Create a new issue in the `QWE` project
3. Paste the generated requirement into the issue description
4. Set the `SERVICE_NAME` custom field to the target service (e.g. `java-api`, `python-processor`, `node-gateway`)

### Step 3: Trigger the pipeline

Transition the Jira issue status to "Ready for AI Dev".

That's it. The Jira Automation rule fires a webhook to GitLab, which triggers the full pipeline:

```
Jira "Ready for AI Dev"
  → GitLab pipeline starts
    → validate (resolve service config)
    → execute-workflow (AI-DLC INCEPTION + CONSTRUCTION via kiro-cli)
    → checkpoint-gates (tests, security scan, code review — in parallel)
    → finalize (push branch ai/{ISSUE_KEY} to kiro-sandbox, create MR, update Jira)
```

The result: a merge request on [kiro-sandbox](https://gitlab.internal.ericsson.com/san-tools-technology-platform/genai-innovation/ai-streams/developer/kiro-sandbox) with implemented code, tests, and documentation.

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
│  git-rollback                                                │
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
| `KIRO_AUTH_DB` | Base64-encoded kiro-cli auth DB |
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

All servers run via stdio in CI. Locally, they use the Python virtual environment.

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
├── config/jira-project-mappings.yml  # Jira project → service mapping
├── mcp-servers/                   # Custom MCP server implementations
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
