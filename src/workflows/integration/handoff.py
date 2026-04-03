"""Handoff Artifact Generator for AI-DLC Workflow Integration.

Generates, writes, parses, and validates the Handoff Artifact that bridges
INCEPTION and CONSTRUCTION phases. The artifact is stored at
``aidlc-docs/inception/plans/workflow-handoff.md`` and contains references
(not duplicated content) to INCEPTION outputs.

Requirements: 1.2, 1.4, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

from __future__ import annotations

import os
import re
from typing import Optional

from src.workflows.integration.models import (
    ClassificationResult,
    DelegationMarker,
    IntentAnalysis,
)

_DEFAULT_HANDOFF_PATH = "aidlc-docs/inception/plans/workflow-handoff.md"

_REQUIREMENTS_REF = "aidlc-docs/inception/requirements/requirements.md"
_REQUIREMENTS_VERIFICATION_REF = (
    "aidlc-docs/inception/requirements/requirement-verification-questions.md"
)

_REVERSE_ENGINEERING_REFS: dict[str, str] = {
    "Architecture": "aidlc-docs/inception/reverse-engineering/architecture.md",
    "Code Structure": "aidlc-docs/inception/reverse-engineering/code-structure.md",
    "Component Inventory": "aidlc-docs/inception/reverse-engineering/component-inventory.md",
    "Technology Stack": "aidlc-docs/inception/reverse-engineering/technology-stack.md",
    "API Documentation": "aidlc-docs/inception/reverse-engineering/api-documentation.md",
}

_REQUIRED_SECTIONS = (
    "selected_workflow",
    "intent_analysis",
    "requirements_reference",
    "inception_stages",
    "delegated_stages",
)


def generate_handoff_artifact(
    classification: ClassificationResult,
    intent: IntentAnalysis,
    inception_stages: list[dict[str, str]],
    delegated_stages: list[DelegationMarker],
    override: Optional[dict[str, str]] = None,
) -> str:
    """Generate the Handoff Artifact markdown content.

    Produces the full markdown content for the Handoff Artifact that bridges
    INCEPTION and CONSTRUCTION. The artifact references (not duplicates)
    INCEPTION outputs such as requirements and reverse engineering docs.

    Args:
        classification: The classification result from Workflow Planning,
            containing request type, selected WF, confidence, and rationale.
        intent: The intent analysis summary from Requirements Analysis,
            containing request clarity, scope estimate, and complexity estimate.
        inception_stages: A list of dicts, each with keys ``stage_name``,
            ``status``, and ``completed_at`` (ISO 8601 timestamp or ``"N/A"``).
        delegated_stages: A list of :class:`DelegationMarker` instances
            indicating which CONSTRUCTION stages are delegated to the WF.
        override: An optional dict with keys ``original_wf``, ``override_to``,
            and ``override_rationale`` if the user overrode the WF selection.

    Returns:
        A string containing the complete Handoff Artifact in markdown format.
    """
    lines: list[str] = []

    # Title
    lines.append("# Workflow Handoff Artifact")
    lines.append("")

    # Selected Workflow section
    lines.append("## Selected Workflow")
    lines.append(f"- **Workflow**: {classification.selected_wf.value}")
    lines.append(f"- **Request Type**: {classification.request_type.value}")
    lines.append(f"- **Confidence**: {classification.confidence.value}")
    lines.append(f"- **Classification Rationale**: {classification.rationale}")
    lines.append("")

    # Intent Analysis Summary section
    lines.append("## Intent Analysis Summary")
    lines.append(f"- **Request Clarity**: {intent.request_clarity}")
    lines.append(f"- **Scope Estimate**: {intent.scope_estimate}")
    lines.append(f"- **Complexity Estimate**: {intent.complexity_estimate}")
    lines.append("")

    # Requirements Reference section (file paths, not content)
    lines.append("## Requirements Reference")
    lines.append(f"- **Full Requirements**: {_REQUIREMENTS_REF}")
    lines.append(
        f"- **Verification Questions**: {_REQUIREMENTS_VERIFICATION_REF}"
    )
    lines.append("")

    # Reverse Engineering References section (file paths, not content)
    lines.append("## Reverse Engineering References")
    for label, path in _REVERSE_ENGINEERING_REFS.items():
        lines.append(f"- **{label}**: {path}")
    lines.append("")

    # INCEPTION Stages Executed section
    lines.append("## INCEPTION Stages Executed")
    lines.append("| Stage | Status | Completed At |")
    lines.append("|---|---|---|")
    for stage in inception_stages:
        name = stage.get("stage_name", "")
        status = stage.get("status", "")
        completed_at = stage.get("completed_at", "N/A")
        lines.append(f"| {name} | {status} | {completed_at} |")
    lines.append("")

    # Delegated CONSTRUCTION Stages section
    lines.append("## Delegated CONSTRUCTION Stages")
    lines.append("| Stage | Delegation Status |")
    lines.append("|---|---|")
    for marker in delegated_stages:
        lines.append(
            f"| {marker.stage_name} | delegated to {marker.wf_id.value} |"
        )
    lines.append("")

    # User Override section (only if applicable)
    if override is not None:
        lines.append("## User Override")
        lines.append(
            f"- **Original Selection**: {override.get('original_wf', '')}"
        )
        lines.append(
            f"- **Override To**: {override.get('override_to', '')}"
        )
        lines.append(
            f"- **Override Rationale**: {override.get('override_rationale', '')}"
        )
        lines.append("")

    return "\n".join(lines)


def write_handoff_artifact(
    content: str,
    path: str = _DEFAULT_HANDOFF_PATH,
) -> None:
    """Write the Handoff Artifact content to disk.

    Creates parent directories if they do not exist and writes the
    markdown content to the specified path.

    Args:
        content: The markdown string produced by
            :func:`generate_handoff_artifact`.
        path: Destination file path. Defaults to
            ``aidlc-docs/inception/plans/workflow-handoff.md``.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


