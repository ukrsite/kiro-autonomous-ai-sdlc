"""AI-DLC Workflow Integration module.

Implements the integration of AI-DLC INCEPTION as the unified front-end
with WF1–WF5 as the CONSTRUCTION back-end. The INCEPTION phase handles
workspace detection, reverse engineering, requirements analysis, user
stories, and workflow planning. The Workflow Planning stage classifies
the request type and delegates to the appropriate WF for CONSTRUCTION.

Key components:
    - classifier: Request Type Classifier mapping request types to WF1–WF5.
    - delegation: Delegation Marker Manager for CONSTRUCTION stage tracking.
    - thresholds: Coverage threshold lookup per workflow.
    - handoff: Handoff Artifact generation, parsing, and validation.
    - audit: Unified Audit Writer (dual-write to audit.md and audit-logger MCP).
    - state: AIDLC State Manager for integrated workflow progress.
    - session: Session Continuity Handler for cross-phase resumption.
    - ci_approval: CI Auto-Approval Controller for --no-interactive mode.
    - orchestrator: Main entry point wiring all components together.
"""
