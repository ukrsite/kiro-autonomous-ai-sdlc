---
inclusion: fileMatch
globs:
  - "**/*.py"
---

# Python Guardrails

## Coding Standards

1. **Naming conventions**: snake_case for functions, variables, and modules. PascalCase for classes. UPPER_SNAKE_CASE for constants.
2. **Formatting**: Use ruff format (or black). 4-space indentation, 88-character line length.
3. **Type hints**: Use type annotations on all public function signatures. Use `from __future__ import annotations` for forward references.
4. **Imports**: Group imports in order: stdlib, third-party, local. Use absolute imports. Remove unused imports.
5. **Docstrings**: Use Google-style docstrings for all public functions, classes, and modules.

## Linting and Static Analysis

1. **Linter**: ruff (replaces flake8, isort, pyflakes). Configure in `pyproject.toml`.
2. **Type checker**: mypy with strict mode for MCP servers and core modules.
3. **Formatter**: ruff format (applied before commit).
4. **Security scanner**: bandit for static security analysis.

## Security Patterns

1. **Input validation**: Validate all external input. Use Pydantic models for structured data validation.
2. **SQL injection**: Use parameterized queries with DB-API 2.0 (`cursor.execute(query, params)`). Never use f-strings or `%` formatting for SQL.
3. **Subprocess calls**: Use `subprocess.run` with a list of arguments. Never use `shell=True` with untrusted input.
4. **Deserialization**: Never use `pickle.load` or `yaml.load` on untrusted data. Use `yaml.safe_load`.
5. **Dependency security**: Run `bandit -r .` and `safety check` before merge. Block on HIGH/CRITICAL findings.
6. **Secrets**: Never hardcode secrets. Use environment variables or a secrets manager.
7. **Path traversal**: Validate and sanitize file paths. Use `pathlib.Path.resolve()` and check against allowed directories.

## Testing Conventions

1. **Framework**: pytest for unit and integration tests.
2. **Property-based testing**: Hypothesis for property-based tests.
3. **Test location**: `tests/` directory mirroring source structure, or co-located `test_*.py` files.
4. **Naming**: Test files prefixed with `test_`. Test functions prefixed with `test_`. Use descriptive names.
5. **Coverage**: Minimum 80% line coverage on new code (WF1/WF2). Run via `pytest --cov`.
