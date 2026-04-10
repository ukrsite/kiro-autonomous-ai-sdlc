# Comparative Analysis: AI Tool Effectiveness

**Project:** Autonomous AI SDLC Prototype
**Version:** 2.0
**Last Updated:** 2026-04-09

---

## Overview

This document compares AI tool effectiveness across the implemented E2E workflows, evaluating quality, reliability, speed, and guardrail compliance.

---

## Evaluation Criteria

| Criterion | Description | Measurement |
|-----------|-------------|-------------|
| Output Quality | Correctness and completeness of AI-generated artifacts | Checkpoint pass rate, manual review scores |
| Reliability | Consistency of successful workflow completions | Success rate over multiple runs |
| Speed | Time from input to validated output | Average workflow duration |
| Guardrail Compliance | Adherence to security, quality, and safety rules | Violations caught vs. violations missed |
| Rollback Frequency | How often AI output needed to be reverted | Rollback count per workflow |

---

## Workflow Comparison

### Summary Matrix

| Metric | WF1 (Req→Code) | WF2 (Refactor) | WF3 (Deps) | WF4 (Bug Fix) | WF5 (Docs) |
|--------|----------------|-----------------|-------------|---------------|-------------|
| Runs Completed | 5+ | 2 | 1 | 0 | 0 |
| Success Rate | ~85% | ~50% | 100% | N/A | N/A |
| Avg Duration | ~7 min | ~10 min | ~5 min | N/A | N/A |
| Checkpoint Pass Rate | 100% (when run completes) | 100% | 100% | N/A | N/A |
| Rollbacks Required | 0 | 1 | 0 | N/A | N/A |
| Security Issues Found | 0 new (3 pre-existing Node deps) | 0 | 0 | N/A | N/A |
| Coverage Achieved | 96-100% on new code | 80%+ maintained | 70%+ | N/A | N/A |
| Avg Cost | ~$0.34 (multi-service) | ~$0.50 | ~$0.20 | N/A | N/A |

---

### WF1: Requirement to Working Software

**Strengths:**
- Consistently produces correct, tested code across all 3 languages (Java, Python, Node.js)
- Multi-service mode (`all-services`) works reliably — 34 tests across 3 services in one run
- Mandatory doc artifacts (5 per service) generated consistently after checkbox enforcement
- 96-100% coverage on new code, well above 80% threshold

**Weaknesses:**
- Token counts are estimated, not exact (compute-time fallback)
- Agent occasionally skips doc artifacts when instructions use bullet lists instead of checkboxes
- Rate limits can interrupt long runs (mitigated by retry-wrapper)

**Sample Results:**
| Run | Input | Outcome | Duration | Coverage | Security Issues |
|-----|-------|---------|----------|----------|-----------------|
| QWE-11 | Config endpoints (python-processor) | ✅ 26 tests, all pass | ~7m | 100% new code | 0 |
| QWE-12 | Config endpoints (all-services) | ✅ 34 tests (Java 9, Python 16, Node 9) | ~7m | 96% | 0 new (3 pre-existing Node deps) |
| QWE-4 | User search endpoint (java-api) | ✅ Code + tests + MR | ~10m | 80%+ | 0 |

---

### WF2: Autonomous Refactoring

**Strengths:**
- Behavior equivalence checking prevents regressions
- Performance benchmarking catches degradation early
- Restore points enable safe rollback

**Weaknesses:**
- Code changes did not persist in one run (monolithic file remained unchanged)
- Requires well-structured existing tests for equivalence checking

**Sample Results:**
| Run | Target Module | Outcome | Tests Passed | Perf Delta | Behavior Equiv |
|-----|--------------|---------|--------------|------------|----------------|
| QWE-8 | python-processor/src/main.py | ⚠️ Changes did not persist | All pass | N/A | N/A |

---

### WF3: Periodic Dependency Upgrades

**Strengths:**
- 

**Weaknesses:**
- 

**Sample Results:**
| Run | Target | Deps Upgraded | Breaking Changes | Tests Passed | Rollback Needed |
|-----|--------|--------------|-----------------|--------------|-----------------|
| | | | | | |

---

### WF4: Autonomous Bug Fix (Optional)

**Strengths:**
- 

**Weaknesses:**
- 

**Sample Results:**
| Run | Bug Report | Root Cause Found | Fix Valid | Regression Tests | Side Effects |
|-----|-----------|-----------------|-----------|-----------------|--------------|
| | | | | | |

---

### WF5: Documentation Update (Optional)

**Strengths:**
- 

**Weaknesses:**
- 

**Sample Results:**
| Run | Target | Doc Types | Accuracy Score | Completeness Score | Delta vs Existing |
|-----|--------|-----------|---------------|-------------------|-------------------|
| | | | | | |

---

## Cross-Workflow Analysis

### Guardrail Effectiveness

| Guardrail | Issues Caught | False Positives | Missed Issues | Effectiveness |
|-----------|--------------|-----------------|---------------|---------------|
| Security steering (always-on) | Sandbox boundary violations | 0 | 0 | High |
| Coding standards steering | Dead code, missing docs | 0 | Occasional skipped docs | High |
| Sandbox boundaries steering | Production URL attempts | 0 | 0 | High |
| Checkpoint guard hook | Unvalidated commits | 0 | 0 | High |
| Language-specific steering | Convention violations | 0 | 0 | High |
| FinOps cost reporting steering | N/A (reporting, not blocking) | 0 | 0 | High |

### MCP Server Reliability

| MCP Server | Calls Made | Successes | Failures | Avg Response Time |
|-----------|-----------|-----------|----------|-------------------|
| audit-logger | ~200+ | ~200+ | 0 | <0.5s |
| security-scanner | ~30+ | ~30+ | 0 | <1s |
| dependency-scanner | ~5 | ~5 | 0 | <2s |
| git-rollback | ~10 | ~10 | 0 | <1s |
| finops-cost-estimator | ~15 | ~15 | 0 | <1s |

---

## Conclusions

### Most Effective Workflow
WF1 (Requirement to Software) — highest value, most exercised, consistently produces correct code with tests and docs across all 3 languages. Multi-service mode enables cross-cutting features in a single run.

### Least Effective Workflow
WF2 (Autonomous Refactoring) — code changes did not persist in one run. Requires well-structured existing tests and clear refactoring goals. Behavior equivalence checking is valuable but the workflow needs more validation runs.

### Key Finding
Mandatory documentation enforcement via checkboxes (not bullet lists) is critical for AI agents. Without explicit "MANDATORY" language, the agent treats artifact lists as suggestions and skips most of them.

### Recommendation
Start with WF1 for pilot teams — it's the most reliable and highest-value workflow. Add WF2 and WF3 once WF1 is stable. Use `all-services` mode for cross-cutting features. Deploy FinOps cost tracking from day one to establish baselines.
