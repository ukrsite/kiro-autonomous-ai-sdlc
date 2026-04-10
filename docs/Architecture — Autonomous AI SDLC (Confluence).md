# Architecture — Autonomous AI Software Development Lifecycle

> **Status:** Live | **Last Updated:** 2026-04-09 | **Owner:** GenAI Innovation Team

This system transforms natural language requirements (Jira tickets) into working, tested, documented code — delivered as merge requests — with full audit trails and safety guardrails.

The architecture uses [Kiro](https://kiro.dev) native primitives (Skills, Steering, Hooks, Agents, MCP servers) with AI-DLC (AI-Driven Development Lifecycle) for structured requirements-to-code execution. No custom workflow engine is required.

> **Key URLs:**
> - Jira: [https://test.genai-innovation.ericsson.net/jira-ai-dlc/](https://test.genai-innovation.ericsson.net/jira-ai-dlc/)
> - Data Processor — Swagger UI: [https://test.genai-innovation.ericsson.net/python-processor/docs](https://test.genai-innovation.ericsson.net/python-processor/docs)
> - Orchestration Repo: [kiro-autonomous-ai-sdlc](https://gitlab.internal.ericsson.com/san-tools-technology-platform/genai-innovation/ai-streams/developer/kiro-autonomous-ai-sdlc)
> - Sandbox Repo: [kiro-sandbox](https://gitlab.internal.ericsson.com/san-tools-technology-platform/genai-innovation/ai-streams/developer/kiro-sandbox)

---

## 1. System Overview

The system operates through two complementary paths:

| Path | Use Case | Entry Point | Human Involvement |
|---|---|---|---|
| **Path A — Kiro IDE** | Exploratory, novel, complex tasks | Developer ↔ Kiro IDE | Interactive review in IDE |
| **Path B — CI Pipeline** | Well-patterned features, bulk tickets | Jira → GitLab CI → kiro-cli | MR approval only |

Both paths share the same workflow skills, guardrails, AI-DLC rules, and audit system.

```
┌─────────────────────────────────────────────────────┐
│  Path A — Kiro IDE (Development)                    │
│                                                     │
│   ┌───────────┐  interactive chat  ┌──────────────┐ │
│   │ Developer │←──────────────────→│ Kiro IDE /   │ │
│   └───────────┘                    │ kiro-cli     │ │
│                                    └──────┬───────┘ │
└───────────────────────────────────────────┼─────────┘
                                            │
┌───────────────────────────────────────────┼─────────┐
│  Path B — CI Pipeline (Production)        │         │
│                                           │         │
│   ┌────────────┐ webhook ┌───────────┐    │         │
│   │ Jira Issue │────────→│ GitLab CI │    │         │
│   └────────────┘         └─────┬─────┘    │         │
│                                │          │         │
│                   kiro-cli     │          │         │
│                  --no-interactive          │         │
│                                │          │         │
│                                ↓          │         │
│                     ┌──────────────────┐  │         │
│                     │ kiro-cli         │  │         │
│                     │ (headless)       │  │         │
│                     └────────┬─────────┘  │         │
│                              │ MR         │         │
│                              ↓            │         │
│                     ┌──────────────────┐  │         │
│                     │ kiro-sandbox     │  │         │
│                     └──────────────────┘  │         │
└───────────────────────────────┼───────────┘
                                │
                                ↓
┌───────────────────────────────────────────┐
│  Shared Layer                             │
│                                           │
│   ┌─────────────────┐  ┌───────────────┐  │
│   │ Skills (WF1-WF5)│  │ Steering      │  │
│   └─────────────────┘  │ (guardrails)  │  │
│   ┌─────────────────┐  └───────────────┘  │
│   │ AI-DLC Rule     │  ┌───────────────┐  │
│   │ Details         │  │ MCP Servers   │  │
│   └─────────────────┘  └───────────────┘  │
│   ┌─────────────────┐                     │
│   │ Audit Logger    │                     │
│   └─────────────────┘                     │
└───────────────────────────────────────────┘
```

### 1.1 End-to-End Delivery: Jira → Code → EKS

Once the AI generates code and the MR is merged, a per-service CI pipeline in `kiro-sandbox` takes over:

```
Jira Issue → AI-DLC (kiro-cli) → MR → merge to main
  → semantic-release (version tag)
  → Kaniko (container image → Artifactory → ECR)
  → Helm chart (package → ECR OCI registry)
  → GitOps (ArgoCD/Flux detects new chart → deploys to EKS)
```

| Stage | What happens |
|---|---|
| AI-DLC pipeline | Jira → validate → execute-workflow → checkpoint-gates → finalize → MR |
| Merge to main | Triggers per-service `.gitlab-ci.yml` in kiro-sandbox |
| semantic-release | Computes next semver, creates Git tag, publishes GitLab release |
| Kaniko build | Builds container image, pushes to Artifactory + AWS ECR |
| Helm publish | Packages chart, pushes to ECR OCI Helm registry |
| GitOps deploy | ArgoCD/Flux detects new chart version in ECR, deploys to AWS EKS |

The python-processor service is live at [https://test.genai-innovation.ericsson.net/python-processor/docs](https://test.genai-innovation.ericsson.net/python-processor/docs) — deployed automatically via this pipeline.

---

## 2. Architecture

### 2.1 Two-Repository Model

| Repository | Purpose |
|---|---|
| **kiro-autonomous-ai-sdlc** | Orchestration — pipeline, agents, skills, steering, MCP servers, AI-DLC rules |
| **kiro-sandbox** | Application code — services modified by the AI, plus AI-DLC artifacts |

```
┌─────────────────────────────────────────────────────────┐
│  kiro-autonomous-ai-sdlc (Orchestration)                │
│                                                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │ .kiro/skills/ — WF1-WF5 SKILL.md                  │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ .kiro/steering/ — security, coding standards,      │ │
│  │                   sandbox                          │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ .kiro/aws-aidlc-rule-details/ — common,            │ │
│  │                   construction, inception          │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ agents/ — developer.json, devops.json              │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ mcp-servers/ — audit-logger, security-scanner,     │ │
│  │   dependency-scanner, git-rollback,                │ │
│  │   finops-cost-estimator                            │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ .gitlab-ci-workflow.yml                            │ │
│  └──────────────────────┬─────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────┘
                          │
            clone → modify → push → MR
                          │
                          ↓
┌─────────────────────────────────────────────────────────┐
│  kiro-sandbox (Application Code)                        │
│                                                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │ services/java-api — Spring Boot 3.2.3, Java 21     │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ services/python-processor — FastAPI, Python 3.12   │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ services/node-gateway — Express, Node 20           │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ aidlc-docs/ — AI-DLC artifacts                     │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```


### 2.2 Kiro Primitive Mapping

Every component maps to a Kiro-native primitive — no custom engine code:

| Kiro Primitive | Files | SDLC Role |
|---|---|---|
| **Skills** | `.kiro/skills/developer-skills/wf{1-5}/SKILL.md` | Workflow definitions |
| **Steering** | `.kiro/steering/*.md` | Always-on guardrails + language-specific (fileMatch) |
| **Hooks** | `.kiro/hooks/*.json` | Event triggers (preToolUse, postTaskExecution) |
| **Agent configs** | `agents/developer.json`, `agents/devops.json` | Role-based routing with MCP bindings |
| **MCP servers** | `mcp-servers/*/server.py` | Infrastructure tooling via stdio |
| **AI-DLC rules** | `.kiro/aws-aidlc-rule-details/` | Phase rules loaded by WF skills |

### 2.3 Component Architecture

```
┌───────────────────────────────────────┐
│  Entry Points                         │
│  ┌──────────────┐  ┌───────────────┐  │
│  │ Kiro IDE     │  │ kiro-cli      │  │
│  │ (interactive)│  │ (headless CI) │  │
│  └──────┬───────┘  └───────┬───────┘  │
└─────────┼──────────────────┼──────────┘
          │                  │
          └────────┬─────────┘
                   ↓
┌───────────────────────────────────────┐
│  AI-DLC Lifecycle                     │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │ INCEPTION — Workspace Detection │  │
│  │ → Requirements → Planning       │  │
│  └──────────────┬──────────────────┘  │
│        Handoff Artifact               │
│  ┌──────────────↓──────────────────┐  │
│  │ CONSTRUCTION — Code Generation  │  │
│  │ → Build & Test → Docs           │  │
│  └──────────────┬──────────────────┘  │
└─────────────────┼─────────────────────┘
          ┌───────┼───────┐
          ↓       ↓       ↓
┌─────────────────────────────────────────┐
│  Guardrails Layer                       │
│  ┌──────────────┐  ┌─────────────────┐  │
│  │ security-    │  │ coding-         │  │
│  │ rules.md     │  │ standards.md    │  │
│  ├──────────────┤  ├─────────────────┤  │
│  │ sandbox-     │  │ java / python / │  │
│  │ boundaries.md│  │ nodejs guards   │  │
│  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  MCP Servers                            │
│  ┌──────────────────────────────────┐   │
│  │ audit-logger — SHA-256 hash chain│   │
│  ├──────────────────────────────────┤   │
│  │ security-scanner — bandit+safety │   │
│  ├──────────────────────────────────┤   │
│  │ dependency-scanner — outdated+CVE│   │
│  ├──────────────────────────────────┤   │
│  │ git-rollback — restore points    │   │
│  ├──────────────────────────────────┤   │
│  │ finops-cost-estimator — cost     │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
          │
          │  code + tests + docs
          ↓
┌─────────────────────────────────────────┐
│  kiro-sandbox                           │
│  ┌──────────────────────────────────┐   │
│  │ services/ — java-api,            │   │
│  │   python-processor, node-gateway │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

## 3. AI-DLC Lifecycle

AI-DLC (AI-Driven Development Lifecycle) is a structured two-phase process that adapts to request complexity.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  INCEPTION — what to build                                               │
│                                                                          │
│  ┌──────────────────────────┐                                            │
│  │ Workspace Detection      │ ← ALWAYS                                   │
│  └────────────┬─────────────┘                                            │
│               ↓                                                          │
│  ┌──────────────────────────┐                                            │
│  │ Reverse Engineering      │ ← CONDITIONAL                              │
│  └────────────┬─────────────┘                                            │
│               ↓                                                          │
│  ┌──────────────────────────┐                                            │
│  │ Requirements Analysis    │ ← ALWAYS                                   │
│  └────────────┬─────────────┘                                            │
│               ↓                                                          │
│  ┌──────────────────────────┐                                            │
│  │ User Stories             │ ← CONDITIONAL                              │
│  └────────────┬─────────────┘                                            │
│               ↓                                                          │
│  ┌──────────────────────────┐                                            │
│  │ Workflow Planning        │ ← ALWAYS                                   │
│  └────────────┬─────────────┘                                            │
│               ↓                                                          │
│  ┌──────────────────────────┐                                            │
│  │ Application Design       │ ← CONDITIONAL                              │
│  └────────────┬─────────────┘                                            │
│               ↓                                                          │
│  ┌──────────────────────────┐                                            │
│  │ Units Generation         │ ← CONDITIONAL                              │
│  └────────────┬─────────────┘                                            │
└───────────────┼──────────────────────────────────────────────────────────┘
                ↓
   ┌─────────────────────────┐
   │    Handoff Artifact      │
   └────────────┬────────────┘
                ↓
┌───────────────┼──────────────────────────────────────────────────────────┐
│  CONSTRUCTION — how to build it                                          │
│               ↓                                                          │
│  ┌──────────────────────────┐                                            │
│  │ Functional Design        │ ← CONDITIONAL                              │
│  └────────────┬─────────────┘                                            │
│               ↓                                                          │
│  ┌──────────────────────────┐                                            │
│  │ Code Generation          │ ← ALWAYS                                   │
│  └────────────┬─────────────┘                                            │
│               ↓                                                          │
│  ┌──────────────────────────┐                                            │
│  │ Build and Test           │ ← ALWAYS                                   │
│  └────────────┬─────────────┘                                            │
│               ↓                                                          │
│  ┌──────────────────────────┐                                            │
│  │ Documentation            │ ← ALWAYS                                   │
│  └──────────────────────────┘                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

**INCEPTION** analyzes the request, gathers requirements, and selects the appropriate workflow (WF1-WF5). It produces a Handoff Artifact consumed by CONSTRUCTION.

**CONSTRUCTION** is delegated to the selected WF skill, which generates code, tests, and documentation.

### 3.1 Shared Rule Details

Each WF skill loads rules from `.kiro/aws-aidlc-rule-details/` at startup:

| Rule File | Purpose |
|---|---|
| `common/verbosity-mode.md` | Silent/debug output control |
| `common/error-handling.md` | Error severity, recovery, escalation |
| `common/overconfidence-prevention.md` | Default to asking questions |
| `common/content-validation.md` | Validate content before writing |
| `common/depth-levels.md` | Adapt detail to complexity |
| `construction/code-generation.md` | Code location, brownfield rules, automation-friendly code |
| `construction/build-and-test.md` | Test strategy, instruction formats |
| `extensions/security/baseline/security-baseline.md` | 15 SECURITY rules (OWASP-mapped) |

---

## 4. Workflows

### 4.1 Available Workflows

| Workflow | Trigger | Coverage | Description |
|---|---|---|---|
| **WF1 — Requirement to Software** | New feature / enhancement | 80% | Requirement → design → code → tests → docs → MR |
| **WF2 — Autonomous Refactoring** | Technical debt | 80% | Analyze → refactor → verify behavior equivalence → benchmark |
| **WF3 — Dependency Upgrades** | Outdated / vulnerable deps | 70% | Scan → compatibility → upgrade → full test suite |
| **WF4 — Bug Fix** | Bug report / failing test | 90% | Root cause → fix → regression tests → side-effect analysis |
| **WF5 — Documentation** | Docs-only changes | N/A | Codebase analysis → generate docs |

### 4.2 WF1 — Requirement to Software (Primary)

```
┌───────┐   ┌────────┐   ┌────────┐   ┌───────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌──────┐   ┌───────┐
│ Parse │   │ Create │   │ Create │   │ Impl  │   │Code │   │Test │   │ Sec │   │ Gen  │   │       │
│ Req   │──→│ Kiro   │──→│Restore │──→│ Tasks │──→│Rev ✓│──→│Cov ✓│──→│Scan │──→│ Docs │──→│ Merge │
│       │   │ Spec   │   │ Point  │   │       │   │     │   │≥80% │   │  ✓  │   │      │   │       │
└───────┘   └────────┘   └────────┘   └───────┘   └─────┘   └─────┘   └─────┘   └──────┘   └───────┘
                                                   ^^^^^^    ^^^^^^    ^^^^^^
                                                   checkpoint gates
```

### 4.2.1 Example: WF1 Flow for Adding a New Endpoint

Paste something like this into Kiro CLI:

> Using AI-DLC, as a Product Owner I want to add a new REST API endpoint GET /api/v1/health/detailed to the python-processor service in the kiro-sandbox repository (../kiro-sandbox/services/python-processor). The endpoint should return a JSON response with service name, version, uptime, and current timestamp.

**INCEPTION PHASE:**

1. **Workspace Detection** — scans `../kiro-sandbox/services/python-processor`, detects brownfield Python/FastAPI project
2. **Reverse Engineering** (if first time) — catalogs existing routes, models, dependencies
3. **Requirements Analysis** — asks clarifying questions:
   - Should the endpoint require authentication?
   - What HTTP status codes should it return?
   - Should uptime be calculated from process start or deployment time?
4. **Workflow Planning** — classifies as WF1 (new feature), presents execution plan for approval
5. **Handoff Artifact** — generates `workflow-handoff.md` consumed by WF1

**CONSTRUCTION PHASE (WF1):**

6. **Functional Design** — defines the response schema:

```json
{
  "service": "python-processor",
  "version": "1.2.0",
  "uptime_seconds": 3842,
  "timestamp": "2026-04-09T15:38:43Z"
}
```

7. **Code Generation** — produces minimal code:

```python
# routers/health.py
import time
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/health", tags=["health"])
_start_time = time.monotonic()

@router.get("/detailed")
async def detailed_health():
    return {
        "service": "python-processor",
        "version": "1.2.0",
        "uptime_seconds": round(time.monotonic() - _start_time),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

```python
# test_health.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_detailed_health():
    resp = client.get("/api/v1/health/detailed")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "python-processor"
    assert "uptime_seconds" in body
    assert "timestamp" in body
```

8. **Checkpoint Gates** (all must pass before merge):

| Checkpoint | What runs | Pass criteria |
|---|---|---|
| Code Review | AI reviews correctness, conventions, dead code | No blocking issues |
| Security Scan | `scan_code` + `scan_dependencies` via MCP | No HIGH/CRITICAL findings |
| Test Coverage | `pytest --cov` on changed files | ≥80% line coverage |

9. **Generate Documentation** — 5 mandatory artifacts:
   - `docs/release-notes-{ISSUE_KEY}.md`
   - `docs/CHANGELOG.md`
   - `docs/openapi.yaml`
   - `docs/architecture.md`
   - `docs/wf1-summary-{ISSUE_KEY}.md`

10. **Merge** — if all checkpoints pass, code is merged to the target branch

**Cost Report** — automatic at the end:

```
## 💰 Workflow Cost Summary

Workflow: wf1-requirement-to-software

| Dimension         | Quantity      | Unit Price          | Cost       |
|-------------------|---------------|---------------------|------------|
| LLM Input Tokens  | ~50K tokens   | $0.003 / 1K tokens  | ~$0.15     |
| LLM Output Tokens | ~20K tokens   | $0.015 / 1K tokens  | ~$0.30     |
| Compute Time      | ~7m           | $0.00005 / sec      | ~$0.02     |
| MCP Tool Calls    | ~15           | $0.0001 / call      | ~$0.002    |
| Checkpoints       | 3             | $0.001 / checkpoint | ~$0.003    |
| Total             |               |                     | ~$0.50     |
```

### 4.3 Checkpoint Gates

All checkpoints must pass before merge:

| Checkpoint | Type | Criteria |
|---|---|---|
| **Code Review** | Automated + human | Correctness, conventions, no dead code |
| **Test Coverage** | Automated | WF1: 80%, WF2: 80%, WF3: 70%, WF4: 90% |
| **Security Scan** | Automated | No HIGH or CRITICAL findings |

> If any checkpoint fails: workflow stops, failure logged to audit, `git-rollback` MCP restores previous state.

---

## 5. CI/CD Pipeline

### 5.1 Pipeline Architecture

```
                                        ┌──────────────────────────────────────────────────────────┐
                                        │  GitLab CI Pipeline                                      │
                                        │                                                          │
┌────────────┐   ┌──────────┐           │  ┌──────────┐   ┌──────────────┐   ┌─────────────────┐   │
│ Jira Issue │   │  Jira    │           │  │          │   │   execute-   │   │ checkpoint-gates│   │
│ Ready for  │──→│Automation│──────────→│  │ validate │──→│   workflow   │──→│   (parallel)    │   │
│ AI Dev     │   │ Webhook  │           │  │          │   │  kiro-cli in │   │                 │   │
└────────────┘   └──────────┘           │  └──────────┘   │  sandbox/    │   │ ┌─────────────┐ │   │
                                        │                 └──────────────┘   │ │ java-tests  │ │   │
                                        │                                    │ │ python-tests│ │   │
                                        │                                    │ │ node-tests  │ │   │
                                        │                                    │ │ security-   │ │   │
                                        │                                    │ │   scan      │ │   │
                                        │                                    │ │ review      │ │   │
                                        │                                    │ └──────┬──────┘ │   │
                                        │                                    └────────┼────────┘   │
                                        │                                             ↓            │
                                        │                                    ┌─────────────────┐   │
                                        │                                    │    finalize      │   │
                                        │                                    │ push + MR + Jira │   │
                                        │                                    └────────┬────────┘   │
                                        └─────────────────────────────────────────────┼────────────┘
                                                                                      ↓
                                                                             ┌─────────────────┐
                                                                             │ MR on kiro-      │
                                                                             │ sandbox —        │
                                                                             │ ai/ISSUE_KEY     │
                                                                             └─────────────────┘
```

### 5.2 Pipeline Stages

| Stage | Image | Purpose |
|---|---|---|
| **validate** | kiro-ci | Resolve Jira project → service → workflow → coverage threshold |
| **execute-workflow** | kiro-ci | Clone kiro-sandbox, `cd sandbox`, run AI-DLC via kiro-cli |
| **java-tests** | maven:3.9-eclipse-temurin-21 | `mvn verify` + JaCoCo coverage |
| **python-tests** | python:3.12-slim | `pytest --cov` with per-service coverage (multi-service aware) |
| **node-tests** | node:18 | `npm test` + Jest coverage (skips if no `package.json`) |
| **security-scan** | python:3.12-slim | `bandit` + `safety` (blocks on HIGH/CRITICAL) |
| **review** | kiro-ci | AI-assisted code review via kiro-cli |
| **finalize** | kiro-ci | Push branch, create MR, transition Jira |
| **on-failure** | kiro-ci | Transition Jira to "AI Dev Failed" |

### 5.3 End-to-End Sequence

```
  Product Owner          Jira (EKS)         GitLab CI          kiro-cli        kiro-sandbox
       │                     │                  │                  │                │
       │  Create issue +     │                  │                  │                │
       │  set SERVICE_NAME   │                  │                  │                │
       │────────────────────→│                  │                  │                │
       │                     │                  │                  │                │
       │  Transition to      │                  │                  │                │
       │  "Ready for AI Dev" │                  │                  │                │
       │────────────────────→│                  │                  │                │
       │                     │                  │                  │                │
       │                     │  Webhook POST    │                  │                │
       │                     │  (issue key,     │                  │                │
       │                     │   summary,       │                  │                │
       │                     │   service)       │                  │                │
       │                     │─────────────────→│                  │                │
       │                     │                  │                  │                │
       │                     │                  │  validate        │                │
       │                     │                  │  (resolve config)│                │
       │                     │                  │─────────┐        │                │
       │                     │                  │←────────┘        │                │
       │                     │                  │                  │                │
       │                     │                  │  clone kiro-     │                │
       │                     │                  │  sandbox.git     │                │
       │                     │                  │─────────────────────────────────→│
       │                     │                  │                  │                │
       │                     │                  │  execute-workflow│                │
       │                     │                  │  (AI-DLC)        │                │
       │                     │                  │─────────────────→│                │
       │                     │                  │                  │                │
       │                     │                  │                  │  write code +  │
       │                     │                  │                  │  tests + docs  │
       │                     │                  │                  │───────────────→│
       │                     │                  │                  │                │
       │                     │                  │  checkpoint-gates│                │
       │                     │                  │  (parallel)      │                │
       │                     │                  │─────────┐        │                │
       │                     │                  │←────────┘        │                │
       │                     │                  │                  │                │
       │                     │                  │  push ai/ISSUE_KEY, create MR    │
       │                     │                  │─────────────────────────────────→│
       │                     │                  │                  │                │
       │                     │  transition to   │                  │                │
       │                     │  "In Review"     │                  │                │
       │                     │←─────────────────│                  │                │
       │                     │                  │                  │                │
       │  review MR          │                  │                  │                │
       │─────────────────────────────────────────────────────────────────────────→│
       │                     │                  │                  │                │
```

### 5.4 Retry and Recovery

| Layer | Mechanism | Detail |
|---|---|---|
| kiro-cli | `retry-wrapper.sh` | 5 retries, exponential backoff (15s→300s cap), rate-limit detection (60s cooldown) |
| GitLab job | `retry: max: 2` | Runner crashes, network timeouts |
| MR creation | HTTP 409 handler | Fetches existing MR URL |
| Rollback | `git-rollback` MCP | Restore point before implementation |

---

## 6. Jira Instance — AWS EKS

A dedicated Jira instance serves as the issue tracking frontend for the AI-DLC pipeline.

> **URL:** [https://test.genai-innovation.ericsson.net/jira-ai-dlc/](https://test.genai-innovation.ericsson.net/jira-ai-dlc/)

```
┌──────────────┐   browser    ┌──────────────────────────────────────────┐
│ Developer /  │─────────────→│ AWS ALB Ingress                         │
│ PO           │              │ test.genai-innovation.ericsson.net       │
└──────────────┘              └──────────────────┬───────────────────────┘
                                                 │ /jira-ai-dlc/
                                                 ↓
                              ┌──────────────────────────────────────────┐
                              │  AWS EKS Cluster                        │
                              │                                         │
                              │  ┌──────────────┐  Automation  ┌──────┐ │
                              │  │  Jira Pod    │──webhook────→│GitLab│ │
                              │  │              │              │Pipe- │ │
                              │  │              │←─REST API──┐ │line  │ │
                              │  └──────────────┘            │ │Trigger│
                              │                              │ │API   │ │
                              │  ┌──────────────┐            │ └──┬───┘ │
                              │  │ GitLab Runner│────────────┘    │     │
                              │  │ (EKS)       │←─ pipeline ──────┘     │
                              │  └──────┬───────┘                       │
                              └─────────┼───────────────────────────────┘
                                        │
                           clone + push + MR
                                        ↓
                              ┌──────────────────┐
                              │ kiro-sandbox.git  │
                              └──────────────────┘
```

| Component | Detail |
|---|---|
| **Platform** | AWS EKS (Kubernetes) |
| **Project Key** | `QWE` |
| **Custom Fields** | `SERVICE_NAME` — java-api, python-processor, node-gateway |
| **Automation** | Issue → "Ready for AI Dev" → POST to GitLab trigger API |
| **Workflow** | To Do → Ready for AI Dev → In Review → Done |

---

## 7. Safety and Guardrails

### 7.1 Steering Files

| File | Inclusion | Scope |
|---|---|---|
| **security-rules.md** | Always | No hardcoded secrets, input validation, dependency scanning |
| **coding-standards.md** | Always | Code review, coverage thresholds, documentation standards |
| **sandbox-boundaries.md** | Always | No production access, sandbox-only resources |
| **finops-cost-reporting.md** | Always | Mandatory cost reporting at end of every workflow run |
| **java-guardrails.md** | fileMatch `*.java` | Java/Spring conventions |
| **python-guardrails.md** | fileMatch `*.py` | Python/FastAPI conventions |
| **nodejs-guardrails.md** | fileMatch `*.js`, `*.ts` | Node.js/TypeScript conventions |

### 7.2 Security Baseline (OWASP-Mapped)

15 SECURITY rules conditionally enforced via `aidlc-state.md`:

| Rule | Category |
|---|---|
| SECURITY-01 | Encryption at rest and in transit |
| SECURITY-05 | Input validation on all API parameters |
| SECURITY-08 | Application-level access control (A01:2025) |
| SECURITY-10 | Software supply chain security (A03:2025) |
| SECURITY-12 | Authentication and credential management (A07:2025) |
| SECURITY-15 | Exception handling and fail-safe defaults (A10:2025) |

### 7.3 Checkpoint Flow

```
┌──────────────────────┐
│ Code generated by LLM│
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Automated checkpoint │
│ compile + lint + test│
└─────┬────────┬───────┘
      │        │
     pass     fail
      │        ↓
      │   ┌──────────────────────────┐
      │   │ Retry with error context │
      │   │ max 2x                   │
      │   └─────┬──────────┬─────────┘
      │        pass    still failing
      │         │          ↓
      │         │   ┌──────────────┐
      │         │   │ Workflow     │
      ↓         ↓   │ STOPS ✗     │
┌──────────────────┐└──────────────┘
│ Security scan    │       ↑
│ bandit + safety  │       │
└─────┬────────┬───┘       │
      │        │           │
     pass   HIGH/CRITICAL  │
      │        └───────────┘
      ↓
┌──────────────────┐
│ Code review      │
│ AI-assisted      │
└─────┬────────────┘
      │ approved
      ↓
┌──────────────────┐
│ Create MR ✓      │
└──────────────────┘
```

---

## 8. MCP Servers

| Server | Purpose | Key Tools |
|---|---|---|
| **audit-logger** | Tamper-evident logging (SHA-256 hash chain) | `log_interaction`, `log_checkpoint`, `log_event`, `query_audit` |
| **security-scanner** | Static analysis + dependency CVE scanning | `scan_code`, `scan_dependencies`, `get_scan_report` |
| **dependency-scanner** | Outdated dependency detection | `scan_outdated`, `check_compatibility`, `get_upgrade_plan` |
| **git-rollback** | Git restore points and safe rollback | `create_restore_point`, `rollback`, `verify_consistency` |
| **finops-cost-estimator** | Per-run cost estimation and reporting | `estimate_workflow_cost`, `calculate_workflow_cost`, `get_cost_report`, `get_historical_baseline` |

All servers run via stdio transport. In CI: Python runtime in kiro-ci image. Locally: Docker containers from ECR (generated by `setup-kiro.sh`).

---

## 9. Audit Trail

| Event Type | When | Data |
|---|---|---|
| `workflow_start` | Pipeline begins | Issue key, workflow ID, pipeline ID |
| `inception_complete` | INCEPTION done | Stages executed/skipped, WF selected |
| `construction_start` | CONSTRUCTION begins | Delegation markers |
| `code-generation` | Code generated | Files modified, test count |
| `security-scan` | Scan complete | Finding counts by severity |
| `workflow_end` | Pipeline complete | MR URL, branch, checkpoint results |

**Traceability:** Jira issue → pipeline ID → `ai/{ISSUE_KEY}` branch → commit → MR → audit records (SHA-256 hash chain)

---

## 9.5 FinOps Cost Reporting

At the end of every workflow run, the agent calls `calculate_workflow_cost` and includes a cost breakdown in its final response. Costs are tracked across five dimensions:

| Dimension | Unit Price | Source |
|---|---|---|
| LLM Input Tokens | $0.003 / 1K tokens | Kiro-cli log parsing or compute-time estimation |
| LLM Output Tokens | $0.015 / 1K tokens | Kiro-cli log parsing or compute-time estimation |
| Compute Time | $0.00005 / sec | workflow_start → workflow_end timestamps |
| MCP Tool Calls | $0.0001 / call | tool_invocation events in audit log |
| Checkpoints | $0.001 / checkpoint | checkpoint records in audit log |

Unit prices are configured in `config/finops-cost-model.yml`. Reports are written to `reports/finops/` as JSON and Markdown. Historical baselines are maintained per workflow type to improve estimate accuracy over time.

Token estimation priority: (1) kiro-cli trace log (actual API counts), (2) manual injection, (3) compute-time estimation (duration × 40 tok/s).