# ---------------------------------------------------------------------------
# Section heading patterns used by the parser
# ---------------------------------------------------------------------------

_SECTION_MAP: dict[str, str] = {
    "Selected Workflow": "selected_workflow",
    "Intent Analysis Summary": "intent_analysis",
    "Requirements Reference": "requirements_reference",
    "Reverse Engineering References": "reverse_engineering_references",
    "INCEPTION Stages Executed": "inception_stages",
    "Delegated CONSTRUCTION Stages": "delegated_stages",
    "User Override": "user_override",
}

_HEADING_RE = re.compile(r"^##\s+(.+)$")


def parse_handoff_artifact(path: str) -> dict[str, str]:
    """Read and parse a Handoff Artifact markdown file.

    Splits the file into sections keyed by the normalised section names
    defined in :data:`_SECTION_MAP`.  Each value is the raw markdown text
    of that section (excluding the heading line itself).

    Args:
        path: File path to the Handoff Artifact markdown file.

    Returns:
        A dict with keys ``selected_workflow``, ``intent_analysis``,
        ``requirements_reference``, ``reverse_engineering_references``,
        ``inception_stages``, ``delegated_stages``, and ``user_override``.
        Missing sections are omitted from the dict.
    """
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()

    sections: dict[str, list[str]] = {}
    current_key: Optional[str] = None

    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            heading = match.group(1).strip()
            current_key = _SECTION_MAP.get(heading)
            if current_key is not None:
                sections[current_key] = []
            continue
        if current_key is not None:
            sections[current_key].append(line)

    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def validate_handoff_artifact(
    parsed: dict[str, str],
) -> tuple[bool, list[str]]:
    """Validate that a parsed Handoff Artifact contains all required sections.

    Required sections are: ``selected_workflow``, ``intent_analysis``,
    ``requirements_reference``, ``inception_stages``, and ``delegated_stages``.
    The ``reverse_engineering_references`` and ``user_override`` sections are
    optional.

    Args:
        parsed: A dict returned by :func:`parse_handoff_artifact`.

    Returns:
        A tuple of ``(is_valid, missing_sections)`` where *is_valid* is
        ``True`` when all required sections are present and non-empty, and
        *missing_sections* lists the keys of any absent or empty sections.
    """
    missing: list[str] = []
    for section in _REQUIRED_SECTIONS:
        if not parsed.get(section):
            missing.append(section)
    return (len(missing) == 0, missing)
