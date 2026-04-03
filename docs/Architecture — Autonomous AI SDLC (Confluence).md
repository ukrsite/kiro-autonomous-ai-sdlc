# Architecture — Autonomous AI Software Development Lifecycle

> **Status:** Live | **Last Updated:** 2026-03-31 | **Owner:** GenAI Innovation Team

This system transforms natural language requirements (Jira tickets) into working, tested, documented code — delivered as merge requests — with full audit trails and safety guardrails.

The architecture uses [Kiro](https://kiro.dev) native primitives (Skills, Steering, Hooks, Agents, MCP servers) with AI-DLC (AI-Driven Development Lifecycle) for structured requirements-to-code execution. No custom workflow engine is required.

> **Key URLs:**
> - Jira: [https://test.genai-innovation.ericsson.net/jira-ai-dlc/](https://test.genai-innovation.ericsson.net/jira-ai-dlc/)
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

```mermaid
graph TB
    subgraph PATHA["Path A — Kiro IDE (Development)"]
        DEV["Developer"] <-->|"interactive chat"| KIRO["Kiro IDE / kiro-cli"]
    end

    subgraph PATHB["Path B — CI Pipeline (Production)"]
        JIRA["Jira Issue"] -->|"webhook"| GITLAB["GitLab CI"]
        GITLAB -->|"kiro-cli --no-interactive"| KIROCI["kiro-cli (headless)"]
        KIROCI -->|"MR"| SANDBOX_B["kiro-sandbox"]
    end

    subgraph SHARED["Shared Layer"]
        SKILLS["Skills (WF1-WF5)"]
        STEERING["Steering (guardrails)"]
        RULES["AI-DLC Rule Details"]
        MCP["MCP Servers"]
        AUDIT["Audit Logger"]
    end

    KIRO --> SHARED
    KIROCI --> SHARED

    style PATHA fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style PATHB fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style SHARED fill:#fff9c4,stroke:#f57f17,stroke-width:2px
```

---

## 2. Architecture

### 2.1 Two-Repository Model

| Repository | Purpose |
|---|---|
| **kiro-autonomous-ai-sdlc** | Orchestration — pipeline, agents, skills, steering, MCP servers, AI-DLC rules |
| **kiro-sandbox** | Application code — services modified by the AI, plus AI-DLC artifacts |

```mermaid
graph TB
    subgraph ORCH["kiro-autonomous-ai-sdlc (Orchestration)"]
        direction TB
        SKILLS2[".kiro/skills/ — WF1-WF5 SKILL.md"]
        STEERING2[".kiro/steering/ — security, coding standards, sandbox"]
        RULES2[".kiro/aws-aidlc-rule-details/ — common, construction, inception"]
        AGENTS2["agents/ — developer.json, devops.json"]
        MCP2["mcp-servers/ — audit-logger, security-scanner, dependency-scanner, git-rollback"]
        PIPELINE2[".gitlab-ci-workflow.yml"]
    end

    subgraph SANDBOX2["kiro-sandbox (Application Code)"]
        direction TB
        JAVA2["services/java-api — Spring Boot 3.2.3, Java 21"]
        PYTHON2["services/python-processor — FastAPI, Python 3.12"]
        NODE2["services/node-gateway — Express, Node 20"]
        AIDLC2["aidlc-docs/ — AI-DLC artifacts"]
    end

    PIPELINE2 -->|"clone → modify → push → MR"| SANDBOX2

    style ORCH fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style SANDBOX2 fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
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

```mermaid
graph TB
    subgraph ENTRY["Entry Points"]
        IDE["Kiro IDE (interactive)"]
        CLI["kiro-cli (headless CI)"]
    end

    subgraph AIDLC["AI-DLC Lifecycle"]
        INCEPTION["INCEPTION — Workspace Detection → Requirements → Planning"]
        CONSTRUCTION["CONSTRUCTION — Code Generation → Build & Test → Docs"]
        INCEPTION -->|"Handoff Artifact"| CONSTRUCTION
    end

    subgraph GUARDRAILS["Guardrails Layer"]
        SEC["security-rules.md"]
        CODE["coding-standards.md"]
        SAND["sandbox-boundaries.md"]
        LANG["java / python / nodejs guardrails"]
    end

    subgraph MCPSERVERS["MCP Servers"]
        AL["audit-logger — SHA-256 hash chain"]
        SS["security-scanner — bandit + safety"]
        DS["dependency-scanner — outdated + CVE"]
        GR["git-rollback — restore points"]
    end

    subgraph SANDBOX3["kiro-sandbox"]
        SVC["services/ — java-api, python-processor, node-gateway"]
    end

    IDE --> AIDLC
    CLI --> AIDLC
    AIDLC --> GUARDRAILS
    AIDLC --> MCPSERVERS
    CONSTRUCTION -->|"code + tests + docs"| SANDBOX3

    style ENTRY fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style AIDLC fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style GUARDRAILS fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    style MCPSERVERS fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
```

---

## 3. AI-DLC Lifecycle

AI-DLC (AI-Driven Development Lifecycle) is a structured two-phase process that adapts to request complexity.

```mermaid
flowchart LR
    subgraph INCEPTION["INCEPTION — what to build"]
        direction TB
        WD["Workspace Detection — ALWAYS"]
        RE["Reverse Engineering — CONDITIONAL"]
        RA["Requirements Analysis — ALWAYS"]
        US["User Stories — CONDITIONAL"]
        WP["Workflow Planning — ALWAYS"]
        AD["Application Design — CONDITIONAL"]
        UG["Units Generation — CONDITIONAL"]
        WD --> RE --> RA --> US --> WP --> AD --> UG
    end

    HANDOFF["Handoff Artifact"]

    subgraph CONSTRUCTION["CONSTRUCTION — how to build it"]
        direction TB
        FD["Functional Design — CONDITIONAL"]
        CG["Code Generation — ALWAYS"]
        BT["Build and Test — ALWAYS"]
        DOC["Documentation — ALWAYS"]
        FD --> CG --> BT --> DOC
    end

    INCEPTION --> HANDOFF --> CONSTRUCTION

    style INCEPTION fill:#bbdefb,stroke:#1565c0,stroke-width:2px
    style CONSTRUCTION fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style HANDOFF fill:#fff9c4,stroke:#f57f17,stroke-width:2px
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

```mermaid
flowchart LR
    REQ["Parse Requirement"]
    SPEC["Create Kiro Spec"]
    RP["Create Restore Point"]
    IMPL["Implement Tasks"]
    CR["Code Review ✓"]
    COV["Test Coverage ✓ ≥80%"]
    SEC["Security Scan ✓"]
    DOCS["Generate Docs"]
    MR["Merge"]

    REQ --> SPEC --> RP --> IMPL --> CR --> COV --> SEC --> DOCS --> MR

    style CR fill:#fff9c4,stroke:#f57f17
    style COV fill:#fff9c4,stroke:#f57f17
    style SEC fill:#fff9c4,stroke:#f57f17
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

```mermaid
flowchart LR
    JIRA3["Jira Issue — Ready for AI Dev"]
    WEBHOOK3["Jira Automation Webhook"]

    subgraph PIPELINE3["GitLab CI Pipeline"]
        direction LR
        V3["validate"]
        EW3["execute-workflow — kiro-cli in sandbox/"]

        subgraph GATES["checkpoint-gates (parallel)"]
            JT3["java-tests"]
            PT3["python-tests"]
            SS3["security-scan"]
            RV3["review"]
        end

        FIN3["finalize — push + MR + Jira"]

        V3 --> EW3 --> GATES --> FIN3
    end

    JIRA3 --> WEBHOOK3 --> PIPELINE3
    FIN3 --> MR3["MR on kiro-sandbox — ai/ISSUE_KEY"]

    style PIPELINE3 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style GATES fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1px
```

### 5.2 Pipeline Stages

| Stage | Image | Purpose |
|---|---|---|
| **validate** | kiro-ci | Resolve Jira project → service → workflow → coverage threshold |
| **execute-workflow** | kiro-ci | Clone kiro-sandbox, `cd sandbox`, run AI-DLC via kiro-cli |
| **java-tests** | maven:3.9-eclipse-temurin-21 | `mvn verify` + JaCoCo coverage |
| **python-tests** | python:3.12-slim | `pytest --cov` with per-file coverage |
| **security-scan** | python:3.12-slim | `bandit` + `safety` (blocks on HIGH/CRITICAL) |
| **review** | kiro-ci | AI-assisted code review via kiro-cli |
| **finalize** | kiro-ci | Push branch, create MR, transition Jira |
| **on-failure** | kiro-ci | Transition Jira to "AI Dev Failed" |

### 5.3 End-to-End Sequence

```mermaid
sequenceDiagram
    actor PO as Product Owner
    participant JIRA4 as Jira (EKS)
    participant GL4 as GitLab CI
    participant KIRO4 as kiro-cli
    participant SANDBOX4 as kiro-sandbox

    PO->>JIRA4: Create issue + set SERVICE_NAME
    PO->>JIRA4: Transition to "Ready for AI Dev"
    JIRA4->>GL4: Webhook POST (issue key, summary, service)
    GL4->>GL4: validate (resolve config)
    GL4->>SANDBOX4: clone kiro-sandbox.git
    GL4->>KIRO4: execute-workflow (AI-DLC)
    KIRO4->>SANDBOX4: write code + tests + docs
    GL4->>GL4: checkpoint-gates (parallel)
    GL4->>SANDBOX4: push ai/ISSUE_KEY, create MR
    GL4->>JIRA4: transition to "In Review"
    PO->>SANDBOX4: review MR
```

### 5.4 Retry and Recovery

| Layer | Mechanism | Detail |
|---|---|---|
| kiro-cli | `retry-wrapper.sh` | 3 retries, exponential backoff |
| GitLab job | `retry: max: 2` | Runner crashes, network timeouts |
| MR creation | HTTP 409 handler | Fetches existing MR URL |
| Rollback | `git-rollback` MCP | Restore point before implementation |

---

## 6. Jira Instance — AWS EKS

A dedicated Jira instance serves as the issue tracking frontend for the AI-DLC pipeline.

> **URL:** [https://test.genai-innovation.ericsson.net/jira-ai-dlc/](https://test.genai-innovation.ericsson.net/jira-ai-dlc/)

```mermaid
graph TB
    USER6["Developer / PO"] -->|"browser"| INGRESS6["AWS ALB Ingress — test.genai-innovation.ericsson.net"]
    INGRESS6 -->|"/jira-ai-dlc/"| JIRA6["Jira Pod — AWS EKS"]
    JIRA6 -->|"Automation webhook"| GITLAB6["GitLab Pipeline Trigger API"]
    GITLAB6 -->|"pipeline"| RUNNER6["GitLab Runner (EKS)"]
    RUNNER6 -->|"clone + push + MR"| SANDBOX6["kiro-sandbox.git"]
    RUNNER6 -->|"REST API"| JIRA6

    subgraph EKS6["AWS EKS Cluster"]
        JIRA6
        RUNNER6
    end

    style EKS6 fill:#fff3e0,stroke:#e65100,stroke-width:2px
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

```mermaid
flowchart TD
    GEN["Code generated by LLM"]
    AUTO["Automated checkpoint — compile + lint + test"]
    SEC7["Security scan — bandit + safety"]
    REVIEW7["Code review — AI-assisted"]
    MR7["Create MR"]
    RETRY7["Retry with error context — max 2x"]
    FAIL7["Workflow STOPS"]

    GEN --> AUTO
    AUTO -->|"pass"| SEC7
    AUTO -->|"fail"| RETRY7
    RETRY7 -->|"pass"| SEC7
    RETRY7 -->|"still failing"| FAIL7
    SEC7 -->|"pass"| REVIEW7
    SEC7 -->|"HIGH/CRITICAL"| FAIL7
    REVIEW7 -->|"approved"| MR7

    style FAIL7 fill:#ffcdd2,stroke:#c62828
    style MR7 fill:#c8e6c9,stroke:#2e7d32
```

---

## 8. MCP Servers

| Server | Purpose | Key Tools |
|---|---|---|
| **audit-logger** | Tamper-evident logging (SHA-256 hash chain) | `log_interaction`, `log_checkpoint`, `log_event`, `query_audit` |
| **security-scanner** | Static analysis + dependency CVE scanning | `scan_code`, `scan_dependencies`, `get_scan_report` |
| **dependency-scanner** | Outdated dependency detection | `scan_outdated`, `check_compatibility`, `get_upgrade_plan` |
| **git-rollback** | Git restore points and safe rollback | `create_restore_point`, `rollback`, `verify_consistency` |

All servers run via stdio transport. In CI: Python runtime in kiro-ci image. Locally: project virtual environment.

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

## 10. Service Configuration

```yaml
# config/jira-project-mappings.yml
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

Set `SERVICE_NAME` custom field on the Jira issue. Falls back to `default_service` if empty.

---

## 11. CI Runner Image

`docker/kiro-ci/Dockerfile` — multi-language image:

| Component | Version | Purpose |
|---|---|---|
| **Python** | 3.12 | kiro-cli, MCP servers, bandit, safety, pytest |
| **OpenJDK** | 21 | Java service compilation and testing |
| **Maven** | 3.9 | Java build tool |
| **Node.js** | 20 LTS | Node service compilation and testing |
| **kiro-cli** | latest | AI workflow execution |

---

## 12. Sandbox Application

Multi-service demo application in `kiro-sandbox`:

| Service | Stack | Port | Purpose |
|---|---|---|---|
| **java-api** | Spring Boot 3.2.3 / Java 21 / H2 | 8088 | User CRUD REST API |
| **python-processor** | FastAPI / Python 3.12 | 5000 | Data processing and reports |
| **node-gateway** | Express / Node 20 | 3000 | API gateway |

---

## 13. Required CI/CD Variables

| Variable | Description |
|---|---|
| `GL_TOKEN` | GitLab token with `api`, `read_repository`, `write_repository` on kiro-sandbox |
| `JIRA_ETEAM_TOKEN` | Jira PAT for REST API (transitions, comments) |
| `PIPELINE_TRIGGER_TOKEN` | GitLab pipeline trigger token (Jira Automation) |

---

## 14. Evolution: AgentCore → Kiro Native

```mermaid
graph LR
    subgraph PHASE1["Phase 1 — AgentCore (Week 1)"]
        P1A["Custom WorkflowEngine"]
        P1B["YAML step definitions"]
        P1C["Direct Bedrock calls"]
    end

    subgraph PHASE2["Phase 2 — Strands Migration (Week 2)"]
        P2A["+ Strands SDK adapter"]
        P2B["+ Multi-agent patterns"]
        P2C["+ Ollama local dev"]
    end

    subgraph PHASE3["Phase 3 — Kiro Native (Week 3)"]
        P3A["Skills + Steering + Hooks"]
        P3B["AI-DLC lifecycle"]
        P3C["kiro-cli in GitLab CI"]
        P3D["Zero custom engine"]
    end

    PHASE1 --> PHASE2 --> PHASE3

    style PHASE1 fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    style PHASE2 fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    style PHASE3 fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
```

| Dimension | AgentCore (Week 1-2) | Kiro Native (Week 3) |
|---|---|---|
| Workflow definition | Custom YAML steps | SKILL.md files |
| Guardrails | `guardrails/*.yaml` | Steering files (.md) |
| Triggers | Custom webhook handler | Jira Automation + GitLab triggers |
| LLM integration | Custom `LLMClient` + Strands adapter | kiro-cli (built-in) |
| Tool integration | `@tool` Python functions | MCP servers (stdio) |
| CI execution | `agentcore run --mode ci` | `kiro-cli chat --no-interactive` |
| Custom code | ~5,000+ lines | ~0 (pipeline YAML + config) |

---

## 15. Key Design Decisions

| Decision | Rationale |
|---|---|
| Two-repo model | Clean separation: pipeline config never mixed with application code |
| AI-DLC two-phase lifecycle | INCEPTION (what) and CONSTRUCTION (how) with explicit handoff |
| Kiro primitives over custom engine | Zero maintenance, declarative, version-controlled |
| MCP servers over custom tools | Standard protocol, stdio transport, reusable |
| Parallel checkpoint gates | Faster feedback, clearer failure isolation |
| `cd sandbox` before kiro-cli | All file writes land in the correct repository |
| Conventional commits | `feat({ISSUE_KEY}): {summary}` for traceability |
| Verbosity mode | `silent` for CI, `debug` for interactive |

---

## 16. Links

| Resource | URL |
|---|---|
| **Jira Instance** | [https://test.genai-innovation.ericsson.net/jira-ai-dlc/](https://test.genai-innovation.ericsson.net/jira-ai-dlc/) |
| **Orchestration Repo** | [kiro-autonomous-ai-sdlc](https://gitlab.internal.ericsson.com/san-tools-technology-platform/genai-innovation/ai-streams/developer/kiro-autonomous-ai-sdlc) |
| **Sandbox Repo** | [kiro-sandbox](https://gitlab.internal.ericsson.com/san-tools-technology-platform/genai-innovation/ai-streams/developer/kiro-sandbox) |
| **Week 3 Report** | [Mandate-Progress-Report-Week3.md](Mandate-Progress-Report-Week3.md) |
| **Kiro Docs** | [https://kiro.dev/docs](https://kiro.dev/docs) |
