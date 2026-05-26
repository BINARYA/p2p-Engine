# Exploration - PROP-015

## Interpretation

PROP-015 makes Change Sets operational. PROP-014 created metadata-only Change Sets; this proposal adds lifecycle transitions and task/action inspection.

## Lifecycle

Primary flow:

```text
proposed
→ planned
→ implementation_ready
→ in_progress
→ in_review
→ completed
```

Side states:

```text
blocked
cancelled
superseded
```

## MVP Commands

```bash
p2p change show CHANGE-001
p2p change set-status CHANGE-001 planned
p2p change tasks CHANGE-001
```

## Guardrail

Invalid transitions are rejected. A Change Set cannot jump directly from `proposed` to `completed`.
