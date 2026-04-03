---
name: delta-report-generator
description: Generates delta reports comparing before/after states of code changes. Used by WF2, WF3, and WF5 workflows.
metadata:
  author: sdlc-prototype-team
  version: "1.0.0"
---

# Delta Report Generator

This shared skill generates structured JSON delta reports that compare git snapshots (before/after commit hashes) and calculate metrics. It is used by WF2 (Autonomous Refactoring), WF3 (Dependency Upgrades), and WF5 (Documentation) workflows.

## Purpose

After a workflow applies changes to the codebase, this skill compares the before and after states to produce a comprehensive delta report. The report captures what changed, how much changed, and whether quality metrics improved or degraded.

## Usage

Run the delta report generator script with before and after git commit hashes:

```bash
python skills/shared-skills/delta-report-generator/scripts/generate_delta_report.py \
  --repo-path . \
  --before-commit <before_commit_hash> \
  --after-commit <after_commit_hash> \
  --workflow-id <workflow_id> \
  --test-command "pytest --tb=short -q" \
  --output delta-report.json
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--repo-path` | Yes | Path to the git repository root |
| `--before-commit` | Yes | Git commit hash of the before snapshot |
| `--after-commit` | Yes | Git commit hash of the after snapshot |
| `--workflow-id` | Yes | Workflow identifier (e.g., `wf2-autonomous-refactoring`) |
| `--workflow-run-id` | No | Unique run identifier (auto-generated if omitted) |
| `--test-command` | No | Command to run tests and collect counts (e.g., `pytest --tb=short -q`) |
| `--coverage-before` | No | Code coverage percentage before changes (default: 0.0) |
| `--coverage-after` | No | Code coverage percentage after changes (default: 0.0) |
| `--output` | No | Output file path for the JSON report (prints to stdout if omitted) |

## Output Schema

The script outputs a JSON object matching the `DeltaReport` schema:

```json
{
  "report_id": "delta-abc123",
  "workflow_id": "wf2-autonomous-refactoring",
  "workflow_run_id": "run-def456",
  "timestamp": "2026-03-20T14:30:00+00:00",
  "summary": "Modified 5 files: +120 lines, -45 lines. Tests: 42 passed, 0 failed.",
  "changes": [
    {
      "file_path": "src/utils.py",
      "change_type": "modified",
      "description": "+30 -12"
    }
  ],
  "metrics": {
    "files_modified": 5,
    "lines_added": 120,
    "lines_removed": 45,
    "tests_added": 3,
    "tests_passed": 42,
    "tests_failed": 0,
    "coverage_before": 75.0,
    "coverage_after": 82.0
  },
  "before_snapshot": "abc123def456",
  "after_snapshot": "789ghi012jkl"
}
```

## Workflow Integration

### WF2 — Autonomous Refactoring
Generate a delta report after refactoring to summarize files changed, lines added/removed, and verify test counts and coverage are maintained or improved.

### WF3 — Dependency Upgrades
Generate a delta report after upgrading dependencies to capture which files were modified for compatibility, test results post-upgrade, and coverage impact.

### WF5 — Documentation
Generate a delta report comparing generated documentation against existing docs to show what was added, modified, or removed.

## Metrics Calculated

- **files_modified**: Count of files with changes between the two commits
- **lines_added**: Total lines added across all changed files
- **lines_removed**: Total lines removed across all changed files
- **tests_added**: New test functions/methods detected in the diff
- **tests_passed**: Number of tests passing (from test command output)
- **tests_failed**: Number of tests failing (from test command output)
- **coverage_before**: Code coverage percentage before changes
- **coverage_after**: Code coverage percentage after changes

## Dependencies

- `gitpython` — Git operations for comparing commits and computing diffs

## Audit Integration

After generating a delta report, the calling workflow should log it via audit-logger MCP: `log_event` with `event_type: "delta_report_generated"` and include the `report_id` in the event details.
