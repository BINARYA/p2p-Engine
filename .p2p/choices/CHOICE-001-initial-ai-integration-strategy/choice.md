---
choice_id: CHOICE-001
title: Initial AI Integration Strategy
status: decided
created_at: 2026-05-20
created_by: local
source:
  intake: INTAKE-001
related:
  proposals:
  - PROP-001
  - PROP-004
  - PROP-005
  - PROP-006
---

# CHOICE-001 - Initial AI Integration Strategy

## Problem

P2P Engine has accepted a prompt-only MVP workflow, but `INTAKE-001` introduced the alternative idea that the CLI should integrate Codex directly immediately.

## Context

The accepted path is:

```text
prompt-only first
-> skill/agent guidance
-> later AI adapter
```

The alternative path is:

```text
direct Codex invocation inside the CLI now
```

This affects MVP scope, provider integration, credentials, deterministic tests and the boundary between P2P CLI, agent skills and future AI adapters.

## Governance Boundary

This choice is advisory until decided through P2P governance. It does not change the accepted status of any proposal by itself.

## Related Intake

- `INTAKE-001`

## Related Proposals

- `PROP-001` - CLI Foundation
- `PROP-004` - Prompt-only Import Workflow
- `PROP-005` - Codex Skill Integration
- `PROP-006` - Multi-Agent Integration Model

## Recommended Direction

Option C: keep prompt-only first and plan Codex adapter later.

Reason:
It preserves MVP stability while keeping direct Codex integration visible as a planned evolution.
