---
name: validate-hld-san-architecture
description: Validates High-Level Design (HLD) documents against SAN Architecture standards from Confluence.
compatibility: Requires Confluence MCP server configured with access to SAN Architecture space.
metadata:
  author: connected-operations
  version: "1.0"
---

# Validate HLD Against SAN Architecture

Validates provided HLD documents against SAN Architecture patterns, standards, and guidelines from the SAN Architecture Confluence space.

**Requires**: Confluence MCP server configured with access to SAN Architecture space
**Requires**: HLD document in readable format (Markdown, text, or accessible file)

## Workflow

### 1. Load HLD Document

- Prompt user for HLD document location (file path or direct content)
- Extract key architectural components: system components, integration patterns, data flows, security mechanisms, infrastructure, technology stack

### 2. Retrieve SAN Architecture Standards

Query the SAN Architecture Confluence space for:
- Architecture patterns matching the HLD's domain
- Architectural principles and guidelines
- Technology standards and approved components
- Security and compliance requirements
- NFR baselines and benchmarks

### 3. Perform Validation Analysis

Compare HLD against SAN Architecture across:
- Architecture patterns: alignment with approved patterns, anti-pattern detection
- Technology stack: approved list compliance, version support
- Integration standards: API design, messaging patterns, data exchange
- Security and compliance: controls baseline, auth mechanisms, encryption
- Infrastructure: cloud patterns, containerization, IaC, CI/CD
- NFRs: scalability, performance, availability, observability

### 4. Generate Validation Report

Produce structured report with:
- Compliance summary and overall status
- Detailed findings with severity (Critical/High/Medium/Low)
- Current state vs required state per SAN Architecture
- Remediation recommendations with Confluence references
- Approved elements and strengths
- Questions and clarifications needed

### 5. Interactive Review

- Present findings to user
- Allow drill-down into specific deviations
- Fetch additional SAN Architecture Confluence pages on request
