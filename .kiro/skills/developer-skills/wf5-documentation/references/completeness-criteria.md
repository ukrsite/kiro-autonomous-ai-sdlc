# Completeness Criteria

This document defines the criteria used during the completeness review checkpoint in the WF5 Documentation workflow.

## Overview

The completeness review verifies that generated documentation covers all required areas for the requested documentation types. Documentation that fails the completeness review must be expanded before proceeding.

## Completeness Criteria by Documentation Type

### API Documentation Completeness

| Criterion | Required | Description |
|-----------|----------|-------------|
| All public functions documented | Yes | Every exported/public function has a documentation entry |
| All public classes documented | Yes | Every exported/public class has a documentation entry |
| All public methods documented | Yes | Every public method on documented classes has an entry |
| Constructor parameters documented | Yes | All constructor/init parameters are listed with types |
| Return types specified | Yes | Every function/method documents its return type |
| Parameter types specified | Yes | Every parameter includes its type annotation |
| At least one example per module | Yes | Each module has at least one usage example |
| Error conditions documented | Yes | Exceptions/errors that can be raised are listed |
| Module-level descriptions | Yes | Each module has a summary description |
| Deprecation notices included | No | Deprecated items are marked (if applicable) |

### Architecture Diagram Completeness

| Criterion | Required | Description |
|-----------|----------|-------------|
| Component diagram present | Yes | High-level component diagram showing major parts |
| Module interaction diagram present | Yes | Diagram showing how modules communicate |
| Data flow diagram present | Yes | At least one data flow for a key workflow |
| Layer diagram present | Yes | Diagram showing architectural layers |
| All major components represented | Yes | No significant component is missing from diagrams |
| External dependencies shown | Yes | Third-party services and libraries are represented |
| Relationships labeled | Yes | All arrows/connections have descriptive labels |
| Diagram descriptions included | Yes | Each diagram has a text description explaining it |

### Onboarding Guide Completeness

| Criterion | Required | Description |
|-----------|----------|-------------|
| Prerequisites listed | Yes | All required tools and versions specified |
| Installation steps provided | Yes | Step-by-step setup instructions with commands |
| Configuration documented | Yes | Environment variables and config files explained |
| Project structure described | Yes | Key directories and their purposes listed |
| Run instructions provided | Yes | Commands to build, run, and test the application |
| Common tasks documented | Yes | At least 3 common development tasks described |
| Troubleshooting section present | Yes | At least 3 common issues with resolutions |

## Completeness Scoring

Each criterion is scored as:
- **Pass**: The criterion is fully satisfied
- **Partial**: The criterion is partially satisfied (some items missing)
- **Fail**: The criterion is not satisfied

### Pass Thresholds

| Documentation Type | Required Pass Rate | Description |
|-------------------|-------------------|-------------|
| API Documentation | 100% required criteria | All required criteria must pass |
| Architecture Diagrams | 100% required criteria | All required criteria must pass |
| Onboarding Guides | 100% required criteria | All required criteria must pass |

### Overall Completeness

The completeness review checkpoint passes when all requested documentation types meet their individual pass thresholds.

## Review Process

1. **Enumerate** — List all items that should be documented (public interfaces, components, setup steps)
2. **Cross-reference** — Check each item against the generated documentation
3. **Score** — Mark each criterion as Pass, Partial, or Fail
4. **Report** — Generate a completeness report with:
   - Total criteria checked
   - Criteria passed / partial / failed
   - Specific items missing or incomplete
   - Recommendations for addressing gaps

## Failure Handling

If the completeness review fails:

1. Identify specific gaps (which interfaces, components, or sections are missing)
2. Generate the missing documentation sections
3. Re-run the completeness review
4. If the review still fails after one remediation attempt, report the remaining gaps and halt

Log all completeness review results via audit-logger MCP: `log_checkpoint`.

## Metrics Collected

| Metric | Description |
|--------|-------------|
| `total_criteria` | Total number of completeness criteria evaluated |
| `criteria_passed` | Number of criteria that fully passed |
| `criteria_partial` | Number of criteria partially satisfied |
| `criteria_failed` | Number of criteria that failed |
| `completeness_score` | Percentage of criteria passed (passed / total × 100) |
| `missing_items` | Count of specific items missing from documentation |
