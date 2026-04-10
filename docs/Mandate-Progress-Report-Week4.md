# Mandate Progress Report: Autonomous AI Software Development Lifecycle Prototype

**Document:** Progress Report — Week 4 (CI Hardening + FinOps + Multi-Service + Sandbox Deployment)
**Date:** 2026-04-09
**Period:** 2026-04-03 → 2026-04-09
**Reference:** Mandate — Autonomous AI Software Development Lifecycle Prototype

---

## Executive Summary

Week 4 hardened the CI pipeline, added FinOps cost tracking, enabled multi-service runs, and delivered the first live deployment of AI-generated code to AWS EKS. The system now supports `SERVICE_NAME=all-services` to inspect and update all three sandbox services in a single pipeline run. A new `finops-cost-estimator` MCP server tracks per-run costs across 5 dimensions (LLM tokens, compute time, MCP calls, checkpoints). Node.js checkpoint gates were added alongside the existing Java and Python gates. The python-processor service — with AI-generated config endpoints — is live at [https://test.genai-innovation.ericsson.net/python-processor/docs](https://test.genai-innovation.ericsson.net/python-processor/docs).

---

## 1. Week 4 Deliverables

| # | Deliverable | Status | Evidence |
|---|---|---|---|
| 1 | CI Pipeline Restructure | ✅ DELIVERED | Split lint into 5 jobs, `extends:` over YAML anchors, workflow rules |
| 2 | Shell Injection Fix | ✅ DELIVERED | `scripts/build_kiro_prompt.py` + `scripts/create_mr.py` extracted from YAML |
| 3 | Finalize Stage Fix (push + MR) | ✅ DELIVERED | `scripts/finalize_push.sh`, re-clone-and-overlay, 409 handler |
| 4 | WF1-WF5 Coverage Gaps Closed | ✅ DELIVERED | Restore points, mandatory tests, WF2 equivalence, WF4 side-effect, WF5 onboarding |
| 5 | FinOps Cost Estimator MCP Server | ✅ DELIVERED | `mcp-servers/finops-cost-estimator/server.py`, 4 tools, 5 cost dimensions |
| 6 | Node.js Checkpoint Gate | ✅ DELIVERED | `checkpoint-gates:node-tests` — `npm test` + Jest coverage |
| 7 | Multi-Service Mode (`all-services`) | ✅ DELIVERED | `SERVICE_NAME=all-services` runs across all 3 services |
| 8 | WF1 Summary Report | ✅ DELIVERED | `docs/wf1-summary-{ISSUE_KEY}.md` — mandatory doc artifact |
| 9 | LLM Token Cost Extraction | ✅ DELIVERED | `scripts/extract_token_usage.py` + compute-time estimation fallback |
| 10 | Rate-Limit Aware Retry | ✅ DELIVERED | `retry-wrapper.sh` — 5 retries, 60s cooldown on rate limit |
| 11 | MCP Server Deduplication | ✅ DELIVERED | Removed duplicates from agent configs; single source in `mcp.json` |
| 12 | Sandbox CI/CD Pipeline | ✅ DELIVERED | Kaniko → Artifactory → ECR (container + Helm chart) → EKS via GitOps |
| 13 | Live Deployment | ✅ DELIVERED | python-processor on EKS: [Swagger UI](https://test.genai-innovation.ericsson.net/python-processor/docs) |
| 14 | Documentation Update | ✅ DELIVERED | README, architecture docs, recommendations, lessons learned |

---

## 2. CI Pipeline Improvements

### 2.1 Pipeline Structure

The `.gitlab-ci-workflow.yml` pipeline now has 5 checkpoint gates running in parallel:

```
validate → execute-workflow → checkpoint-gates → finalize
                                  ├── java-tests
                                  ├── python-tests
                                  ├── node-tests
                                  ├── security-scan
                                  └── review
```

### 2.2 Key Fixes (April 3-6)

| Issue | Fix |
|---|---|
| Jira descriptions with `()`, `*`, `{code}` caused shell metacharacter errors | Extracted prompt builder to `scripts/build_kiro_prompt.py` (standalone Python) |
| MR creation failed on special characters | Extracted to `scripts/create_mr.py` (JSON body, not form-encoded) |
| `origin/main` not found in finalize | Save artifact as `sandbox-artifact/`, clone fresh, overlay changes |
| MR 409 false-positive on re-runs | Search exact `source_branch` match across opened/all states |
| `target/` directory appearing in MR | Added `rm -rf "${REPO_PATH}/target"` to `finalize_push.sh` |
| Python-tests failed on multi-service (`all-services`) | Iterate per Python service directory instead of running from `services/` root |

### 2.3 New Checkpoint Gate: Node.js

| Field | Value |
|---|---|
| Job | `checkpoint-gates:node-tests` |
| Image | `node:18` |
| Test runner | `npm test` (Jest) |
| Coverage | Jest `--coverage` with cobertura report |
| Threshold | Per-workflow (WF1: 80%) |
| Skip condition | No `package.json` in sandbox path |

### 2.4 Multi-Service Mode

Setting `SERVICE_NAME=all-services` on the Jira issue triggers a pipeline that:
- Resolves `repo_path: services` with `multi_service: true`
- Passes all individual service paths to the kiro-cli prompt
- The agent inspects and updates all 3 services (java-api, python-processor, node-gateway)
- Python-tests iterates per service; Java/Node tests detect their respective project files

### 2.5 Retry Wrapper Improvements

| Before (Week 3) | After (Week 4) |
|---|---|
| 3 retries, 10s initial delay | 5 retries, 15s initial delay |
| Fixed exponential backoff | Rate-limit detection (greps for "quota exceeded", "429", "throttle") |
| No cap | 60s minimum cooldown on rate limit, 300s max cap |
| No logging | Retry events logged to `/tmp/retry-wrapper.log` |

---

## 3. FinOps Cost Tracking

### 3.1 MCP Server

New `finops-cost-estimator` MCP server with 4 tools:

| Tool | When | Description |
|---|---|---|
| `estimate_workflow_cost` | Before run | Pre-run estimate based on scope |
| `calculate_workflow_cost` | After run | Post-run actuals from audit log |
| `get_cost_report` | On demand | Retrieve stored report (JSON/Markdown) |
| `get_historical_baseline` | On demand | p50/p95 statistics from past runs |

### 3.2 Cost Dimensions

| Dimension | Unit Price | Source |
|---|---|---|
| LLM Input Tokens | $0.003 / 1K tokens | kiro-cli log or compute-time estimation |
| LLM Output Tokens | $0.015 / 1K tokens | kiro-cli log or compute-time estimation |
| Compute Time | $0.00005 / sec | workflow_start → workflow_end timestamps |
| MCP Tool Calls | $0.0001 / call | tool_invocation events in audit log |
| Checkpoints | $0.001 / checkpoint | checkpoint records in audit log |

### 3.3 Token Estimation Priority

1. **kiro-cli trace log** (most accurate) — actual LLM API token counts. CI sets `KIRO_LOG_LEVEL=trace`.
2. **Manual injection** — `--input-tokens N --output-tokens N`
3. **Compute-time estimation** — duration × 40 tok/s output × 2.5 input ratio (configurable in `finops-cost-model.yml`)

`scripts/extract_token_usage.py` runs after kiro-cli in CI and injects token counts into the audit NDJSON before `calculate_workflow_cost`.

### 3.4 Steering Integration

`finops-cost-reporting.md` (always-on steering file) mandates the agent call `calculate_workflow_cost` after every `workflow_end` event and include the cost table in its final response.

---

## 4. WF1 Documentation Artifacts

Step 9 of WF1 now generates 5 mandatory doc artifacts per service (checkbox-tracked):

| Artifact | Path | Template |
|---|---|---|
| Release notes | `docs/release-notes-{ISSUE_KEY}.md` | `references/output-templates.md` |
| API changelog | `docs/CHANGELOG.md` (append) | Keep a Changelog format |
| OpenAPI spec | `docs/openapi.yaml` | OpenAPI 3.0.3 |
| Architecture diagram | `docs/architecture.md` | Mermaid diagram |
| WF1 Summary Report | `docs/wf1-summary-{ISSUE_KEY}.md` | `references/output-templates.md` |

The summary report uses the same structure as the agent's final chat response: headline with ✅/❌ status, checkpoint table, what was done, files list, and FinOps cost table.

---

## 5. Sandbox CI/CD — Container and Helm Delivery

Each service in `kiro-sandbox` has its own `.gitlab-ci.yml`:

| Stage | Description |
|---|---|
| `version` | `main`: semantic-release → semver. Other branches: `{version}-{hash}` |
| `build container` | Kaniko builds and pushes to Artifactory |
| `publish container ECR` | Copies image to AWS ECR |
| `create helm chart` | Packages Helm chart with release version |
| `helm publish ECR` | Pushes chart to ECR OCI Helm registry |
| `release` | On `main`: Git tag, CHANGELOG, GitLab release |

**Live deployment:** python-processor is deployed to AWS EKS via GitOps.

> **Swagger UI:** [https://test.genai-innovation.ericsson.net/python-processor/docs](https://test.genai-innovation.ericsson.net/python-processor/docs)

---

## 6. MCP Server Consolidation

Removed duplicate MCP server definitions from all 4 agent configs (`developer.json`, `devops.json` × 2 locations). The 5 custom servers (audit-logger, security-scanner, dependency-scanner, git-rollback, finops-cost-estimator) are now defined exclusively in `.kiro/settings/mcp.json`, generated by `setup-kiro.sh`:

- **CI mode:** stdio transport (`python3 server.py`)
- **Local mode:** Docker transport (ECR images with resolved volume mounts)

Agent configs retain only Docker-only servers (confluence, gitlab, jira) that can't run via stdio.

---

## 7. Validated E2E Runs

| Pipeline | Issue | Service | Tests | Coverage | Checkpoints | Cost | Duration |
|---|---|---|---|---|---|---|---|
| QWE-11 | Config endpoints | python-processor | 26 pass | 100% new code | 3/3 ✅ | $0.03 | ~7m |
| QWE-12 | Config endpoints | all-services | 34 pass (Java 9, Python 16, Node 9) | 96% | 3/3 ✅ | $0.34 | ~7m |
| QWE-12 (re-run) | Config endpoints | all-services | 34 pass | 96% | 3/3 ✅ | $0.34 | ~7m |

All runs produced: code changes, unit tests, 5 doc artifacts per service, delta report, audit trail, and cost report.

---

## 8. Known Issues

| # | Issue | Severity | Status |
|---|---|---|---|
| 1 | Jira "In Review" transition not found | Low | Open — depends on Jira workflow config |
| 2 | Personal kiro-cli token in CI | Medium | Open — service account needed |
| 3 | Docker MCP images stale after code changes | Medium | Open — must rebuild locally after server.py changes |
| 4 | LLM token counts estimated, not exact | Low | Mitigated — compute-time estimation when kiro-cli log unavailable |
| 5 | Helm chart version race with semantic-release | Low | Open — helm job needs `needs: [release]` in sandbox CI |

---

## 9. Conclusion

Week 4 hardened the end-to-end pipeline from Jira ticket to live deployment on AWS EKS. The system now supports multi-service runs, per-run cost tracking, Node.js checkpoint gates, mandatory documentation artifacts, and rate-limit-aware retry. The python-processor service — with AI-generated `GET /api/config` and `PUT /api/config/log-level` endpoints — is live and accessible via Swagger UI. Total pipeline duration is ~7 minutes from Jira trigger to merge request, with ~$0.34 estimated cost per multi-service run.
