"""Configuration validator for the Jira-GitLab-Kiro integration pipeline.

Reads, validates, and resolves project mapping configuration from
``config/jira-project-mappings.yml``.  Enforces the schema contract
described in the design document:

* ``repo_path`` and ``target_branch`` are required and non-empty for every
  project entry (directly or via defaults).
* Every project entry must have a valid ``workflow`` identifier (directly
  or via defaults).
* Unknown project keys (not present in ``projects``) are rejected with a
  descriptive error.
* Default values are merged into project entries that omit optional fields.
* Coverage thresholds are mapped per workflow identifier.
"""

from __future__ import annotations

import os
from typing import Any

import yaml

VALID_WORKFLOWS: list[str] = [
    "wf1-requirement-to-software",
    "wf2-autonomous-refactoring",
    "wf3-dependency-upgrades",
    "wf4-bug-fix",
    "wf5-documentation",
    "auto",  # AI-DLC classifier selects WF at runtime
]

COVERAGE_THRESHOLDS: dict[str, int | None] = {
    "wf1-requirement-to-software": 80,
    "wf2-autonomous-refactoring": 80,
    "wf3-dependency-upgrades": 70,
    "wf4-bug-fix": 90,
    "wf5-documentation": None,
}

_REQUIRED_PROJECT_FIELDS = ("repo_path", "target_branch")
_DEFAULT_FIELDS = ("workflow", "agent", "trigger_status", "timeout_minutes")


def load_config(path: str) -> dict[str, Any]:
    """Read a YAML configuration file and return the parsed dictionary.

    Args:
        path: Filesystem path to the YAML configuration file.

    Returns:
        Parsed configuration as a dictionary.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If the file is empty or does not contain a valid YAML
            mapping.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError(
            f"Configuration file must contain a YAML mapping, "
            f"got {type(data).__name__}: {path}"
        )

    return data


def validate_config(config: dict[str, Any]) -> bool:
    """Validate a parsed project-mapping configuration.

    Supports two project entry formats:
    1. Flat: ``repo_path`` and ``target_branch`` directly on the entry.
    2. Multi-service: a ``services`` map with ``default_service`` key.
       Each service entry must have ``repo_path`` and ``target_branch``.

    Args:
        config: Parsed YAML configuration dictionary.

    Returns:
        ``True`` if the configuration is valid.

    Raises:
        ValueError: If the configuration is invalid, with a descriptive
            message listing all validation errors found.
    """
    errors: list[str] = []

    if not isinstance(config, dict):
        raise ValueError(f"Config must be a dict, got {type(config).__name__}")

    projects = config.get("projects")
    if not isinstance(projects, dict) or len(projects) == 0:
        raise ValueError("'projects' section is missing or empty")

    defaults = config.get("defaults") or {}

    for key, entry in projects.items():
        if not isinstance(entry, dict):
            errors.append(f"Project '{key}': entry must be a mapping")
            continue

        # Multi-service format
        if "services" in entry:
            services = entry["services"]
            if not isinstance(services, dict) or len(services) == 0:
                errors.append(f"Project '{key}': 'services' must be a non-empty mapping")
                continue
            default_svc = entry.get("default_service", "")
            if default_svc and default_svc not in services:
                errors.append(
                    f"Project '{key}': default_service '{default_svc}' "
                    f"not found in services: {list(services.keys())}"
                )
            for svc_name, svc_entry in services.items():
                if not isinstance(svc_entry, dict):
                    errors.append(f"Project '{key}'.services.{svc_name}: must be a mapping")
                    continue
                for field in _REQUIRED_PROJECT_FIELDS:
                    value = svc_entry.get(field) or defaults.get(field)
                    if not value or (isinstance(value, str) and not value.strip()):
                        errors.append(
                            f"Project '{key}'.services.{svc_name}: "
                            f"missing or empty required field '{field}'"
                        )
                workflow = svc_entry.get("workflow") or defaults.get("workflow")
                if not workflow or workflow not in VALID_WORKFLOWS:
                    errors.append(
                        f"Project '{key}'.services.{svc_name}: "
                        f"invalid or missing workflow '{workflow}'. "
                        f"Valid workflows: {VALID_WORKFLOWS}"
                    )
        else:
            # Flat format
            for field in _REQUIRED_PROJECT_FIELDS:
                value = entry.get(field) or defaults.get(field)
                if not value or (isinstance(value, str) and not value.strip()):
                    errors.append(
                        f"Project '{key}': missing or empty required field '{field}'"
                    )

            workflow = entry.get("workflow") or defaults.get("workflow")
            if not workflow or workflow not in VALID_WORKFLOWS:
                errors.append(
                    f"Project '{key}': invalid or missing workflow '{workflow}'. "
                    f"Valid workflows: {VALID_WORKFLOWS}"
                )

    if errors:
        raise ValueError(
            "Configuration validation failed:\n  - " + "\n  - ".join(errors)
        )

    return True


def resolve_project(
    config: dict[str, Any], project_key: str, service_name: str = ""
) -> dict[str, Any]:
    """Merge defaults with a project-specific entry and return the result.

    For multi-service projects (those with a ``services`` map), the
    *service_name* parameter selects which service to resolve. If omitted,
    the project's ``default_service`` is used.

    Args:
        config: Parsed and validated configuration dictionary.
        project_key: Jira project key to look up (e.g. ``"SAN"``).
        service_name: Service name within a multi-service project.
            Ignored for flat (single-service) project entries.

    Returns:
        A dictionary containing the fully resolved project configuration
        with defaults applied for any omitted optional fields.

    Raises:
        ValueError: If *project_key* is not found in the ``projects`` map,
            or if *service_name* is invalid for a multi-service project.
    """
    projects = config.get("projects") or {}

    if project_key not in projects:
        available = ", ".join(sorted(projects.keys())) if projects else "(none)"
        raise ValueError(
            f"Unknown project key '{project_key}'. "
            f"Available keys: {available}"
        )

    defaults = config.get("defaults") or {}
    entry = projects[project_key]

    # Resolve the effective entry (flat or from services map)
    if "services" in entry:
        services = entry["services"]
        svc_name = service_name or entry.get("default_service", "")
        if not svc_name or svc_name not in services:
            available = ", ".join(sorted(services.keys()))
            raise ValueError(
                f"Service '{svc_name}' not found in project '{project_key}'. "
                f"Available services: {available}"
            )
        effective = services[svc_name]
    else:
        effective = entry

    resolved: dict[str, Any] = {}

    for field in _REQUIRED_PROJECT_FIELDS:
        if field in effective and effective[field]:
            resolved[field] = effective[field]
        elif field in defaults and defaults[field]:
            resolved[field] = defaults[field]
        else:
            resolved[field] = effective.get(field, "")

    for field in _DEFAULT_FIELDS:
        if field in effective:
            resolved[field] = effective[field]
        elif field in defaults:
            resolved[field] = defaults[field]

    return resolved


def resolve_coverage_threshold(workflow_id: str) -> int | None:
    """Return the coverage threshold for a given workflow identifier.

    Args:
        workflow_id: A valid workflow identifier string.

    Returns:
        The coverage threshold as an integer, or ``None`` for workflows
        that skip coverage checks (e.g. ``wf5-documentation``).

    Raises:
        ValueError: If *workflow_id* is not a recognised workflow identifier.
    """
    if workflow_id not in COVERAGE_THRESHOLDS:
        raise ValueError(
            f"Invalid workflow identifier '{workflow_id}'. "
            f"Valid workflows: {VALID_WORKFLOWS}"
        )

    return COVERAGE_THRESHOLDS[workflow_id]
