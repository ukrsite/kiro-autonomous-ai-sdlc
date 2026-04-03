---
name: generate-documentation
description: Generates release notes, API changelog, OpenAPI spec, and architecture diagrams for AI-produced code changes. Invoked by WF1–WF4 after implementation, before merge.
metadata:
  author: sdlc-prototype-team
  version: "1.0.0"
---

# Generate Documentation for AI Changes

This shared skill produces documentation artifacts that accompany every AI-generated code change. It is invoked by workflow skills (WF1–WF4) after implementation is complete and all tests pass, but before the final merge/commit step.

## When to Invoke

Call this skill after:
- Code implementation is complete
- Unit tests are written and passing
- Security scan has no blocking findings

Call this skill before:
- Committing / pushing changes
- Creating the merge request

## Artifacts Produced

| Artifact | File | Description |
|----------|------|-------------|
| Release Notes | `docs/release-notes-{ISSUE_KEY}.md` | Summary of changes, test results, security status |
| API Changelog | `docs/CHANGELOG.md` (append) | Added/Changed/Deprecated/Removed endpoints |
| OpenAPI Spec | `docs/openapi.yaml` (create or update) | OpenAPI 3.0 spec for REST endpoints |
| Architecture Diagram | `docs/architecture.md` | Mermaid diagram of service components |

All files are placed in the `docs/` directory of the target service.

## Workflow Steps

### 1. Analyze Changes

Scan the modified source files to identify:
- New or modified REST endpoints (FastAPI decorators, Spring `@RequestMapping`, Express routes)
- New or modified Pydantic/DTO models (request/response schemas)
- New modules, classes, or public functions
- Dependency changes (requirements.txt, pom.xml, package.json)
- Database model changes

### 2. Generate Release Notes

Create `docs/release-notes-{ISSUE_KEY}.md` following the template in `references/output-templates.md`:
- Issue key, summary, workflow, date, branch name (`workflow/{WORKFLOW}/{issue_key_lower}`)
- List of files modified with brief description of each change
- API changes table (method, endpoint, description, status)
- Test results summary (passed/failed counts, coverage percentage)
- Security scan summary
- Rollback instructions

### 3. Generate API Changelog Entry

If REST endpoints were added, changed, or removed:
- Append an entry to `docs/CHANGELOG.md` (create if it doesn't exist)
- Use Keep a Changelog format: Added / Changed / Deprecated / Removed
- Each entry: `{METHOD} {path}` with brief description
- Include the issue key and date as the section header

### 4. Generate or Update OpenAPI Spec

If the service exposes REST endpoints:
- Create or update `docs/openapi.yaml` following OpenAPI 3.0.3 standard
- See `references/openapi-standards.md` for field requirements
- Extract endpoints from route decorators/annotations
- Extract request/response schemas from model classes
- Include operation IDs, descriptions, parameter types, response codes
- Validate the generated YAML is syntactically correct

### 5. Generate Architecture Diagram

Create or update `docs/architecture.md` with a Mermaid diagram:
- Show the service and its endpoints
- Show external dependencies (HTTP clients, databases, message queues)
- Show internal module relationships if multiple modules exist
- Keep diagrams under 15 nodes; split into multiple diagrams if larger
- Include an endpoint summary table below the diagram

## Output Quality Requirements

- All file paths referenced in docs must exist in the codebase
- All API signatures in docs must match actual source code
- OpenAPI spec must be valid YAML and conform to OpenAPI 3.0.3
- Mermaid diagrams must render correctly (valid syntax)
- Release notes must include all files that were actually modified
- Changelog entries must not duplicate existing entries

## Language-Specific Endpoint Detection

| Language | Framework | Pattern |
|----------|-----------|---------|
| Python | FastAPI | `@app.get(`, `@app.post(`, `@router.get(` etc. |
| Python | Flask | `@app.route(`, `@blueprint.route(` |
| Java | Spring | `@GetMapping`, `@PostMapping`, `@RequestMapping` |
| JavaScript | Express | `app.get(`, `router.post(`, `app.use(` |
| TypeScript | NestJS | `@Get(`, `@Post(`, `@Controller(` |

## Language-Specific Model Detection

| Language | Framework | Pattern |
|----------|-----------|---------|
| Python | Pydantic | `class Foo(BaseModel):` |
| Python | dataclass | `@dataclass` |
| Java | Spring | Classes in `dto/`, `model/` packages |
| TypeScript | NestJS | `class FooDto`, interfaces in `dto/` |

## References

- [output-templates.md](references/output-templates.md) — Template formats for all artifacts
- [openapi-standards.md](references/openapi-standards.md) — OpenAPI generation rules
