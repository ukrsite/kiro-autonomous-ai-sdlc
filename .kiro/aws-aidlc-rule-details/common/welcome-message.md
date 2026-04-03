# AI-DLC Welcome Message

**Purpose**: This file contains the user-facing welcome message that should be displayed ONCE at the start of any AI-DLC workflow.

---

# 👋 Welcome to AI-DLC (AI-Driven Development Life Cycle)! 👋

I'll guide you through an adaptive software development workflow that intelligently tailors itself to your specific needs.

## What is AI-DLC?

AI-DLC is a structured yet flexible software development process that adapts to your project's needs. Think of it as having an experienced software architect who:

- **Analyzes your requirements** and asks clarifying questions when needed
- **Plans the optimal approach** based on complexity and risk
- **Automatically selects the right specialized workflow** (WF1–WF5) for implementation
- **Documents everything** so you have a complete record of decisions and rationale
- **Guides you through each phase** with clear checkpoints and approval gates

## The Integrated Lifecycle

```
                         User Request
                              |
                              v
        ╔═══════════════════════════════════════╗
        ║     INCEPTION PHASE                   ║
        ║     Planning & Requirements           ║
        ╠═══════════════════════════════════════╣
        ║ • Workspace Detection (ALWAYS)        ║
        ║ • Reverse Engineering (COND)          ║
        ║ • Requirements Analysis (ALWAYS)      ║
        ║ • User Stories (CONDITIONAL)          ║
        ║ • Workflow Planning + WF Selection    ║
        ║   (ALWAYS)                            ║
        ║ • Application Design (CONDITIONAL)    ║
        ║ • Units Generation (CONDITIONAL)      ║
        ╚═══════════════════════════════════════╝
                              |
                    Handoff Artifact
                    (workflow-handoff.md)
                              |
                              v
        ╔═══════════════════════════════════════╗
        ║     CONSTRUCTION PHASE                ║
        ║     Delegated to WF1-WF5              ║
        ╠═══════════════════════════════════════╣
        ║                                       ║
        ║  New Feature / Enhancement            ║
        ║  └─► WF1: Requirement to Software     ║
        ║       design + tasks + implement      ║
        ║       + checkpoints + docs + merge    ║
        ║                                       ║
        ║  Refactoring                          ║
        ║  └─► WF2: Autonomous Refactoring      ║
        ║       equivalence + benchmarking      ║
        ║                                       ║
        ║  Dependency Upgrade / Migration       ║
        ║  └─► WF3: Dependency Upgrades         ║
        ║       scan + compatibility + upgrade  ║
        ║                                       ║
        ║  Bug Fix                              ║
        ║  └─► WF4: Bug Fix                     ║
        ║       root cause + fix + regression   ║
        ║                                       ║
        ║  Documentation                        ║
        ║  └─► WF5: Documentation               ║
        ║       analysis + generation           ║
        ║                                       ║
        ╚═══════════════════════════════════════╝
                              |
                              v
        ╔═══════════════════════════════════════╗
        ║     OPERATIONS PHASE                  ║
        ║     Placeholder for Future            ║
        ╚═══════════════════════════════════════╝
```

## Phase Breakdown

**INCEPTION PHASE** - *Planning & Requirements*
- **Purpose**: Determines WHAT to build and WHY
- **Activities**: Workspace analysis, requirements gathering, automatic WF selection
- **Output**: Requirements doc, Handoff Artifact, delegation markers in aidlc-state.md
- **Your Role**: Answer questions, review requirements, approve direction

**CONSTRUCTION PHASE** - *Delegated to the right WF*
- **Purpose**: Determines HOW to build it — handled by the selected specialized workflow
- **WF1** (New Feature/Enhancement): Kiro spec workflow → design → tasks → implement → code review → test coverage → security scan → docs → merge
- **WF2** (Refactoring): Behavior equivalence analysis → refactor → benchmark → delta report
- **WF3** (Dependency Upgrades): Scan → compatibility check → upgrade → full test suite
- **WF4** (Bug Fix): Root cause analysis → fix → regression tests → side-effect analysis
- **WF5** (Documentation): Codebase analysis → generate docs, release notes, OpenAPI spec
- **Your Role**: Review generated design/tasks, validate checkpoint results

**OPERATIONS PHASE** - *Deployment & Monitoring (Future)*
- **Status**: Placeholder for future deployment and monitoring workflows

## WF1 Checkpoints (must all pass before merge)

```
  Code Review       Test Coverage      Security Scan
  (correctness,     (WF1: 80%,         (no HIGH or
   conventions,      WF2: 80%,          CRITICAL via
   no dead code)     WF3: 70%,          security-scanner
                     WF4: 90%,          MCP)
                     WF5: none)
```

## Key Principles

- ⚡ **Fully Adaptive**: INCEPTION depth scales to request complexity
- 🎯 **Auto WF Selection**: Workflow Planning classifies your request and picks WF1–WF5
- 📦 **Handoff Artifact**: Clean boundary between INCEPTION and CONSTRUCTION — no repeated planning
- 🔍 **Transparent**: You see and approve the execution plan and WF selection before work begins
- 📝 **Unified Audit Trail**: Complete trace across both INCEPTION and CONSTRUCTION phases
- 🔒 **Quality Gates**: All three checkpoints must pass before any merge

## What Happens Next

1. **Workspace analysis** — detect brownfield vs greenfield, load existing artifacts if present
2. **Requirements gathering** — clarifying questions if needed, then requirements doc
3. **WF selection** — Workflow Planning classifies your request and selects WF1–WF5
4. **You approve** — review the plan and WF selection (or override)
5. **Handoff** — INCEPTION produces `workflow-handoff.md` consumed by the selected WF
6. **CONSTRUCTION** — selected WF runs: design, implementation, checkpoints, docs, merge
7. **Complete** — working code, tests, docs, full audit trail

Let's begin!
