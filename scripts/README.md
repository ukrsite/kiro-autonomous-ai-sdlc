# Scripts

Utility and setup scripts for the Kiro Autonomous AI SDLC pipeline.

## Shell Scripts

| Script | Purpose |
|--------|---------|
| `setup-kiro.sh` | Verifies kiro-cli, agent configs, and MCP servers. Generates `.kiro/settings/mcp.json` with stdio (CI) or Docker (local) transport. |
| `retry-wrapper.sh` | Wraps a command with 3 retries and exponential backoff (10s → 20s → 40s). Used for kiro-cli calls in CI. |
| `generate-docs.sh` | Deterministic documentation generator (fallback). Produces release notes, API changelog entry, Mermaid architecture diagram, and OpenAPI spec by parsing source code for route decorators and Pydantic models. Called by `finalize` stage. |
| `setup-sandbox.sh` | Sandbox environment setup helper. |
| `install-mcp-servers.sh` | Installs Python dependencies for all MCP servers. |
| `cron-triggers.sh` | Helper for scheduled pipeline triggers. |

## Validation Modules (`scripts/validation/`)

Testable Python modules extracted from pipeline inline scripts. Each module handles a single concern and is importable for unit testing.

| Module | Purpose |
|--------|---------|
| `config_validator.py` | Loads and validates `config/jira-project-mappings.yml`. Resolves project keys to service configs with defaults merging. Supports flat and multi-service project entries. |
| `check_coverage.py` | Parses `coverage.xml` and checks line coverage threshold. When `CHANGED_SRC_FILES` is set, measures coverage only on changed files (not total repo). Called by `checkpoint-gates:python-tests`. |
| `issue_key_validator.py` | Validates Jira issue key format (`^[A-Z][A-Z0-9]+-[0-9]+$`). |
| `sanitizer.py` | Escapes shell metacharacters, strips HTML tags, truncates input. Used to sanitize Jira content before passing to kiro-cli. |
| `exit_code_handler.py` | Classifies process exit codes (0 = success, non-zero = failure with category). |
| `branch_naming.py` | Generates feature branch names (`workflow/{WORKFLOW}/{issue_key_lower}`). |
| `merge_request.py` | Builds merge request metadata (title, description, labels). |
| `jira_status.py` | Jira status transition logic and comment builder. |
| `audit_records.py` | Builds audit record dictionaries for workflow start/end and checkpoint events. |
| `checkpoint_gates.py` | Evaluates coverage, security, and code review gate pass/fail. |
| `pipeline_summary.py` | Builds the `finalize-output/pipeline-summary.json` artifact. |

### Environment Variables for `check_coverage.py`

| Variable | Required | Description |
|----------|----------|-------------|
| `COVERAGE_XML` | No | Path to coverage.xml (default: `coverage.xml`) |
| `COVERAGE_THRESHOLD` | Yes | Minimum line coverage percentage (e.g. `80`) |
| `CHANGED_SRC_FILES` | No | Newline-separated list of changed source file paths. If set, coverage is measured only on these files. |
| `REPO_PATH` | No | Service path prefix to strip from file paths (e.g. `services/python-processor`) |
