# Verbosity Mode

## Overview

The workflow supports two verbosity modes that control how much output is shown to the user in chat.

- **`silent`** — minimal output. Only show what the user needs to act on (questions, approvals, errors, final results).
- **`debug`** — full output. Show all phase diagrams, stage announcements, internal reasoning, plan details, and completion messages.

## Reading the Mode

Always read the current mode from `aidlc-docs/aidlc-state.md` under `## Verbosity Mode`.

- If the field is missing or unset, default to **`debug`**.
- The user can change the mode at any time by saying "switch to silent mode" or "switch to debug mode". Update `aidlc-state.md` immediately when they do.

## Silent Mode Rules

When mode is `silent`, SUPPRESS the following:

| Item | Suppress? |
|---|---|
| Welcome message (full AI-DLC intro) | YES — replace with one-liner: `AI-DLC ready. Starting [stage]...` |
| Phase transition diagrams (╔══╗ boxes) | YES |
| Stage start/end announcements | YES |
| Execution plan details (checkbox lists before execution) | YES |
| Mermaid / ASCII workflow diagrams | YES |
| "What Happens Next" step lists | YES |
| Verbose completion messages per stage | YES |
| Internal reasoning narration ("I will now load...") | YES |

When mode is `silent`, ALWAYS SHOW the following:

| Item | Always Show? |
|---|---|
| Questions requiring user input | YES |
| Approval prompts (2-option choices) | YES |
| Errors and blocking findings | YES |
| Final deliverable summaries (e.g. files created, test results) | YES |
| WF selection confirmation | YES |
| Security scan results | YES |
| Checkpoint pass/fail results | YES |

## Debug Mode Rules

When mode is `debug`, show everything as defined in the respective stage rule files. No suppression.

## Changing Mode Mid-Workflow

The user can switch modes at any point. When they do:
1. Update `## Verbosity Mode` in `aidlc-docs/aidlc-state.md`
2. Acknowledge the change with a single line: `Verbosity mode set to [silent|debug].`
3. Apply the new mode immediately from the next output onward.
