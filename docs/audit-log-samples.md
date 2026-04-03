# Audit Log Samples

**Project:** Autonomous AI SDLC Prototype
**Version:** 1.0
**Last Updated:** [Date]

---

## Overview

The audit-logger MCP server stores all records in append-only NDJSON format with SHA-256 hash chains for tamper evidence. This document provides sample records for each audit record type.

---

## Storage Location

```
audit/audit.ndjson
```

Each line is a self-contained JSON record. Records are linked via `previous_hash` → `content_hash` chain.

---

## Sample: Interaction Record

Logged when an AI agent processes a prompt and generates output.

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-03-20T14:30:00Z",
  "type": "interaction",
  "workflow_id": "wf1-requirement-to-software",
  "workflow_run_id": "run-abc123",
  "initiator": "developer-1",
  "content_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "previous_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "payload": {
    "input_prompt": "Implement a REST endpoint for user registration with email validation",
    "ai_output": "Created UserRegistrationController.java with POST /api/users endpoint...",
    "agent_role": "developer",
    "duration_ms": 1500
  }
}
```

---

## Sample: Checkpoint Record

Logged when a validation checkpoint is evaluated.

```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "timestamp": "2026-03-20T14:32:00Z",
  "type": "checkpoint",
  "workflow_id": "wf1-requirement-to-software",
  "workflow_run_id": "run-abc123",
  "initiator": "developer-1",
  "content_hash": "sha256:d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592",
  "previous_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "payload": {
    "checkpoint_id": "security-scan",
    "passed": true,
    "validation_details": "bandit scan completed: 0 HIGH, 0 CRITICAL, 2 LOW issues found",
    "metrics": {
      "high_issues": 0,
      "critical_issues": 0,
      "medium_issues": 0,
      "low_issues": 2
    }
  }
}
```

---

## Sample: Checkpoint Failure Record

Logged when a checkpoint blocks a workflow.

```json
{
  "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "timestamp": "2026-03-20T15:10:00Z",
  "type": "checkpoint",
  "workflow_id": "wf2-autonomous-refactoring",
  "workflow_run_id": "run-def456",
  "initiator": "developer-2",
  "content_hash": "sha256:ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d",
  "previous_hash": "sha256:d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592",
  "payload": {
    "checkpoint_id": "test-coverage",
    "passed": false,
    "validation_details": "Coverage 62% is below minimum threshold of 80%. Failing files: LegacyProcessor.java (45%), DataProcessor.java (58%)",
    "metrics": {
      "coverage_percent": 62,
      "threshold_percent": 80,
      "files_below_threshold": 2
    }
  }
}
```

---

## Sample: Event Record — Workflow Start

```json
{
  "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "timestamp": "2026-03-20T14:29:00Z",
  "type": "event",
  "workflow_id": "wf3-dependency-upgrades",
  "workflow_run_id": "run-ghi789",
  "initiator": "cron-scheduler",
  "content_hash": "sha256:4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce",
  "previous_hash": "sha256:ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d",
  "payload": {
    "event_type": "workflow_start",
    "details": {
      "scope": "security",
      "target": "sample-app/java-module",
      "trigger": "scheduled-nightly"
    }
  }
}
```

---

## Sample: Event Record — Rollback

```json
{
  "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "timestamp": "2026-03-20T15:15:00Z",
  "type": "event",
  "workflow_id": "wf2-autonomous-refactoring",
  "workflow_run_id": "run-def456",
  "initiator": "developer-2",
  "content_hash": "sha256:6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
  "previous_hash": "sha256:4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce",
  "payload": {
    "event_type": "rollback",
    "details": {
      "restore_point_id": "rp-wf2-20260320-143000",
      "reason": "Test coverage checkpoint failed — rolling back refactoring",
      "git_commit_restored": "a1b2c3d"
    }
  }
}
```

---

## Hash Chain Verification

To verify the integrity of the audit log:

1. Read each record sequentially
2. Compute `SHA-256(payload)` and compare to `content_hash`
3. Verify each record's `previous_hash` matches the prior record's `content_hash`
4. First record's `previous_hash` should be all zeros

Any mismatch indicates tampering or corruption.

---

## Querying Audit Records

Use the `query_audit` MCP tool with filters:

```
workflow_type: "wf1-requirement-to-software"
date_from: "2026-03-18T00:00:00Z"
date_to: "2026-03-22T23:59:59Z"
initiator: "developer-1"
outcome: "success"
type: "checkpoint"
```
