# Expected Output Artifact Format

This document defines the expected output artifacts produced by the WF1 Requirement to Working Software workflow.

## Output Artifacts

### 1. Source Code

- Implementation files satisfying the input requirement
- Placed in the appropriate module directory within the target project
- Follows project coding conventions (naming, formatting, structure)
- All public functions, classes, and interfaces include docstrings or JSDoc comments
- No hardcoded secrets, dead code, or unused imports

### 2. Unit Tests

- Test files co-located with source or in the project's test directory
- Minimum 80% line coverage on new/modified code
- Cover core functional logic and important edge cases
- Use the project's test framework:
  - Python: pytest
  - Java: JUnit 5
  - Node JS: Jest
- Descriptive test names explaining what is being tested

### 3. Documentation

- Inline documentation: docstrings/JSDoc on all public APIs
- Inline comments on complex logic and non-obvious algorithms
- README updates when a new module or significant feature is added
- Feature description summarizing what was implemented and why

### 4. Kiro Spec

- `requirements.md` — Acceptance criteria derived from the input requirement
- `design.md` — Technical design decisions and component interfaces
- `tasks.md` — Implementation task list with traceability to requirements

### 5. Audit Trail

All workflow activity is logged to the audit-logger MCP in NDJSON format:

- **Interaction records**: Each AI interaction (input prompt + generated output)
- **Checkpoint records**: Each checkpoint result (pass/fail, validation details, metrics)
- **Event records**: Workflow start, workflow end, merge, and any rollback events

Each audit record includes: `workflow_id`, `initiator`, `timestamp`, and a SHA-256 content hash for tamper evidence.

## Directory Structure Example

```
target-project/
├── src/
│   └── <feature>/
│       ├── <implementation files>
│       └── <implementation files>
├── tests/
│   └── <feature>/
│       ├── <test files>
│       └── <test files>
├── docs/
│   └── <feature-description>.md  (if applicable)
└── .kiro/specs/<feature>/
    ├── requirements.md
    ├── design.md
    └── tasks.md
```
